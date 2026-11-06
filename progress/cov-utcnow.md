NODE: cov-app-main-py-utcnow
TIER: 1
BRANCH: node/cov-app-main-py-utcnow
COMMITS: single commit containing this file and tests/test_cov_utcnow.py (exact hash in git log / PR; self-referential hash cannot be embedded in its own commit)
STATUS: complete

CHANGED:
- tests/test_cov_utcnow.py (new, only code change)
- progress/cov-utcnow.md (owned report path listed in Owned paths)
- progress/cov-app-main-py-utcnow.md (report path named in the Report/handoff instructions; identical report)

Task finding: no omission justification was warranted. app/main.py:61-62
utcnow() (`return datetime.now(timezone.utc)`) is directly testable
in isolation, so direct coverage was added instead of justifying a gap.
No test previously named utcnow (verified by repo-wide search: only
app/main.py:61 definition, :66 iso() call, :162 create_session call).

Tests added (all names name utcnow explicitly):
- test_utcnow_returns_aware_datetime_in_utc: datetime instance,
  tzinfo present, utcoffset()==0, tzinfo==timezone.utc.
- test_utcnow_is_current_not_frozen_or_epoch: result bracketed by
  aware-UTC readings taken immediately before/after the call.
- test_utcnow_is_monotonic_non_decreasing_across_calls: second >=
  first, and within 60s of the test's own clock.
- test_utcnow_delegates_to_datetime_now_with_timezone_utc:
  monkeypatched app.main.datetime records the tz argument; asserts
  it is timezone.utc and the returned object is passed through.
- test_utcnow_isoformat_has_explicit_zero_offset_and_roundtrips:
  isoformat ends '+00:00', fromisoformat round-trips equal, offset 0.

EVIDENCE:
- command (target gate): .venv/bin/python -m pytest tests/test_cov_utcnow.py -q
  raw output: "5 passed in 0.07s" (final restored run; also 0.78s first run), exit 0
- toolchain: Python 3.11.15 (.venv/bin/python, /Users/quberon1/.local/bin/python3.11), pytest 8.3.4, cargo present at /opt/homebrew/bin/cargo for with-Rust mode
- host: Quberon1.local (macOS 15.3.1)
- UTC: 2026-11-06T12:41:58Z (evidence runs 2026-11-06 12:38-12:41 UTC)
- raw output paths (host, not committed):
  /tmp/cov-utcnow-with-rust.log (pre-build full suite),
  /tmp/cov-utcnow-cargo-build.log,
  /tmp/cov-utcnow-with-rust-built.log,
  /tmp/cov-utcnow-without-rust.log
- fail-direction (mutants, applied temporarily to app/main.py then
  restored byte-for-byte, git diff on app/main.py empty after):
  naive mutant `return datetime.now()`: 5 failed, exit 1.
  frozen mutant `return datetime(2020,1,1,tzinfo=timezone.utc)`:
  3 failed, 2 passed, exit 1. Restored: 5 passed, exit 0.
- import-inert gate: .venv/bin/python -m pytest
  tests/test_app.py::test_import_app_main_is_filesystem_inert -q
  -> "1 passed", exit 0.

TESTS (both modes):
- With Rust (cargo build --workspace exit 0, target/debug/quberon-secure-core-cli present):
  .venv/bin/python -m pytest -q -> "216 passed, 2 warnings in 41.30s", exit 0.
  (Before building the CLI, same suite: "204 passed, 12 skipped", exit 0.)
- Without Rust (CLI binary moved aside, PATH stripped of cargo dirs):
  .venv/bin/python -m pytest -q -> "204 passed, 12 skipped, 2 warnings in 38.61s", exit 0.
  CLI binary restored afterwards; final target run 5 passed.

STILL NOT TRUE:
- This node proves nothing about clock correctness on any deployed
  host (Pi, server): host clock sync/NTP, monotonicity across sleep
  or clock steps, and timezone-database state were not observed.
- utcnow() coverage does not certify that session-expiry or timestamp
  ordering is correct end-to-end; Store.get_session compares stored
  ISO strings, and that string-comparison ordering was not re-proven
  here (existing test_app.py coverage was run, not extended).
- No certification, physical-safety, latency, or regulatory-compliance
  claim is supported by this repository or by these tests; utcnow()
  is a simulated-system timestamp source, not a safety clock.
- The exact commit hash is not embedded above (impossible
  self-reference); it must be read from git log / the PR.

NEEDS A HUMAN DECISION:
- None for this node. Note the instruction inconsistency for the
  record: Owned paths list progress/cov-utcnow.md while the Report
  section names progress/cov-app-main-py-utcnow.md; both were written
  identically so neither checker path is empty.
