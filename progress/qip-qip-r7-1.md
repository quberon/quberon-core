NODE: qip-qip-r7-1
TIER: 1
BRANCH: node/qip-qip-r7-1
COMMITS: see git log on branch (this file committed with the conformance change)
STATUS: done for owned paths; QIP-v0.1 traceability amendment NOT done (profile-owner only, see handoff)

TASK RESTATED
QIP-R7.1 (AUTHORIZE) was UNIMPLEMENTED: "QIP-DEG-03 skipped: NOT TESTED,
gap not pass". Trace it to a passing conformance test or record it as
explicitly untestable. Partial coverage stays UNIMPLEMENTED; a gap is
never rounded up to a trace. A work node may not amend QIP traceability
itself (QIP-v0.1 section 11 belongs to the profile owner).

WHAT WAS FOUND
- On current origin/main, QIP-DEG-03 is no longer skipped: Wave 5 F1
  (progress/F1-degraded-conformance.md) un-skipped it and it passes in
  both Rust modes. DEG-03 covers reachable refusal alone; DEG-01 covers
  authority unavailability alone.
- No existing test asserted QIP-R7.1 itself: that unavailability and
  reachable refusal are recorded AND returned as DISTINCT outcomes.
  Two separately-passing single-state tests do not by themselves prove
  the two outcomes never collapse into one another. That non-collapse
  was the remaining, testable gap for QIP-R7.1.

CHANGED (owned paths only: conformance/**, progress/qip-qip-r7-1.md)
- conformance/test_conformance.py: appended QIP-DEG-04 (no IDs
  renumbered; DEG class header updated 01..03 -> 01..04).
  test_QIP_DEG_04_unavailable_and_reachable_refusal_are_distinct issues
  the SAME operator STOP against adapter_no_core (authority unavailable)
  and adapter_refusing_core (reachable refusal, QIP-DEG-03 injection)
  and asserts pairwise distinctness of every returned operator-facing
  field and of the recorded audit outcome:
    unavailable: 200, command_state ACKNOWLEDGED, observed_state
      SIMULATED_STOPPED, secure_core_status "unavailable",
      audit auth_result "UNSIGNED/core_unavailable" (exactly 1 event)
    refusing:    503, command_state UNKNOWN, observed_state UNKNOWN,
      secure_core_status "rejected", non-empty explanatory detail,
      audit auth_result "secure_core_rejected" (exactly 1 event)
  Both retain stop_latched True. If the refusal injection capability is
  False the test skips as NOT TESTED (via _needs_injection), never passes.
- conformance/README.md: new "QIP-R7.1 distinctness (QIP-DEG-04)"
  section stating DEG-04 supports but does not amend the QIP-v0.1
  section 11 row; QIP-R7.1 stays UNIMPLEMENTED in QIP-v0.1.md until the
  profile owner amends it.
- No app/**, integrations/**, or any control-path file was changed.

EVIDENCE
Host: Darwin Mac 24.3.0 (macOS 15.3.1), arm64 T8132
Toolchain: Python 3.11.15 (.venv from requirements.txt), cargo 1.99.1,
  rustc 1.99.1 (Homebrew)
UTC (run start): 2026-11-06T16:24:58Z
Raw output paths (this machine):
  /tmp/qip-r7-1-evidence/conformance-with-rust.log
  /tmp/qip-r7-1-evidence/conformance-without-rust.log
  /tmp/qip-r7-1-evidence/full-with-rust.log
  /tmp/qip-r7-1-evidence/full-without-rust.log
  /tmp/qip-r7-1-evidence/negative_probe.py
Raw output (verbatim tails):
  Targeted: .venv/bin/python -m pytest conformance/test_conformance.py::test_QIP_DEG_04_unavailable_and_reachable_refusal_are_distinct conformance/test_conformance.py::test_QIP_DEG_01_without_core_stop_unsigned_but_reset_fails_closed conformance/test_conformance.py::test_QIP_DEG_03_persistence_failure_and_reachable_refusal -q -rs
    3 passed, 1 warning in 0.65s
  With Rust (cargo build --workspace first):
    conformance: 29 passed, 1 warning in 4.52s
    full suite:  212 passed, 2 warnings in 39.27s
  Without Rust (binary moved aside, PATH=/usr/bin:/bin:/usr/sbin:/sbin):
    conformance: 28 passed, 1 skipped, 1 warning in 3.91s
      SKIPPED [1] conformance/test_conformance.py:23: NOT TESTED in this
      run: secure-core binary unavailable, so the authorized reset path
      cannot be exercised   (this is QIP-LATCH-03 only; DEG-04 passed)
    full suite:  200 passed, 12 skipped, 2 warnings in 37.20s
  Exit gate (exact): .venv/bin/python -m pytest conformance/ -q
    29 passed, 1 warning in 4.50s   (exit 0, with Rust binary present)
  Negative control (negative_probe.py, uninjected no-core adapter):
    uninjected: status=200 command=ACKNOWLEDGED secure_core=unavailable observed=SIMULATED_STOPPED
    NEGATIVE CONTROL OK: DEG-04 refusing expectations FAIL without injection (test is not vacuous)
  Import check (empty dir): import app.main -> "import ok", before/after
    file lists identical: import_app_main_created_files: 0 (diff empty)

TESTS (both modes): see EVIDENCE above. DEG-04 passes in both modes
(it uses only core-less/stub fixtures and needs no Rust binary).

STILL NOT TRUE (mandatory, non-empty)
- QIP-R7.1 is still recorded UNIMPLEMENTED in
  docs/specs/intervention-profile/QIP-v0.1.md section 11. This node did
  NOT amend it and must not; DEG-04 is supporting evidence only.
- The reachable-refusal side is exercised through a conformance-side
  stub authority raising SecureCoreRejected, NOT through a real Rust
  secure-core rejection of a signed envelope. No signing/verification,
  sequence/epoch handling, or real authority is exercised by DEG-04.
- Adapter non-invocation under refusal is inferred from UNKNOWN /
  latch / audit outcomes, not from an invocation counter on a real
  adapter. No manufacturer interface, real robot, physical stopping,
  latency, persistence-corruption, or restart-recovery claim is made.
- Without the Rust binary, QIP-LATCH-03 still skips (NOT TESTED in
  that run); that skip is a gap, not a pass.
- No certification, physical-safety, latency, or regulatory-compliance
  claim is supported by this repository or by this test.

NEEDS A HUMAN DECISION
- Profile owner: run the QIP-v0.1 section 11 amendment procedure to
  decide whether QIP-DEG-04 (+ DEG-01/DEG-03) may replace the
  UNIMPLEMENTED marker for QIP-R7.1, given the stub-authority limit.
handoff: docs/specs/intervention-profile/QIP-v0.1.md needs section 11 traceability amendment for QIP-R7.1 (UNIMPLEMENTED -> QIP-DEG-04, if accepted) because traceability amendment belongs to the profile owner, not a work node
