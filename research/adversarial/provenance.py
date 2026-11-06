"""Self-describing summary provenance (postmerge summary first).

The committed postmerge summary reported ``total_results=63012`` with no
``complete``, ``commit``, ``finished_utc``, ``toolchain`` or ``generator``
field: a reader quoting 63,012 quoted a count with no run attached to it.
This module makes every summary written through it carry that run inside
the JSON itself, so the count cannot be separated from its provenance.

Long-run machinery comes from ``ops.longrun`` when that module is
importable (atomic JSON writes, UTC clock). ``ops/longrun.py`` exists only
on the unmerged ``ops/installation`` branch at the time this node branched
from ``origin/main``, and ``ops/**`` is outside this node's ownership, so
this module tries ``ops.longrun`` first and otherwise uses a vendored
fallback with the same semantics (tempfile + fsync + ``os.replace``).
A clean clone works either way and picks up ``ops.longrun`` automatically
once it lands on main. The fallback is recorded in the output, never
hidden: see ``provenance.source`` / ``LONGRUN_SOURCE``.

No value is invented: a fact that cannot be obtained (git or cargo
absent, a historical field no committed evidence records) is ``None``,
never guessed.
"""
from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parents[1]

REQUIRED_FIELDS = ["complete", "citable", "commit", "started_utc",
                   "finished_utc", "toolchain", "generator"]


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_json(path, obj) -> None:
    """Write JSON so no reader ever sees a half-written file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic within a filesystem
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


LONGRUN_SOURCE = (
    "research/adversarial/provenance.py vendored fallback "
    "(ops/longrun.py absent on origin/main at branch time)"
)
try:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from ops.longrun import atomic_write_json as _ops_atomic  # type: ignore
    from ops.longrun import utcnow as _ops_utcnow  # type: ignore

    atomic_write_json = _ops_atomic  # noqa: F811
    utcnow = _ops_utcnow  # noqa: F811
    LONGRUN_SOURCE = "ops.longrun"
except Exception:  # ops/longrun.py not on this branch: keep fallback above
    pass


def _version(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if p.returncode == 0:
            lines = (p.stdout or p.stderr).strip().splitlines()
            return lines[0] if lines else None
    except Exception:
        pass
    return None


def git_commit(repo_root=None):
    """HEAD commit of the repo containing this file, or None if unknown."""
    try:
        p = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            timeout=20, cwd=str(repo_root or REPO_ROOT))
        if p.returncode == 0:
            return p.stdout.strip() or None
    except Exception:
        pass
    return None


def toolchain(commit=None):
    """Toolchain actually observed on this host; absent tools are None."""
    return {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "cargo": _version(["cargo", "--version"]),
        "rustc": _version(["rustc", "--version"]),
        "git_commit": commit if commit is not None else git_commit(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "host": socket.gethostname(),
        "cpu_count": os.cpu_count(),
    }


def enrich_summary(summary, *, complete: bool, reason: str,
                   started_utc=None, finished_utc=None, duration_s=None,
                   commit=None, toolchain_info=None, generator=None,
                   extra_provenance=None):
    """Return a copy of *summary* with self-describing provenance fields.

    Only a finished run (``complete=True``) is citable. A non-complete
    summary carries ``citable=False`` and an explicit WARNING.
    """
    out = dict(summary)
    prov = {
        "source": LONGRUN_SOURCE,
        "note": ("Provenance is embedded in this file. Values that could "
                 "not be obtained are null, never guessed."),
    }
    if extra_provenance:
        prov.update(extra_provenance)
    out["complete"] = bool(complete)
    out["citable"] = bool(complete)
    out["reason"] = reason
    out["started_utc"] = started_utc
    out["finished_utc"] = finished_utc if finished_utc is not None else utcnow()
    if duration_s is not None:
        out["duration_s"] = duration_s
    out["commit"] = commit if commit is not None else git_commit()
    out["toolchain"] = (toolchain_info if toolchain_info is not None
                        else toolchain(commit=out["commit"]))
    out["generator"] = generator if generator is not None else {
        "script": "research/adversarial/run.py",
        "name": "adversarial-runner",
    }
    out["provenance"] = prov
    if not complete:
        out["WARNING"] = (
            "PARTIAL RUN. This file is diagnostics, not evidence. Its "
            "counts must never be cited as a result. Re-run to "
            "completion; only a summary with complete=true and "
            "citable=true is citable."
        )
    else:
        out.pop("WARNING", None)
    return out


def write_summary(summary_path, summary, **enrich_kwargs) -> Path:
    """Enrich with complete=True and atomically write the summary."""
    enrich_kwargs.setdefault("complete", True)
    if not enrich_kwargs["complete"]:
        raise ValueError("write_summary requires complete=True")
    path = Path(summary_path)
    atomic_write_json(path, enrich_summary(summary, **enrich_kwargs))
    return path


def is_citable(summary_path) -> bool:
    """Gate helper: True only for a finished, citable summary file."""
    try:
        data = json.loads(Path(summary_path).read_text())
    except Exception:
        return False
    return bool(data.get("complete")) and bool(data.get("citable"))
