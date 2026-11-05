# Lane A P0 — evidence summary

Date (UTC): 2026-11-05
Host: Mac (hostname `Mac`, Darwin 24.3.0 arm64)
Code tip tested in fresh clones: ca8cd4db1623b1c525e7aed46a70b631f0bf3abb
  (evidence/docs commit on top adds only docs/evidence changes)
Reviewer independent result (NOT a run by this agent): Python 3.12.7 —
  reviewer reported the suite passing on Python 3.12.7. Recorded as
  independent reviewer evidence only; all runs below are Python 3.11.15
  on this Mac unless stated otherwise.

## Rebase onto current main

Rebased onto origin/main 4d2ce60 (Merge PR #4, secure-core Increment 2,
5995c0b). Pre-rebase lane commits 317fbc2/4d835b6/0db0b09/a90daa5/09d071d
replayed as dc3cf2b/37e3783/4b39b08/312592f/8bce081; no history outside
this lane was rewritten. No conflict markers remain, no rebase in progress.

Conflict resolution, file by file (overlapping files only):
- app/main.py: Lane A degraded semantics re-applied on Increment 2's
  client_from_env wiring. UNAVAILABLE (no client/binary): authenticated
  STOP executes UNSIGNED, HTTP 200, secure_core.status="unavailable",
  decision/sequence/audit_record null, audit UNSIGNED/core_unavailable,
  latch retained. REJECTED (reachable core): adapter NOT invoked,
  HTTP 503, secure_core.status="rejected", latch retained, observed
  state UNKNOWN. Reset/simulated-task call require_secure_core_for_motion()
  -> HTTP 503 without a core.
- integrations/secure_core.py: Increment 2 client retained (production
  external-key mode, development ephemeral keys, epoch/sequence/key-file
  handling); Lane A distinction preserved — unavailable is not a
  rejection, rejection fails closed.
- tests/test_secure_core.py: Increment 2 tests retained; Lane A tests
  assert the exact unavailable/rejected semantics above.
- tests/test_app.py: kept Increment 2 dev-mode fixture
  (QUBERON_SECURE_CORE_MODE=development); B5 tests added (below).
- docs/SECURE-CORE.md, README.md: Increment 2 mode documentation kept;
  Lane A degraded-mode wording and (README) B5 capability matrix added.
  Inflated tests-passed badge removal (dc3cf2b) kept.
- .github/workflows/secure-core.yml: upstream workflow kept; Lane A
  python-without-rust degraded job kept. Push branches include lane-*;
  PR to main triggers attached checks (verified on PR #5).
- Makefile: no base conflict; python3.11 preference kept; B5 adds
  CORE_CLI detection and the exact degraded demo message.
- Rust crates/apps/fuzz/scripts: untouched by Lane A; taken from main.

## B5 (commit ca8cd4d)

When the secure-core CLI is not built, `make demo` prints exactly:
secure core not built: STOP available with unsigned attestation; simulated task and latch reset are disabled. Run make core to enable them.
Status API exposes secure_core_available/secure_core_message; the
operator page shows the same message and disables (not errors on) the
simulated-task (taskBtn) and simulation-reset (resetBtn) controls.
STOP remains available. README carries the full capability matrix
(ACCEPTED / UNAVAILABLE / REJECTED x STOP / task / reset / attestation).

## Intermittent full-suite failure — diagnosis

With-Rust suite run 11x consecutively in the worktree before the fix:
48 passed every time. Exact B5 demo test standalone then exposed the
leakage: one run passed in 0.23s instead of ~8s. Root cause is real, in
test_b5_make_demo_prints_exact_degraded_message (pre-fix):
subprocess.run(timeout=8) kills only `make`, orphaning its uvicorn
child on port 8000; the next run passes spuriously via bind failure and
leaks port state across runs (order/state leakage). Fixed by starting
`make` with start_new_session=True and killing the whole process group
(SIGTERM, SIGKILL fallback); the test itself is the regression cover.
After fix: B5 test 6/6 with port 8000 free after each run; full suite
48 passed x3 more in worktree, x2 in fresh with-Rust clone, no leaks.

## Gates run on this Mac (Python 3.11.15, cargo/rustc 1.99.1)

- Rust: cargo fmt --all --check OK; cargo clippy --workspace
  --all-targets --all-features -- -D warnings clean;
  cargo test --workspace --all-features --locked: 17 passed
  (14 core + 3 CLI integration).
- Python with Rust: 48 passed (repeated, see above).
- Python without Rust (built CLI hidden, cargo/rustc excluded from
  PATH): 37 passed, 11 skipped. Named tests pass in this mode:
  test_stop_executes_without_secure_core_but_reset_does_not,
  test_stop_rejected_by_secure_core_does_not_invoke_adapter,
  test_b5_degraded_ui_message_and_disabled_controls,
  test_b5_make_demo_prints_exact_degraded_message (4 passed).

## Fresh clones (raw logs beside this file)

- fresh-clone-with-rust.log: fresh clone of ca8cd4d, no .venv/target;
  make setup/test, cargo fmt/clippy/test (17 passed), Python 48 passed
  x3 total, demo probe HTTP 200.
- fresh-clone-without-rust.log: fresh clone, PATH with NO CARGO /
  NO RUSTC, no CLI; make setup prints degraded message; 37 passed,
  11 skipped; named Lane A + B5 tests 4 passed; demo probe HTTP 200
  and prints the exact B5 degraded message.
- pi-readonly-inspection.log: unchanged prior read-only Pi inspection
  (no writes/deploy/restart). Conclusion unchanged: Pi-deployed app
  has no secure-core gate; no Pi pass is claimed. A Mac pass is not a
  Pi or Isaac-host pass.

## Historical commit note

317fbc2 (rebased dc3cf2b) is a docs-only badge removal made before the
no-Rust failure was fixed; history was not rewritten to hide this.
