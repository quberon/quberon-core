# Node qip-qip-r11-1 progress

NODE: qip-qip-r11-1
TIER: 1
BRANCH: node/qip-qip-r11-1
COMMITS: see git log on branch node/qip-qip-r11-1 (this file is included in the node's commit; no commit hash is self-referenced)
STATUS: done as explicit-untestable recording; NOT a trace. QIP-R11.1 remains UNIMPLEMENTED.
CHANGED:
- conformance/adapter_interface.py — added QIP_CLASSES, validate_class_claim() (shape-only validator: named class, non-empty profile version, distinct non-empty test IDs, non-empty raw_output mentioning each ID; its docstring states it cannot verify raw-output authenticity, summary-vs-raw distinction, or cumulative class satisfaction), neutral AdapterUnderTest.class_claim() readout (default None, must be claimant-sourced, never adapter-hardcoded), and class_claim_available=False capability default.
- conformance/quberon_adapter.py — explicitly reports class_claim_available=False and class_claim() is None, because quberon-core exposes no class-claim artifact (probe below). No claim or non-claim was fabricated in the adapter.
- conformance/test_conformance.py — appended QIP-CLAIM-01 (append-only stable ID; no renumbering) as the QIP-R11.1 test. It is capability-gated and skips as NOT TESTED on quberon-core. Its non-skip branch (validator passes, each named ID prefixes an existing test function in the suite) was exercised against a stub adapter in-session and passed; all six malformed stub claims were rejected (below). A stub pass is form-only and is NOT a trace.
- conformance/README.md — documents QIP-R11.1 / QIP-CLAIM-01 in NOT TESTED with the full reason.
- progress/qip-qip-r11-1.md — this report.

Why QIP-R11.1 is explicitly untestable here, not traced:
QIP-R11.1 (QIP-v0.1.md Section 10/R11) requires a class claim to name the class, this profile version, and the exact test identifiers relied on, accompanied by the raw output of those tests (a summary does not satisfy it). (1) No class claim exists to validate: QIP-v0.1 states "In v0.1 no QIP class is claimed", and the probe below shows quberon-core's status body has no class/profile_version/claim field and capabilities() exposed no claim surface. Absence of a claim is not a passing claim-form test, and hardcoding a claim/non-claim in the adapter would fabricate the artifact. (2) Even with a claimant-sourced artifact, this suite could check only form: it cannot verify the raw output is genuine/unedited output of the named tests run against the claimed profile version, cannot reliably distinguish raw output from a summary by shape, cannot see claims made in documents/PRs/external text outside the adapter surface, and cannot verify satisfaction of the named class's cumulative MUSTs (several QIP requirements, including all of R10 and R11 itself, remain UNIMPLEMENTED). That is partial coverage, which per the node rule and QIP-v0.1 Section 11 stays UNIMPLEMENTED and is never rounded up to a trace. This node does not amend QIP traceability: Section 11 amendment belongs to the profile owner.

EVIDENCE (command, toolchain, host, UTC, raw output path):
Commands:
  python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
  cargo build --workspace   (with-Rust mode; binary target/debug/quberon-secure-core-cli)
  .venv/bin/python -m pytest conformance/ -q -rs   (with Rust; exit gate form .venv/bin/python -m pytest conformance/ -q also run, exit 0)
  .venv/bin/python -m pytest -q   (full suite, with Rust)
  binary moved aside + PATH=/usr/bin:/bin:/usr/sbin:/sbin .venv/bin/python -m pytest conformance/ -q -rs and full suite (without Rust; binary restored after)
  probe script via make_quberon_adapter; stub-adapter exercise of QIP-CLAIM-01 non-skip branch; import check in empty mktemp cwd
Toolchain: Python 3.11.15, pytest 8.3.4 (requirements.txt), cargo 1.99.1 (5f94df478 2026-08-27) (Homebrew), rustc 1.99.1 (58cf8f9c3 2026-10-13) (Homebrew)
Host: Darwin Quberon1.local 24.3.0 Darwin Kernel Version 24.3.0: Thu Jan  2 20:22:58 PST 2025; root:xnu-11215.81.4~3/RELEASE_ARM64_T8132 arm64
UTC: 2026-11-06T13:38:47Z (with-Rust conformance run)
Raw output path: /tmp/qip-r11-1-evidence/conformance-with-rust.txt, conformance-without-rust.txt, full-with-rust.txt, full-without-rust.txt, probe.txt, stub.txt (local to this host/session; verbatim excerpts below are the durable record)

Raw output — conformance, WITH Rust (cargo build --workspace done first):
............................s                                            [100%]
SKIPPED [1] conformance/test_conformance.py:264: NOT TESTED: QIP-R11.1 requires a class-claim artifact sourced from the claimant/system under test; this adapter reports class_claim_available=False (no class is claimed in QIP-v0.1 and no claim surface is exposed), so claim form -- class, profile version, exact test IDs and accompanying raw output -- cannot be verified
28 passed, 1 skipped, 1 warning in 4.56s

Raw output — conformance, WITHOUT Rust (binary moved aside, cargo-free PATH):
...............s............s                                            [100%]
SKIPPED [1] conformance/test_conformance.py:27: NOT TESTED in this run: secure-core binary unavailable, so the authorized reset path cannot be exercised
SKIPPED [1] conformance/test_conformance.py:264: NOT TESTED: QIP-R11.1 requires a class-claim artifact sourced from the claimant/system under test; this adapter reports class_claim_available=False (no class is claimed in QIP-v0.1 and no claim surface is exposed), so claim form -- class, profile version, exact test IDs and accompanying raw output -- cannot be verified
27 passed, 2 skipped, 1 warning in 4.25s

Raw output — full suite (tails): with Rust: 211 passed, 1 skipped, 2 warnings in 40.75s ; without Rust: 199 passed, 13 skipped, 2 warnings in 38.31s
Raw output — fail-direction subset -k "DEG or STATE_01": 4 passed, 25 deselected, 1 warning in 0.70s
Raw output — exit gate: .venv/bin/python -m pytest conformance/ -q -> 28 passed, 1 skipped, 1 warning in 4.66s (exit 0, binary restored)
Raw output — import check (empty mktemp cwd, empty before and after): import ok; total 0 entries in cwd

Raw output — probe (no claim surface):
status body keys: ['actor', 'adapter_mode', 'capabilities', 'csrf_token', 'observed_state', 'persistence_ok', 'robot_id', 'role', 'safety_notice', 'secure_core_available', 'secure_core_message', 'server_time_utc', 'stop_latched']
capabilities(): {'secure_core_available': False, 'adapter_mode_simulation': True, 'persistence_failure_injectable': True, 'secure_core_refusal_injectable': True, 'class_claim_available': False}
any class/profile keys in status: {}

Raw output — QIP-CLAIM-01 non-skip branch against stub adapters:
stub good-claim non-skip branch: PASS
bad[0]: validator_errors=['claimed_class does not name a QIP class', 'profile_version is missing or empty', 'test_ids is not a non-empty list of distinct identifiers', 'raw_output is missing or empty (a summary does not satisfy QIP-R11.1)'] test=rejected
bad[1]: validator_errors=['raw_output does not mention QIP-ID-01'] test=rejected
bad[2]: validator_errors=['test_ids is not a non-empty list of distinct identifiers'] test=rejected
bad[3]: validator_errors=['claimed_class does not name a QIP class'] test=rejected
bad[4]: validator_errors=['profile_version is missing or empty'] test=rejected
bad[5]: validator_errors=[] test=rejected (unknown QIP-NOPE-99 rejected by suite-ID existence check)

TESTS (both modes):
- With Rust: conformance 28 passed, 1 skipped (QIP-CLAIM-01 NOT TESTED). Full suite 211 passed, 1 skipped.
- Without Rust: conformance 27 passed, 2 skipped (QIP-CLAIM-01 NOT TESTED; QIP-LATCH-03 NOT TESTED, pre-existing). Full suite 199 passed, 13 skipped.
- Exit gate `python -m pytest conformance/ -q` exits 0 in both modes (run as .venv/bin/python -m pytest conformance/ -q / -q -rs; -rs only adds skip reasons).
- Clean-clone check of pushed branch 1dda3a7 (fresh clone, fresh .venv, no Rust binary built): 27 passed, 2 skipped (QIP-LATCH-03 and QIP-CLAIM-01, both NOT TESTED), exit 0. PR: https://github.com/quberon/quberon-core/pull/69

STILL NOT TRUE:
- QIP-R11.1 is not verified by any passing test; QIP-CLAIM-01 skips in every quberon-core run and QIP-R11.1 must remain UNIMPLEMENTED in QIP-v0.1 Section 11.
- No QIP class claim exists in QIP-v0.1, and no claimant-sourced class-claim artifact (class + profile version + exact test IDs + raw output) is exposed by quberon-core or any adapter surface in this repo.
- The stub-adapter pass verifies claim form only: it does not verify raw-output authenticity/provenance, that named tests actually passed on the claimed version, summary-vs-raw distinction, claims made outside the adapter surface, or satisfaction of any class's cumulative MUSTs.
- No QIP conformance class is claimed; nothing here is certification, standards conformance, physical-safety, latency, or regulatory-compliance evidence.

NEEDS A HUMAN DECISION:
- Profile owner: whether/when any QIP class claim is ever made, and any Section 11 traceability amendment for QIP-R11.1 — only after a future QIP-CLAIM-01 passes (not skips) against a claimant-sourced claim artifact, following the Section 11 amendment procedure. This node made no traceability amendment.
- Implementation owner: whether a class-claim artifact should exist on any system surface at all is a design decision outside this node's owned paths.

handoff: docs/specs/intervention-profile/QIP-v0.1.md needs a Section 11 traceability decision for QIP-R11.1 by the profile owner because a work node may not amend QIP traceability itself and QIP-R11.1 must stay UNIMPLEMENTED until QIP-CLAIM-01 passes rather than skips against a claimant-sourced claim artifact
