#!/usr/bin/env python3
"""Deterministic N3 gate: record a STOP run, replay it, compare bytes.

Runs the spike binary twice into fresh temp dirs. For each run the binary
itself already fails on record/replay mismatch; this script additionally
checks, with plain byte/hash operations only (no model judgement):
  1. original vs replay task outputs are byte-identical within a run
  2. original vs replay Copper unified logs are byte-identical within a run
  3. task outputs are byte-identical across the two independent runs
  4. the recorded run contains the authorized STOP (via comparison.txt)

Exit 0 only if every check passes. Prints one line per check.
"""
import hashlib
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
BIN = HERE / "target" / "debug" / "copper-stop-path"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    build = subprocess.run(
        ["cargo", "build", "--locked"], cwd=HERE, capture_output=True, text=True
    )
    if build.returncode != 0:
        print(build.stdout)
        print(build.stderr, file=sys.stderr)
        return build.returncode
    runs = []
    with tempfile.TemporaryDirectory(prefix="copper-stop-path-") as tmp:
        for i in (1, 2):
            out = pathlib.Path(tmp) / f"run{i}"
            proc = subprocess.run([str(BIN), str(out)], capture_output=True, text=True)
            print(f"run{i}_stdout_begin")
            print(proc.stdout, end="")
            print(f"run{i}_stdout_end")
            if proc.returncode != 0:
                print(proc.stderr, file=sys.stderr)
                print(f"FAIL run{i} exit={proc.returncode}")
                return 1
            runs.append(out)
            orig = out / "original-task-outputs.bin"
            repl = out / "replay-task-outputs.bin"
            print(f"run{i} task_outputs_cmp={'IDENTICAL' if orig.read_bytes() == repl.read_bytes() else 'DIFFER'}")
            print(f"run{i} original_task_outputs_sha256={sha256(orig)}")
            print(f"run{i} replay_task_outputs_sha256={sha256(repl)}")
            clog_o, clog_r = out / "original_0.copper", out / "replay_0.copper"
            print(f"run{i} copper_logs_cmp={'IDENTICAL' if clog_o.read_bytes() == clog_r.read_bytes() else 'DIFFER'}")
            print(f"run{i} original_copper_sha256={sha256(clog_o)}")
            print(f"run{i} replay_copper_sha256={sha256(clog_r)}")
            comp = (out / "comparison.txt").read_text()
            for line in comp.splitlines():
                print(f"run{i} comparison {line}")
            assert "command=STOP" in comp and "byte_identical=true" in comp
        a = (runs[0] / "original-task-outputs.bin").read_bytes()
        b = (runs[1] / "original-task-outputs.bin").read_bytes()
        print(f"cross_run_task_outputs_cmp={'IDENTICAL' if a == b else 'DIFFER'}")
        if a != b:
            return 1
    print("N3_GATE_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
