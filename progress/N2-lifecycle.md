# Progress - N2-lifecycle

Owner: N2-lifecycle alone. Other nodes must not edit this file.
Base at node start: origin/main aab6496699490f8deb15edd67fc65f481200e33a
(N0 merged; graph.md base line predates that merge.)

## Attempts (explicit, max 3)

- Attempt 1 (prior worker, rate-limited, preserved in place, NOT reset):
  coherent lifecycle implementation in app/main.py,
  integrations/secure_core.py, entrypoints (Makefile, systemd unit,
  scripts/deploy_user_pi.sh), new tests in tests/test_app.py,
  scripts/wave3_n2_evidence.py, and 10x evidence logs in both modes.
  Inspected on resume; not discarded.
- Attempt 2 (this resume): safety-semantics fix only - state-dir chmod
  must never tighten a shared/system ancestor (/, system temp dir,
  $HOME) when a DB sits directly there; secure-core parent handling
  unified behind the same guard; without-rust evidence now hides both
  debug and release CLIs; evidence logs now include the named gate
  tests verbosely before the 10 runs; permission test also asserts
  WAL/SHM sidecars (when present) and secure-core parent dir.
  All evidence below is from Attempt 2, re-run fresh after the fix.
- Attempt 3: unused.

## What the implementation does

- Import of app.main is filesystem-inert: the module-level
  `app = create_app(...)` (which created /tmp/quberon-robot-interface.db
  on import) is replaced by an explicit `asgi_app()` factory.
  Entrypoints use `uvicorn app.main:asgi_app --factory`
  (Makefile demo, systemd unit, scripts/deploy_user_pi.sh user unit;
  systemd unit also pins QUBERON_DB_PATH=/var/lib/quberon-robot-interface/quberon.db).
- Default state path is instance-scoped under
  ~/.local/share/quberon-robot-interface/quberon.db; QUBERON_DB_PATH
  and explicit db_path still work (legacy explicit path tested).
- State dirs are created/chmodded 0700 and DB files 0600
  (DB, -wal, -shm when present), except shared/system ancestors are
  never chmodded (Attempt-2 guard above).
- Secure core is instance-scoped from the app DB path
  (<stem>-secure-core.db, .seq, .epoch beside it, 0600 epoch writes);
  client_from_env no longer falls back to a global /tmp app DB when
  no app_db_path is given - it returns None (core unavailable).

## Safety semantics (fail directions, R-IMM-1 / R-IMM-2)

Unchanged and re-verified by named tests:
- STOP with core unavailable: authenticated STOP executes UNSIGNED,
  adapter invoked once, latch retained, audit UNSIGNED/core_unavailable.
  Reset/task (motion-permitting) fail closed (503, adapter not invoked).
  tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not
- STOP rejected by a reachable core: fail closed, adapter NOT invoked,
  latch retained, observed UNKNOWN, 503 with rejected decision.
  tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter

## Raw evidence (committed)

- docs/evidence/wave3-n2/with-rust-10x.log
  MODE with-rust, RUST_CLI_PRESENT: True, named gate tests 4 PASSED (-v),
  10/10 full-suite runs "68 passed", RESULT: 10 consecutive passed.
- docs/evidence/wave3-n2/without-rust-10x.log
  MODE without-rust, RUST_CLI_PRESENT: False, named gate tests 4 PASSED (-v),
  10/10 full-suite runs "57 passed, 11 skipped" (Rust-gated tests skip),
  RESULT: 10 consecutive passed.
- Failure diagnostics: scripts/wave3_n2_evidence.py captures, on any
  non-zero run, full pytest traceback (stderr merged into the log),
  UTC, DB_PATH, `ps -axo pid,ppid,state,command`, and
  `lsof -nP -iTCP:8000` port-owner output. No run failed in Attempt 2,
  so no diagnostics block was triggered.
- Rust gates (local, this resume): cargo fmt --all --check OK;
  cargo clippy --workspace --all-targets --all-features -- -D warnings OK;
  cargo test --workspace --all-features --locked OK
  (14 secure-core tests + 3 CLI tests passed);
  cargo audit OK; cargo deny check OK (advisories/bans/licenses/sources).
- Secret/diff checks: git diff --check exit 0; pattern scan of changed
  files and evidence logs found no private keys/tokens/64-hex secrets.
- make test after evidence (CLI restored): 68 passed.

## Scope notes

- Files changed: app/main.py, integrations/secure_core.py,
  scripts/wave3_n2_evidence.py (new), scripts/deploy_user_pi.sh,
  Makefile, systemd/quberon-robot-interface.service (entrypoint factory
  updates - required, the old `app.main:app` symbol no longer exists),
  tests/test_app.py (gate tests), docs/evidence/wave3-n2/ (new),
  progress/N2-lifecycle.md (this file).
- graph.md / checks.md / progress.md / REPO-MAP.md NOT edited:
  assembly is N0's alone. N0 to update checks.md N2 rows and
  REPO-MAP.md (new tracked: scripts/wave3_n2_evidence.py,
  docs/evidence/wave3-n2/*.log, progress/N2-lifecycle.md) at wave close.
- No Pi/hardware, blockchain, or public-claim changes.
