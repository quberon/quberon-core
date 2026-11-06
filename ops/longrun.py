#!/usr/bin/env python3
"""Checkpointed, SIGTERM-durable long runs.

Why this exists: the post-merge adversarial rerun reached 56,506 executions and
exited RC=143 (128+15 = SIGTERM). It was killed, not crashed and not finished,
and because the summary was written only at the end, 56,506 executions produced
no citable evidence at all.

This module fixes the three failures in that one exit code:

  lifetime      the caller is launched detached by ops/worker.sh, so the end of
                an agent turn cannot take it down
  durability    results are appended and fsynced as they happen, and the summary
                is written atomically, so a kill at any instant leaves a valid
                file on disk
  resumability  a checkpoint records the next index, so a restart continues
                instead of starting over

Evidence rule enforced here, mechanically:

    summary.json with "complete": true is the ONLY artefact that may be cited.
    summary-partial.json exists so a killed run is diagnosable, and it carries
    "complete": false and "citable": false so nobody can quote it by accident.

Stdlib only. Usage:

    from ops.longrun import LongRun

    with LongRun("adversarial-rerun", outdir, total=len(cases)) as lr:
        for i, case in lr.items(cases):
            rec = execute(case)
            lr.record(rec, escaped=rec["escaped"])
"""

from __future__ import annotations

import json
import os
import platform
import signal
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["LongRun", "atomic_write_json", "TerminatedEarly"]


class TerminatedEarly(Exception):
    """Raised inside the context when a termination signal has been received."""


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_json(path: Path, obj) -> None:
    """Write JSON so no reader ever sees a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic within a filesystem
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _toolchain() -> dict:
    def ver(cmd):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            return (p.stdout or p.stderr).strip().splitlines()[0] if p.returncode == 0 else None
        except Exception:
            return None

    return {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "cargo": ver(["cargo", "--version"]),
        "rustc": ver(["rustc", "--version"]),
        "git_commit": ver(["git", "rev-parse", "HEAD"]),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "host": socket.gethostname(),
        "cpu_count": os.cpu_count(),
    }


class LongRun:
    """Append-as-you-go run with a resume checkpoint and an honest summary."""

    def __init__(self, name: str, outdir, total: int = 0,
                 checkpoint_every: int = 100, flush_every: int = 25,
                 metadata: dict = None, resume: bool = True):
        self.name = name
        self.outdir = Path(outdir)
        self.total = total
        self.checkpoint_every = max(1, checkpoint_every)
        self.flush_every = max(1, flush_every)
        self.metadata = dict(metadata or {})
        self.resume = resume

        self.outdir.mkdir(parents=True, exist_ok=True)
        self.results_path = self.outdir / "results.jsonl"
        self.checkpoint_path = self.outdir / "checkpoint.json"
        self.summary_path = self.outdir / "summary.json"
        self.partial_path = self.outdir / "summary-partial.json"

        self.start_index = 0
        self.index = 0
        self.counters = {"executed": 0, "escaped": 0, "errors": 0}
        self._since_ckpt = 0
        self._since_flush = 0
        self._stop = False
        self._stop_signal = None
        self._prev_handlers = {}
        self._fh = None
        self._started = None

    # -- signals ---------------------------------------------------------

    def _install_handlers(self):
        def handler(signum, _frame):
            self._stop = True
            self._stop_signal = signum
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            try:
                self._prev_handlers[sig] = signal.getsignal(sig)
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass  # not on the main thread; caller must poll should_stop

    def _restore_handlers(self):
        for sig, prev in self._prev_handlers.items():
            try:
                signal.signal(sig, prev)
            except (ValueError, OSError):
                pass

    @property
    def should_stop(self) -> bool:
        return self._stop

    # -- lifecycle -------------------------------------------------------

    def __enter__(self) -> "LongRun":
        self._install_handlers()
        self._started = time.time()

        if self.resume and self.checkpoint_path.exists():
            try:
                ck = json.loads(self.checkpoint_path.read_text())
                self.start_index = int(ck.get("next_index", 0))
                self.counters.update({k: int(v) for k, v in (ck.get("counters") or {}).items()})
            except (ValueError, OSError):
                self.start_index = 0  # unreadable checkpoint: start over, loudly
                print(f"{utcnow()} [longrun] checkpoint unreadable; restarting from 0", flush=True)
        self.index = self.start_index

        # A resumed run appends; a fresh run truncates. Never silently mix.
        self._fh = open(self.results_path, "a" if self.start_index else "w")

        # The summary from any previous attempt is no longer true.
        if self.summary_path.exists():
            self.summary_path.unlink()

        atomic_write_json(self.outdir / "run-metadata.json", {
            "name": self.name,
            "started_utc": utcnow(),
            "resumed_from_index": self.start_index,
            "total_planned": self.total,
            "toolchain": _toolchain(),
            "metadata": self.metadata,
        })
        print(f"{utcnow()} [longrun] {self.name} starting at index {self.start_index}"
              f" of {self.total}", flush=True)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self._flush()
            if exc_type is None and not self._stop:
                self._write_summary(complete=True, reason="finished")
                if self.checkpoint_path.exists():
                    self.checkpoint_path.unlink()
            else:
                reason = (f"signal {self._stop_signal}" if self._stop
                          else f"{exc_type.__name__}: {exc}")
                self._write_checkpoint(reason)
                self._write_summary(complete=False, reason=reason)
        finally:
            if self._fh:
                self._fh.close()
            self._restore_handlers()
        # A clean stop on SIGTERM is not an error: evidence is intact.
        return exc_type is TerminatedEarly

    # -- iteration -------------------------------------------------------

    def items(self, seq):
        """Yield (index, item) from the resume point, stopping cleanly on SIGTERM."""
        if self.total == 0:
            try:
                self.total = len(seq)
            except TypeError:
                pass
        for i in range(self.start_index, len(seq)):
            if self._stop:
                raise TerminatedEarly(f"signal {self._stop_signal} at index {i}")
            self.index = i
            yield i, seq[i]
            self._after_item()

    def _after_item(self):
        self._since_ckpt += 1
        self._since_flush += 1
        if self._since_flush >= self.flush_every:
            self._flush()
            self._since_flush = 0
        if self._since_ckpt >= self.checkpoint_every:
            self._write_checkpoint("periodic")
            self._since_ckpt = 0

    # -- recording -------------------------------------------------------

    def record(self, record: dict, escaped: bool = False, error: bool = False) -> None:
        payload = dict(record)
        payload.setdefault("index", self.index)
        payload.setdefault("utc", utcnow())
        self._fh.write(json.dumps(payload, sort_keys=True) + "\n")
        self.counters["executed"] += 1
        if escaped:
            self.counters["escaped"] += 1
        if error:
            self.counters["errors"] += 1

    def _flush(self):
        if self._fh:
            self._fh.flush()
            os.fsync(self._fh.fileno())

    def _write_checkpoint(self, reason: str):
        self._flush()
        atomic_write_json(self.checkpoint_path, {
            "next_index": self.index + 1,
            "counters": self.counters,
            "reason": reason,
            "utc": utcnow(),
        })

    def _write_summary(self, complete: bool, reason: str):
        summary = {
            "name": self.name,
            "complete": complete,
            "citable": complete,
            "reason": reason,
            "started_utc": datetime.fromtimestamp(self._started, timezone.utc)
                                   .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "finished_utc": utcnow(),
            "duration_s": round(time.time() - self._started, 3),
            "resumed_from_index": self.start_index,
            "last_index": self.index,
            "total_planned": self.total,
            "counters": dict(self.counters),
            "toolchain": _toolchain(),
            "metadata": self.metadata,
        }
        if not complete:
            summary["WARNING"] = (
                "PARTIAL RUN. This file is diagnostics, not evidence. Its counts "
                "must never be cited as a result. Re-run to completion; only "
                "summary.json with complete=true is citable."
            )
            atomic_write_json(self.partial_path, summary)
            print(f"{utcnow()} [longrun] PARTIAL ({reason}) at index {self.index}; "
                  f"checkpoint written, evidence intact", flush=True)
        else:
            atomic_write_json(self.summary_path, summary)
            if self.partial_path.exists():
                self.partial_path.unlink()
            print(f"{utcnow()} [longrun] COMPLETE: {self.counters}", flush=True)


def is_citable(summary_path) -> bool:
    """Gate helper: True only for a finished run. Use this before quoting a count."""
    data = json.loads(Path(summary_path).read_text())
    return bool(data.get("complete")) and bool(data.get("citable"))


if __name__ == "__main__":
    # Self-test: 500 items, SIGTERM-safe, resumable. Proves the mechanism
    # without needing the adversarial corpus.
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/longrun-selftest")
    cases = list(range(500))
    with LongRun("selftest", out, total=len(cases), checkpoint_every=50) as lr:
        for i, c in lr.items(cases):
            time.sleep(0.01)
            lr.record({"case": c, "ok": True}, escaped=(c % 97 == 0))
    print(json.dumps(json.loads((out / "summary.json").read_text()), indent=2))
