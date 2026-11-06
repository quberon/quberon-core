NODE: qip-qip-r10-2
TIER: 1
BRANCH: node/qip-qip-r10-2
COMMITS: 12e1feb (plus this report-hash commit if present; see PR https://github.com/quberon/quberon-core/pull/64)
STATUS: partial
CHANGED:
  - conformance/adapter_interface.py: added AdapterUnderTest.manufacturer_mapping_declaration() (default NotImplementedError, capability manufacturer_mapping_declared=False, so silence is NOT TESTED never a pass) and validate_manufacturer_mapping_declaration() shape validator for QIP-R10.2.
  - conformance/quberon_adapter.py: implemented explicit non-claim declaration (mapping_claimed=False, mappings=[], basis simulation_only) and manufacturer_mapping_declared=True capability.
  - conformance/test_conformance.py: appended QIP-CAP-01 (explicit non-claim by reference adapter) and QIP-CAP-02 (fail-direction: 8 unsourced/contradictory/missing declarations rejected, well-formed claim and non-claim shapes accepted as shapes). No existing ID renumbered.
  - conformance/README.md: CAP class note; QIP-R10.2 provenance recorded as explicitly untestable in-suite under NOT TESTED.
  - progress/qip-qip-r10-2.md: this report.
EVIDENCE:
  command: /tmp/qip-r10-venv/bin/python -m pytest conformance/ -q -rs (and full-suite, CAP-only, and import checks below)
  toolchain: Python 3.14.9 (/tmp/qip-r10-venv created from requirements.txt), cargo/rustc 1.99.1 Homebrew for with-Rust mode
  host: Quberon1.local (macOS 15.3.1)
  UTC: 2026-11-06T12:43:53Z
  raw output path: raw lines are reproduced verbatim below in this file; ephemeral run logs were at /tmp/qip-evidence/{with-rust,full-with-rust,conformance-without-rust,full-without-rust,cap}.txt on the host above (not tracked, not a clean-clone artifact)
  raw output (verbatim tail lines):
    with-rust conformance: "30 passed, 1096 warnings in 4.44s" / "EXIT:0"
    with-rust full: "213 passed, 3038 warnings in 44.14s" / "EXIT:0"
    without-rust conformance: "29 passed, 1 skipped, 1096 warnings in 3.86s" / "EXIT:0" / "SKIPPED [1] conformance/test_conformance.py:24: NOT TESTED in this run: secure-core binary unavailable, so the authorized reset path cannot be exercised"
    without-rust full: "201 passed, 12 skipped, 2855 warnings in 41.51s" / "EXIT:0" (12 skips all Rust-CLI-not-built, listed in run log)
    CAP-only: "2 passed, 28 deselected, 37 warnings in 0.14s" / "EXIT:0" (with Rust); repeated without Rust on PATH: "2 passed, 28 deselected, 37 warnings in 0.13s"
    import check: PYTHONPATH=<worktree> python -c "import app.main" in empty /tmp/qip-importcheck -> "import ok" and diff before/after file lists empty -> "ZERO_FILES_CREATED"
TESTS (both modes):
  with Rust (cargo build --workspace, target/debug/quberon-secure-core-cli present): conformance 30 passed; full suite 213 passed. QIP-CAP-01 and QIP-CAP-02 passed (not skipped).
  without Rust (target/ moved aside and PATH=/usr/bin:/bin:/usr/sbin:/sbin, QUBERON_SECURE_CORE_BIN unset; restored afterwards): conformance 29 passed, 1 skipped (QIP-LATCH-03 NOT TESTED); full suite 201 passed, 12 skipped. CAP tests do not depend on the Rust binary and passed in this mode as part of the 29 (CAP-only run above was with Rust present; without-Rust conformance count 29 = 30 minus LATCH-03 skip includes both CAP tests).
  exit gate: python -m pytest conformance/ -q exits 0 in both modes.
STILL NOT TRUE:
  - QIP-R10.2 is NOT fully traced and remains UNIMPLEMENTED in docs/specs/intervention-profile/QIP-v0.1.md section 11. CAP-01/02 cover only the testable negative slice (explicit non-claim; claimed mappings must carry kind/interface/recorded source). Partial coverage is not rounded up to a trace.
  - The provenance half of R10.2 is explicitly untestable in this suite: no runtime test can verify a cited source is genuinely manufacturer-provided, current, or applicable to a product/firmware. An adapter citing a plausible false source would pass the CAP shape check. That verification requires recorded manufacturer-material review outside conformance/.
  - QIP-R10.1 is not traced by CAP: a mapping non-claim is not a declaration of supported kinds, target scope, status values, or reset semantics.
  - No real manufacturer interface, mapping, capability negotiation, physical stop/reset, certification, physical-safety, latency, or regulatory-compliance claim is supported by this work or this repository.
NEEDS A HUMAN DECISION:
  - Profile owner decision under QIP-v0.1 section 11 amendment procedure: whether QIP-CAP-01/02 (with the raw output above, verified by grep on merged main and a passing not-skipped run) are sufficient to change QIP-R10.2 from UNIMPLEMENTED, or whether it must stay UNIMPLEMENTED until provenance verification outside the suite exists. This node does not amend that traceability.
  - If a trace is ever granted, its scope wording needs owner approval so it cannot be read as covering provenance or any real manufacturer mapping.
