NODE: qip-qip-r10-1 (QIP-R10.1 OBSERVE)
TIER: 1
BRANCH: node/qip-qip-r10-1
COMMITS: 8374dcd test(conformance): add QIP-CAP capability declaration tests for R10.1; plus the commit adding this progress file (see PR head / git log for its hash)
STATUS: partial
CHANGED:
  - conformance/adapter_interface.py: neutral AdapterUnderTest.capability_declaration() contract for QIP-R10.1 (target_scope, intervention_kinds stop/audit_only, undeclared_kinds="unsupported", status_values, reset_semantics, manufacturer_mapping/manufacturer_mapping_source) plus capability flag capability_declaration_available=False by default (False = NOT TESTED skip, never a pass).
  - conformance/quberon_adapter.py: QuberonCoreAdapter.capability_declaration() for the in-repo SIMULATION adapter only, derived from app/integrations behaviour; manufacturer_mapping and manufacturer_mapping_source explicitly None.
  - conformance/test_conformance.py: appended stable IDs QIP-CAP-01..06 (no renumbering). CAP-01 completeness + explicit no-manufacturer-mapping; CAP-02 declared stop kinds trigger stop and declared audit-only kinds do not; CAP-03 undeclared kind QIP_UNSUPPORTED_KIND returns 400, is not approximated, creates no event, latch unchanged; CAP-04 declared status values match observed stop/status; CAP-05 declared reset distinct-from-stop, admin-gated, operator reset 403 with latch retained; CAP-06 admin reset (Rust core required) clears latch, task_started False, declared status values match.
  - conformance/README.md: CAP class mapping and explicit NOT TESTED entries for manufacturer mapping / QIP-R10.2 and CAP-06 without Rust.
  - progress/qip-qip-r10-1.md: this report.
EVIDENCE:
  - command (with Rust): cargo build --workspace; .venv/bin/python -m pytest conformance/ -q -rs ; .venv/bin/python -m pytest -q
  - command (without Rust): target/debug/quberon-secure-core-cli temporarily moved aside and PATH=/usr/bin:/bin:/usr/sbin:/sbin .venv/bin/python -m pytest conformance/ -q -rs ; same PATH .venv/bin/python -m pytest -q ; binary restored afterwards
  - command: import check in empty mktemp cwd: PYTHONPATH=<repo> .venv/bin/python -c "import app.main" -> import ok, 0 files created in cwd
  - toolchain: Python 3.11.15 (.venv from requirements.txt), cargo 1.99.1 (5f94df478 2026-08-27) (Homebrew), pytest from requirements.txt
  - host: Quberon1.local, Darwin 24.3.0 arm64 (uname: Darwin Quberon1.local 24.3.0 Darwin Kernel Version 24.3.0: Thu Jan 2 20:22:58 PST 2025; root:xnu-11215.81.4~3/RELEASE_ARM64_T8132 arm64)
  - UTC: 2026-11-06T11:34:14Z (evidence run timestamp; conformance runs immediately before)
  - raw output path: /tmp/qip-r10-evidence/conformance-with-rust.txt, /tmp/qip-r10-evidence/conformance-without-rust.txt, /tmp/qip-r10-evidence/full-with-rust.txt, /tmp/qip-r10-evidence/full-without-rust.txt, /tmp/qip-r10-evidence/fail-direction.txt, /tmp/qip-r10-evidence/import-app-main.txt (local to this host/session; verbatim tails below)
  - raw output, with Rust, conformance (verbatim tail):
      34 passed, 1 warning in 5.27s
  - raw output, with Rust, full suite (verbatim tail):
      217 passed, 2 warnings in 42.71s
  - raw output, without Rust, conformance (verbatim):
      ...............s.................s                                       [100%]
      SKIPPED [2] conformance/test_conformance.py:26: NOT TESTED in this run: secure-core binary unavailable, so the authorized reset path cannot be exercised
      32 passed, 2 skipped, 1 warning in 4.82s
    (2 skipped = QIP-LATCH-03 and QIP-CAP-06, both NOT TESTED in that mode, never passes)
  - raw output, without Rust, full suite (verbatim tail):
      204 passed, 13 skipped, 2 warnings in 38.82s
  - raw output, CAP subset without Rust before cargo build (verbatim tail):
      5 passed, 1 skipped, 28 deselected, 1 warning in 0.80s (skipped = QIP-CAP-06)
  - raw output, fail-direction subset -k "DEG or STATE_01" (verbatim tail):
      4 passed, 30 deselected, 1 warning in 0.79s
  - raw output, import check: import ok; files created in tmp cwd: 0
TESTS (both modes):
  - with Rust: conformance 34 passed; full suite 217 passed. Exit gate python -m pytest conformance/ -q exits 0 in this mode.
  - without Rust (binary aside + cargo-free PATH): conformance 32 passed, 2 skipped (QIP-LATCH-03, QIP-CAP-06 NOT TESTED); full suite 204 passed, 13 skipped. The QIP-CAP-01..05 declarations are still probed and pass in this mode; QIP-CAP-06's admin-reset clearing branch is NOT TESTED without Rust, not a pass.
STILL NOT TRUE:
  - QIP-R10.1 is NOT traced in docs/specs/intervention-profile/QIP-v0.1.md Section 11: that row still reads UNIMPLEMENTED and this node did not (and may not) amend it. QIP-CAP-01..06 are candidate trace IDs for the profile owner, nothing more.
  - No manufacturer/capability mapping exists, was observed, or is tested: research/humanoids registry api-surfaces had no observed manufacturer interface at gate zero, no real-robot adapter exists in conformance/, and the only declaration probed is the in-repo SIMULATION adapter with manufacturer_mapping explicitly None.
  - QIP-R10.2 remains UNIMPLEMENTED/untested. Capability negotiation with any manufacturer, vendor stop/status/reset names, stop categories, timing, authentication and reset semantics of any real controller are all untested.
  - Without the Rust binary, QIP-CAP-06 (and QIP-LATCH-03) are NOT TESTED; the with-Rust pass does not transfer to no-Rust runs.
  - Nothing here is certification, standards conformance, physical-safety, latency, or regulatory-compliance evidence; SIMULATED_STOPPED is simulator vocabulary, not a physical state claim (QIP-R11.2).
NEEDS A HUMAN DECISION:
  - Profile owner decision on whether QIP-CAP-01..06 (passing, with raw output above, on merged main after this PR lands) satisfy QIP-R10.1 (OBSERVE) sufficiently to amend QIP-v0.1.md Section 11 under its amendment procedure. Until then R10.1 stays UNIMPLEMENTED; partial coverage must not be rounded up. This node makes no such amendment.
    handoff: docs/specs/intervention-profile/QIP-v0.1.md needs Section 11 QIP-R10.1 traceability amendment (UNIMPLEMENTED -> candidate QIP-CAP-01..06, only after the amendment procedure's fetch/grep/raw-output verification on merged main) because a work node may not amend QIP traceability itself and that procedure belongs to the profile owner
