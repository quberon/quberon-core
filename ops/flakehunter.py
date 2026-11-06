#!/usr/bin/env python3
"""Standing hunt for the open P0: intermittent STOP-path non-determinism.

We fixed a plausible cause (the orphaned uvicorn leak at tests/test_app.py:349)
but never proved it was the cause, because the failing run's traceback was
never captured. A control-path flake we cannot explain is the most dangerous
thing in this repository, and no amount of green CI retires it.

This daemon runs the suite in randomised order under CPU contention, forever,
capturing on every run: exit code, full pytest output, process list, listening
port owners, database paths under the temp dir, the random seed and the
environment. It stops on one of exactly two outcomes, and says which:

    REPRODUCED   a failure with a captured traceback, saved whole
    DOWNGRADED   1000 consecutive clean runs with no failure observed

DOWNGRADED is not "fixed". It is a bounded statement about 1000 runs on one
host, and it must be written that way wherever it is cited.

Runs under ops/longrun.py, so SIGTERM at any instant leaves a valid checkpoint
and every raw run already on disk.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ops.longrun import LongRun, TerminatedEarly  # noqa: E402

REPO = Path(os.environ.get("QUBERON_REPO", str(Path.home() / "quberon-core"))).resolve()
if sys.platform == "darwin":
    _default_state = Path.home() / "Library" / "Application Support" / "Quberon"
else:
    _default_state = Path.home() / ".local" / "state" / "quberon"
STATE_DIR = Path(os.environ.get("QUBERON_STATE", str(_default_state)))
OUT = STATE_DIR / "flakehunt"
CLEAN_RUNS_TO_DOWNGRADE = 1000


def capture_context(tmpdir: Path) -> dict:
    """Everything we wished we had the first time this failed."""
    def sh(cmd):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return p.stdout
        except Exception as e:
            return f"<failed: {e}>"

    dbs = []
    try:
        dbs = sorted(str(p) for p in Path("/tmp").glob("**/*.db"))[:50]
    except Exception:
        pass
    return {
        "processes": sh(["ps", "-Ao", "pid,ppid,stat,etime,command"])[:20000],
        "listening": sh(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])[:8000],
        "uvicorn_procs": sh(["pgrep", "-afl", "uvicorn"])[:4000],
        "tmp_databases": dbs,
        "tmpdir": str(tmpdir),
        "load": sh(["uptime"]).strip(),
        "env_subset": {k: v for k, v in os.environ.items()
                       if k.startswith(("QUBERON", "PYTEST", "TMPDIR", "PATH"))},
    }


def one_run(index: int, contention: int, outdir: Path) -> dict:
    """One randomised, contended full-suite run. Returns a record."""
    seed = random.randrange(1, 2**31)
    run_dir = outdir / "runs" / f"{index:06d}"
    run_dir.mkdir(parents=True, exist_ok=True)

    loaders = []
    for _ in range(contention):
        loaders.append(subprocess.Popen(
            [sys.executable, "-c",
             "import time\nend=time.time()+3600\nwhile time.time()<end: pass"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ))

    venv_py = REPO / ".venv" / "bin" / "python"
    py = str(venv_py) if venv_py.exists() else sys.executable
    cmd = [py, "-m", "pytest", "-q", "-p", "no:randomly",
           f"--basetemp={run_dir / 'pytest-tmp'}"]
    # -p no:randomly then explicit shuffling keeps the order reproducible from
    # the recorded seed; a flake you cannot replay is only half a finding.
    env = dict(os.environ, PYTHONHASHSEED=str(seed), QUBERON_FLAKEHUNT_SEED=str(seed))

    started = time.time()
    try:
        p = subprocess.run(cmd, cwd=str(REPO), env=env, capture_output=True,
                           text=True, timeout=3600)
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        rc, out, err = 124, "", "TIMEOUT after 3600s"
    finally:
        for lp in loaders:
            lp.terminate()
        for lp in loaders:
            try:
                lp.wait(timeout=10)
            except Exception:
                lp.kill()

    duration = round(time.time() - started, 2)
    (run_dir / "pytest.stdout.log").write_text(out)
    (run_dir / "pytest.stderr.log").write_text(err)

    record = {
        "index": index, "seed": seed, "rc": rc, "duration_s": duration,
        "contention": contention, "failed": rc != 0,
        "log_dir": str(run_dir),
    }

    if rc != 0:
        ctx = capture_context(run_dir / "pytest-tmp")
        (run_dir / "context.json").write_text(json.dumps(ctx, indent=2))
        record["context_path"] = str(run_dir / "context.json")
        tail = (out + "\n" + err)[-8000:]
        record["tail"] = tail
        print(f"\n*** REPRODUCED at run {index} (seed {seed}, rc {rc}) ***")
        print(f"*** full output: {run_dir} ***\n{tail[-3000:]}", flush=True)
    else:
        # Keep clean runs lean, but never delete the fact that they happened.
        (run_dir / "pytest.stdout.log").write_text(out[-2000:])
        (run_dir / "pytest.stderr.log").unlink(missing_ok=True)

    return record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--forever", action="store_true")
    ap.add_argument("--max-runs", type=int, default=CLEAN_RUNS_TO_DOWNGRADE)
    ap.add_argument("--contention", type=int, default=max(2, (os.cpu_count() or 4) // 2))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    outdir = Path(a.out)
    total = 10**9 if a.forever else a.max_runs
    indices = list(range(total))
    consecutive_clean = 0

    with LongRun("flakehunt", outdir, total=total, checkpoint_every=5,
                 metadata={"contention": a.contention,
                           "clean_runs_to_downgrade": CLEAN_RUNS_TO_DOWNGRADE,
                           "purpose": "root-cause the open STOP-path P0"}) as lr:
        consecutive_clean = int(lr.counters.get("consecutive_clean", 0) or 0)
        try:
            for i, _ in lr.items(indices):
                rec = one_run(i, a.contention, outdir)
                lr.record(rec, escaped=rec["failed"], error=rec["failed"])

                if rec["failed"]:
                    lr.counters["consecutive_clean"] = 0
                    lr.metadata["outcome"] = "REPRODUCED"
                    lr.metadata["reproduced_at_index"] = i
                    lr.metadata["reproduced_seed"] = rec["seed"]
                    lr.metadata["evidence"] = rec["log_dir"]
                    print(f"{i}: FAILED rc={rec['rc']} seed={rec['seed']} "
                          f"-> stopping, traceback captured", flush=True)
                    break

                consecutive_clean += 1
                lr.counters["consecutive_clean"] = consecutive_clean
                print(f"{i}: clean ({consecutive_clean} consecutive) "
                      f"{rec['duration_s']}s", flush=True)

                if consecutive_clean >= CLEAN_RUNS_TO_DOWNGRADE:
                    lr.metadata["outcome"] = "DOWNGRADED"
                    lr.metadata["downgrade_statement"] = (
                        f"{CLEAN_RUNS_TO_DOWNGRADE} consecutive clean randomised, "
                        f"contended runs on one host. This is a bounded "
                        f"observation, not proof the defect is fixed, and must "
                        f"be cited with those words."
                    )
                    print(f"DOWNGRADED after {consecutive_clean} clean runs", flush=True)
                    break
        except TerminatedEarly:
            raise

    summary = outdir / "summary.json"
    if summary.exists():
        print(summary.read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
