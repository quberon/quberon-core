# cov-app-main-py-asgi-app

NODE: cov-app-main-py-asgi-app
TIER: 1
BRANCH: node/cov-app-main-py-asgi-app
COMMITS: see git log on this branch (single node commit adding the two owned files; base 7fd9ea5)
STATUS: done

## CHANGED
- tests/test_cov_asgi-app.py (new): 4 tests naming app.main:asgi_app() --
  factory signature/fresh instances, env DB path + latched start +
  no secure-core sidecar files, ASGI serving (healthz, / redirect,
  public page + degraded notice, 404, 401 auth boundary), and logged-in
  status reporting secure_core_available=False with the exact degraded
  message when no QUBERON_SECURE_CORE_MODE is set.
- progress/cov-asgi-app.md (this file; the owned-paths list names this
  path -- see NEEDS A HUMAN DECISION below).

No production code changed: asgi_app() at app/main.py:625-627 already
delegates to create_app(); the gap was coverage, not behaviour.

## EVIDENCE
Command / toolchain / host / UTC:
- Host: Darwin 24.3.0 arm64 (Quberon1.local), 2026-11-06T10:53-10:55Z
- Toolchain: Python 3.11.15 (.venv/bin/python, venv built per Makefile
  from requirements.txt, pytest 8.3.4), cargo 1.99.1 for with-Rust mode
- Named gate: python -m pytest tests/test_cov_asgi-app.py -q
  Raw output (with Rust binary present): "4 passed, 1 warning in 0.15s"
  Raw output (Rust binary hidden, cargo off PATH): "4 passed, 1 warning in 0.18s"
- Fail-direction + import-inert, verbose, with Rust restored:
  tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not PASSED
  tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter PASSED
  tests/test_app.py::test_import_app_main_is_filesystem_inert PASSED
  all 4 tests/test_cov_asgi-app.py tests PASSED -- "7 passed, 1 warning in 0.46s"
Raw output path: terminal output reproduced verbatim above/inline here;
no separate log file is committed because only the two owned paths may
be written.

## TESTS (both modes)
- With Rust (cargo build --workspace; target/debug/quberon-secure-core-cli present):
  full suite: "215 passed, 2 warnings in 41.70s"; named file: 4 passed.
- Without Rust (CLI binary moved aside, PATH=.venv/bin:/usr/bin:/bin,
  cargo not found): full suite: "203 passed, 12 skipped, 2 warnings in
  38.39s" (exit 0); named file: 4 passed. The 12 skips are pre-existing
  Rust-gated tests; the new tests are not Rust-gated because they delete
  QUBERON_SECURE_CORE_MODE, under which client_from_env returns None
  whether or not the binary exists.
- Import-inert / fail directions: see EVIDENCE (7 passed).

## STILL NOT TRUE
- asgi_app() was not exercised via a real uvicorn subprocess binding a
  port; the uvicorn --factory contract is pinned at the callable/
  signature/ASGI-TestClient level only.
- The development-mode ephemeral secure-core provisioning path through
  asgi_app() itself (QUBERON_SECURE_CORE_MODE=development with the Rust
  binary generating keys) is not covered by the new tests; signed-core
  behaviour remains covered via create_app in tests/test_secure_core.py.
- No claim is made that importing app.main is inert beyond the existing
  tests/test_app.py probe (re-run and passing, not re-implemented here).
- Nothing here supports any certification, physical-safety, latency or
  regulatory-compliance claim; the app remains SIMULATION only and
  asgi_app()-served STOP without a core is UNSIGNED.

## NEEDS A HUMAN DECISION
- Path discrepancy in the node brief: Owned paths list
  progress/cov-asgi-app.md, while the Report/handoff template names
  progress/cov-app-main-py-asgi-app.md. I followed the Owned paths list
  (writing outside it is a failed node) and put the full report here;
  a human/scheduler should confirm which filename the gate expects.
- None on code or policy.
