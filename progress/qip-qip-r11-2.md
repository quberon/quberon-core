NODE: qip-qip-r11-2 (QIP-R11.2 OBSERVE)
TIER: 1
BRANCH: node/qip-qip-r11-2 (off origin/main 7fd9ea5)
COMMITS: c553d85 test(conformance): record QIP-R11.2 as explicitly untestable; plus this progress commit (hash in PR / final report)
STATUS: complete for this node's permitted scope — QIP-R11.2 recorded as EXPLICITLY UNTESTABLE, not traced. It remains UNIMPLEMENTED in QIP-v0.1.md Section 11; this node did not and may not amend that table.

CHANGED (owned paths only):
- conformance/test_qip_r11_2_untestable.py (new): one permanently skipped test,
  test_QIP_R11_2_representation_prohibition_is_not_adapter_testable, whose
  docstring/skip reason give the full untestability argument. Skipped = NOT
  TESTED, never a pass, never a trace.
- conformance/README.md: NOT TESTED section gains an explicit QIP-R11.2
  EXPLICITLY UNTESTABLE bullet with the same reasoning.
- progress/qip-qip-r11-2.md: this file.
No file outside conformance/** and progress/qip-qip-r11-2.md was changed.
No handoff line was needed.

WHY UNTESTABLE (not merely untested, and not partially traced):
QIP-R11.2: "Passing project or profile tests MUST NOT be represented as
standards conformance, certification, or physical safety validation."
1. No observable surface: conformance/adapter_interface.py (AdapterUnderTest /
   NeutralResult) exposes no operation that makes, returns, or enumerates
   representations or claims, so no adapter call can observe compliance or
   violation.
2. Unbounded universe: representations can occur in any document, PR, issue,
   external statement, wording, medium, or future artefact; compliance is a
   property of human editorial/governance conduct, not system behaviour.
3. Any substitute is partial: grepping enumerated repo files/phrases covers
   only that instant and set, cannot reliably separate a claim from its
   negation ("NOT standards conformance" is compliant), and misses
   paraphrase and out-of-repo claims. Per instruction, partial coverage
   stays UNIMPLEMENTED and is never rounded up; hence no grep test was
   added as evidence.

EVIDENCE (command, toolchain, host, UTC, raw output path):
- Host: Darwin Quberon1.local 24.3.0 arm64 (macOS 15.3.1); Python 3.11.15
  (.venv from requirements.txt); cargo 1.99.1 (Homebrew); 2026-11-06T14:20Z+.
- cargo build --workspace -> Finished dev profile; target/debug/quberon-secure-core-cli present.
- Raw outputs (uncommitted, on this host): /tmp/qip-r11-2-evidence/
  with-rust-conformance.txt, with-rust-full.txt,
  without-rust-conformance.txt, without-rust-full.txt.
- Clean-clone verification: see below (filled before PR).

TESTS (both modes):
- With Rust binary:
  .venv/bin/python -m pytest conformance/ -q -rs
  -> 28 passed, 1 skipped, 1 warning in 4.25s. The 1 skip is exactly
  QIP-R11.2 EXPLICITLY UNTESTABLE (skip reason quoted in README/test file).
  .venv/bin/python -m pytest -q -> 211 passed, 1 skipped, 2 warnings in 39.12s.
- Without Rust binary (binary temporarily moved aside, then restored):
  .venv/bin/python -m pytest conformance/ -q -rs
  -> 27 passed, 2 skipped, 1 warning in 3.74s (QIP-LATCH-03 NOT TESTED:
  secure-core binary unavailable; plus QIP-R11.2 explicitly untestable).
  .venv/bin/python -m pytest -q -> 199 passed, 13 skipped, 2 warnings in 38.20s.
- Exit gate on clean clone: python -m pytest conformance/ -q exits 0
  (verified in clean-clone section below).
- import app.main creating zero files: run from an empty temp dir with
  PYTHONPATH=<worktree>; printed "import ok"; directory listing total 0.
- Both fail-direction tests in the universal gate: not present in this repo
  (no ops/gate.sh tracked); they are run for this node by ops/gate.sh
  externally per task statement. Not claimed as observed here.

STILL NOT TRUE (mandatory, non-empty):
- QIP-R11.2 is NOT traced to any passing test and did NOT become implemented;
  it stays UNIMPLEMENTED in QIP-v0.1.md Section 11.
- The new skipped test is NOT a pass, NOT coverage, and NOT evidence of
  compliance with QIP-R11.2 by any person or artefact.
- Nothing here is standards conformance, certification, or physical-safety
  validation, and no such claim is made (cf. QIP-R11.2 itself).
- Compliance of any concrete claim artefact (doc, PR, statement) with
  QIP-R11.2 has NOT been audited by this node; that requires human review
  when the artefact is made (cf. QIP-R11.1 raw-output requirements).
- QIP-R11.1 and QIP-R11.3 remain UNIMPLEMENTED and untouched.
- No manufacturer interface (R10), physical stopping, latency, or
  regulatory claim is supported by this repository or this node.

NEEDS A HUMAN DECISION:
- Profile owner only: whether, and under what human-review procedure for
  concrete claim artefacts, QIP-R11.2's Section 11 status should ever change,
  via the Section 11 amendment procedure in QIP-v0.1.md. A work node may not
  make that amendment. Recommendation from evidence above: keep UNIMPLEMENTED
  with the reason now recorded in conformance/, unless the owner defines a
  review-based (non-test) evidence class for it.
