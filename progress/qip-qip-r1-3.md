# Node qip-qip-r1-3 progress

NODE: qip-qip-r1-3
TIER: 1
BRANCH: node/qip-qip-r1-3
COMMITS: see git log on branch node/qip-qip-r1-3 (this file is included in the node's commit; no commit hash is self-referenced)
STATUS: done as explicit-untestable recording; NOT a trace. QIP-R1.3 remains UNIMPLEMENTED.
CHANGED:
- conformance/adapter_interface.py — added neutral declared_intervention_kinds() readout (default None) and intervention_kinds_declared capability (default False). The readout must be sourced from the system under test; an adapter-hardcoded kind list is explicitly not a declaration.
- conformance/quberon_adapter.py — explicitly reports intervention_kinds_declared=False and declared_intervention_kinds() is None, because quberon-core exposes no QIP-R10.1 intervention-kind declaration.
- conformance/test_conformance.py — appended QIP-INT-06 (append-only; no renumbering) as the QIP-R1.3 conformance test. It is capability-gated: without a system-sourced QIP-R10.1 declaration it skips as NOT TESTED, never a pass. Its non-skip branch (declaration present, undeclared kind rejected 4xx, no stop triggered, latch unchanged) was exercised against a stub adapter in-session and passed (see EVIDENCE).
- conformance/README.md — documents the QIP-INT-06 declaration surface and lists QIP-R1.3 in NOT TESTED with the reason.

Why QIP-R1.3 is explicitly untestable here, not traced:
QIP-R1.3 (QIP-v0.1.md Section 4) requires rejection of a kind "not a kind it has declared under QIP-R10.1". QIP-R10.1 is itself UNIMPLEMENTED (Section 11 table), and no system surface exposes a kind declaration: app status "capabilities" is ['plan', 'read', 'stop', 'task'] (role permissions, not intervention kinds; observed in the probe below). QIP-INT-05 covers only the audit-only kind PANIC_CANDIDATE never triggering a stop. The app does return 400 for a kind string outside its internal enum (probe below), but that is partial coverage only: it cannot distinguish rejection-because-undeclared from rejection-because-not-in-a-hardcoded-enum, cannot exercise a kind declared as unsupported, and cannot exercise a system declaring only a subset of kinds. Hardcoding that enum in the suite or adapter would fabricate the declaration. Per the node rule, partial coverage stays UNIMPLEMENTED and is not rounded up to a trace. This node does not amend QIP traceability: Section 11 amendment belongs to the profile owner.

EVIDENCE (command, toolchain, host, UTC, raw output path):
Commands:
  python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
  cargo build --workspace   (with-Rust mode; binary target/debug/quberon-secure-core-cli)
  .venv/bin/python -m pytest conformance/ -q -rs   (both modes)
  .venv/bin/python -m pytest -q   (full suite, with Rust)
  probe script via make_quberon_adapter (below)
  stub-adapter exercise of QIP-INT-06 non-skip branch (below)
Toolchain: Python 3.11.15, pytest 8.3.4 (requirements.txt), rustc 1.99.1 (58cf8f9c3 2026-10-13) (Homebrew), cargo 1.99.1 (5f94df478 2026-08-27) (Homebrew)
Host: Darwin Quberon1.local 24.3.0 Darwin Kernel Version 24.3.0: Thu Jan 2 20:22:58 PST 2025; root:xnu-11215.81.4~3/RELEASE_ARM64_T8132 arm64
UTC: 2026-11-06T10:54:11Z (with-Rust conformance run)
Raw output path: raw output is reproduced verbatim below in this file (the durable record); session scratch copies were /tmp/qip-r1-3-rust.txt, /tmp/qip-r1-3-norust.txt, /tmp/qip-r1-3-probe.txt and are not claimed as durable.

Raw output — conformance, WITH Rust (cargo build --workspace done first):
.............s...............                                            [100%]
=============================== warnings summary ===============================
.venv/lib/python3.11/site-packages/starlette/testclient.py:40
  /Users/quberon1/Library/Application Support/Quberon/worktrees/qip-qip-r1-3/.venv/lib/python3.11/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
SKIPPED [1] conformance/test_conformance.py:122: NOT TESTED: QIP-R1.3 requires a QIP-R10.1 intervention-kind declaration sourced from the system under test; this adapter reports intervention_kinds_declared=False, so rejection of undeclared kinds cannot be verified (unknown-string 400s alone are partial coverage and stay UNIMPLEMENTED)
28 passed, 1 skipped, 1 warning in 4.80s

Raw output — conformance, WITHOUT Rust (no secure-core binary present):
.............s..s............                                            [100%]
=============================== warnings summary ===============================
.venv/lib/python3.11/site-packages/starlette/testclient.py:40
  /Users/quberon1/Library/Application Support/Quberon/worktrees/qip-qip-r1-3/.venv/lib/python3.11/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
SKIPPED [1] conformance/test_conformance.py:122: NOT TESTED: QIP-R1.3 requires a QIP-R10.1 intervention-kind declaration sourced from the system under test; this adapter reports intervention_kinds_declared=False, so rejection of undeclared kinds cannot be verified (unknown-string 400s alone are partial coverage and stay UNIMPLEMENTED)
SKIPPED [1] conformance/test_conformance.py:26: NOT TESTED in this run: secure-core binary unavailable, so the authorized reset path cannot be exercised
27 passed, 2 skipped, 1 warning in 4.15s

Raw output — full suite, WITH Rust (tail):
211 passed, 1 skipped, 2 warnings in 40.84s
(the 1 skip is QIP-INT-06)

Raw output — import check (cwd /tmp/emptycwd, empty before and after):
import ok
total 0
drwxr-xr-x@  2 quberon1  wheel    64 Nov  6 11:55 .
drwxrwxrwt@ 83 root      wheel  2656 Nov  6 11:55 ..

Raw output — probe of partial behaviour (NOT coverage; run with Rust binary present):
capabilities: {'secure_core_available': True, 'adapter_mode_simulation': True, 'intervention_kinds_declared': False, 'persistence_failure_injectable': True, 'secure_core_refusal_injectable': True}
declared_intervention_kinds: None
status capabilities field: ['plan', 'read', 'stop', 'task']
NOT_A_KIND -> 400 {'detail': 'unknown intervention kind or source_status'}
RESET_LATCH -> 400 {'detail': 'unknown intervention kind or source_status'}

Raw output — QIP-INT-06 non-skip branch against a stub adapter declaring kinds:
fake-adapter non-skip branch: PASS

TESTS (both modes):
- With Rust: conformance 28 passed, 1 skipped (QIP-INT-06 NOT TESTED). Full suite 211 passed, 1 skipped.
- Without Rust: conformance 27 passed, 2 skipped (QIP-INT-06 NOT TESTED; QIP-LATCH-03 NOT TESTED, pre-existing). Full suite without Rust was not re-run locally in this node; the universal gate (ops/gate.sh) runs it externally.
- Exit gate command `python -m pytest conformance/ -q` exits 0 in both modes above (run as .venv/bin/python -m pytest conformance/ -q -rs; -rs only adds skip reasons).

STILL NOT TRUE:
- QIP-R1.3 is not verified by any passing test; QIP-INT-06 skips in every quberon-core run and QIP-R1.3 must remain UNIMPLEMENTED in QIP-v0.1 Section 11.
- No QIP-R10.1 declaration (kinds, target scope, status values, reset semantics, unsupported kinds) exists in quberon-core or in the neutral readout for it.
- The observed 400 for unknown kind strings is not evidence of declaration-relative rejection, of declared-unsupported handling, or of subset-declaration handling.
- No QIP conformance class is claimed; nothing here is certification, physical-safety, latency, or regulatory-compliance evidence.

NEEDS A HUMAN DECISION:
- Profile owner: whether/when to amend QIP-v0.1 Section 11 for QIP-R1.3 — only after a future QIP-INT-06 passes (not skips) against a system-sourced declaration, following the Section 11 amendment procedure. This node made no traceability amendment.
- Implementation owner: whether quberon-core should expose a QIP-R10.1 declaration at all (and on which surface), which is a design decision outside this node's owned paths.

handoff: app/main.py needs a system-exposed QIP-R10.1 intervention-kind declaration (supported and unsupported kinds) on a readable surface such as status because QIP-R1.3 rejection is defined relative to that declaration and no such declaration is currently exposed
handoff: docs/specs/intervention-profile/QIP-v0.1.md needs a Section 11 traceability decision for QIP-R1.3 by the profile owner because a work node may not amend QIP traceability itself and QIP-R1.3 must stay UNIMPLEMENTED until QIP-INT-06 passes rather than skips
