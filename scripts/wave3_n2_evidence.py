#!/usr/bin/env python3
"""Run and capture the Wave-3 N2 lifecycle evidence gate."""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd: list[str], cwd: Path, env: dict[str, str], output) -> int:
    output.write(f"$ {' '.join(cmd)}\n")
    output.flush()
    proc = subprocess.run(cmd, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, text=True)
    output.write(f"[exit={proc.returncode}]\n")
    output.flush()
    return proc.returncode


def diagnostics(output, db_path: Path) -> None:
    output.write(f"UTC: {datetime.now(timezone.utc).isoformat()}\n")
    output.write(f"DB_PATH: {db_path}\n")
    output.write("PROCESS_LIST:\n")
    output.flush()
    subprocess.run(["ps", "-axo", "pid,ppid,state,command"], stdout=output, stderr=subprocess.STDOUT, text=True)
    output.write("PORT_8000_OWNER:\n")
    output.flush()
    subprocess.run(["lsof", "-nP", "-iTCP:8000"], stdout=output, stderr=subprocess.STDOUT, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("with-rust", "without-rust"), required=True)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    python = repo / ".venv" / "bin" / "python"
    rust_cli = repo / "target" / "debug" / "quberon-secure-core-cli"
    release_cli = repo / "target" / "release" / "quberon-secure-core-cli"
    hidden_cli = rust_cli.with_name(rust_cli.name + ".n2-hidden")
    hidden_release = release_cli.with_name(release_cli.name + ".n2-hidden")
    if not python.is_file():
        raise SystemExit("missing .venv/bin/python")
    if args.mode == "with-rust" and not rust_cli.is_file():
        raise SystemExit("with-rust mode requires target/debug/quberon-secure-core-cli")

    moved = False
    moved_release = False
    try:
        if args.mode == "without-rust" and rust_cli.exists():
            rust_cli.replace(hidden_cli)
            moved = True
        if args.mode == "without-rust" and release_cli.exists():
            release_cli.replace(hidden_release)
            moved_release = True
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if args.mode == "without-rust":
            env.pop("QUBERON_SECURE_CORE_BIN", None)
            path_parts = [p for p in env.get("PATH", "").split(os.pathsep) if not (Path(p) / "cargo").exists()]
            env["PATH"] = os.pathsep.join(path_parts)
        with output_path.open("w") as output:
            output.write(f"MODE: {args.mode}\n")
            output.write(f"START_UTC: {datetime.now(timezone.utc).isoformat()}\n")
            output.write(f"PYTHON: {subprocess.check_output([str(python), '--version'], text=True, stderr=subprocess.STDOUT).strip()}\n")
            output.write(f"RUST_CLI_PRESENT: {rust_cli.is_file() or release_cli.is_file()}\n")
            output.write(f"RUNS_REQUIRED: {args.runs}\n")
            output.flush()
            named = [
                "tests/test_app.py::test_import_app_main_is_filesystem_inert",
                "tests/test_app.py::test_state_paths_are_private_and_instance_scoped",
                "tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not",
                "tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter",
            ]
            output.write("\n===== NAMED GATE TESTS (-v) =====\n")
            output.flush()
            rc = run([str(python), "-m", "pytest", "-v", *named], repo, env, output)
            if rc:
                diagnostics(output, repo / ".n2-evidence-state" / args.mode / "named.db")
                return rc
            for index in range(1, args.runs + 1):
                output.write(f"\n===== RUN {index}/{args.runs} =====\n")
                output.flush()
                db_path = repo / ".n2-evidence-state" / args.mode / f"run-{index}.db"
                shutil.rmtree(db_path.parent, ignore_errors=True)
                rc = run([str(python), "-m", "pytest", "-q"], repo, env, output)
                if rc:
                    diagnostics(output, db_path)
                    return rc
            output.write(f"\nEND_UTC: {datetime.now(timezone.utc).isoformat()}\n")
            output.write(f"RESULT: {args.runs} consecutive full-suite runs passed\n")
        return 0
    finally:
        shutil.rmtree(repo / ".n2-evidence-state", ignore_errors=True)
        if moved and hidden_cli.exists():
            hidden_cli.replace(rust_cli)
        if moved_release and hidden_release.exists():
            hidden_release.replace(release_cli)


if __name__ == "__main__":
    raise SystemExit(main())
