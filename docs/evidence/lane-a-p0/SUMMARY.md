# Lane A P0 — fresh evidence summary

Date (UTC): 2026-11-05
Host: Mac (hostname `Mac`)
Lane tip tested in fresh clones: a90daa5c4929c0dea461aa2084b7769cfb44af47
Preserved prior commits: 317fbc2, 4d835b6, 0db0b09 (not rewritten).

## Fresh clones

Both clones were created fresh in scratch from the lane tip, with no
pre-existing `.venv` and no pre-existing `target/` (recorded in the raw
logs). Only `requirements.txt` was installed, inside each clone's own
`.venv`. No reuse of the main worktree `.venv` or `target/`.

Documented commands run exactly as in README:

- With Rust: `make setup`, `make test`, `make core`,
  `cargo test --workspace`, `make demo`
- Without Rust: `make setup`, `make test`, `make demo`
  (PATH restricted so `cargo`/`rustc` were absent; raw log records
  `cargo: NO CARGO` and `rustc: NO RUSTC`)

`make demo` starts a blocking server; it was run as documented,
probed with curl (HTTP 302 to login), then terminated. That
termination is recorded in the raw logs.

### Results

- With Rust — `fresh-clone-with-rust.log`
  - Python: Makefile selected `/Users/quberon1/.local/bin/python3.11`
    (Python 3.11.15). System `python3` is 3.9.6, which is why the
    earlier (pre-fix) fresh run failed: code uses Python 3.10+
    `X | None` annotations. `make setup` now prefers `python3.11`.
  - cargo 1.99.1 / rustc 1.99.1 (Homebrew)
  - Python tests: 38 passed
  - Rust tests: 4 + 2 passed (plus 0-test suites), `cargo test --workspace` exit 0
  - Demo probe: HTTP 302

- Without Rust — `fresh-clone-without-rust.log`
  - Python 3.11.15 via `python3.11`; no cargo, no rustc, no CLI
  - `make setup` printed the documented degraded message:
    `secure core not built - STOP will run with unsigned attestation; see docs/SECURE-CORE.md`
  - Python tests: 32 passed, 6 skipped (Rust-dependent tests skip)
  - Demo probe: HTTP 302

Pre-fix fresh runs of 0db0b09 in both modes failed 1 test
(`test_gnss_parser_no_fix_and_fix_and_bad_checksum`) under Python 3.9.6
with `TypeError: unsupported operand type(s) for |`. That failure is
why `Makefile` was changed; the fix was verified green in patched
fresh clones before committing, then re-verified above in clean
clones of the committed tip.

## Pi read-only inspection

Raw output: `pi-readonly-inspection.log` (ssh BatchMode, grep/ls/ps
only — no writes, restart, deploy, or config change).

Evidence, exactly as observed on `quberon-pi` at
2026-11-05T08:00:56Z:

- Running process: `/home/quberon1/quberon-robot-interface/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8443 ...`
  from deploy dir `/home/quberon1/quberon-robot-interface`
- `grep secure_core|SecureCore|execute_stop|quberon-secure app/main.py`
  → `NO_MATCH_app/main.py`
- `integrations/` contains only `__init__.py`, `meta.py`, `__pycache__`;
  same grep → `NO_MATCH_integrations`
- No `target/debug/quberon-secure-core-cli` or
  `target/release/quberon-secure-core-cli` on the Pi

Conclusion limited to those files/process: the Pi-deployed app does
NOT include the secure-core gate. No inference beyond the inspected
files and process command is made. The secure-core gate is therefore
repo/Mac-tested only; it is not deployed on the Pi. No Pi claim is
supported.

## Historical commit note

317fbc2 is a docs-only badge-removal commit made before the no-Rust
failure was fixed; at that commit the Python suite was not green in
the no-Rust/Python-3.9 fresh-clone sense demonstrated later. History
was not rewritten to hide this.
