NODE: qip-qip-r7-4 (QIP-R7.4 AUTHORIZE, QIP-DEG-03)
TIER: 1
BRANCH: node/qip-qip-r7-4
COMMITS: see git log on this branch (this file is committed with the conformance change; final hash reported in the PR/final message, not self-referenced here)
STATUS: partial

What was traced, and what was not:
- QIP-R7.4 text (docs/specs/intervention-profile/QIP-v0.1.md, not edited):
  "When a reachable authority refuses, the adapter MUST NOT be invoked,
  the latch MUST be retained, and the observed state MUST be reported
  as UNKNOWN unless independently observed."
- Before this node, QIP-DEG-03 asserted refusal status/UNKNOWN/latch,
  but adapter non-invocation was only inferred from those outcomes
  (conformance/README.md listed it as NOT TESTED via counter). Partial
  coverage was therefore not a trace for the non-invocation clause.
- This node makes non-invocation directly observable in the simulator
  scope of QIP-DEG-03, so QIP-R7.4's three clauses are each directly
  asserted for the in-repo simulator: (1) refused STOP increments the
  directly counted SimulatedRobotAdapter.stop invocation count by 0
  (with a positive control: a normal STOP increments it by exactly 1);
  (2) latch was engaged before the refusal and is retained after;
  (3) command/observed are UNKNOWN (the no-independent-observation case).
- QIP-v0.1 Section 11 still lists QIP-R7.4 as UNIMPLEMENTED. This node
  does not amend it (see NEEDS A HUMAN DECISION / handoff below).

CHANGED (owned paths only):
- conformance/adapter_interface.py: stop_invocation_count() neutral
  observation hook; None = cannot observe = NOT TESTED for
  non-invocation, never an inferred pass.
- conformance/quberon_adapter.py: in-process counting wrapper around
  SimulatedRobotAdapter.stop (conformance process only, no app/**,
  integrations/**, or other control-path edit); stop_invocation_count()
  returns the count.
- conformance/test_conformance.py: QIP-DEG-03 strengthened only (stable
  ID unchanged, no renumbering): positive-control increment, refused
  STOP zero increment, pre-existing latch precondition. Skips (NOT
  TESTED) if invocation count is unobservable.
- conformance/README.md: records the direct-count scope and keeps the
  remaining gaps as NOT TESTED (below).
- progress/qip-qip-r7-4.md: this file.

EVIDENCE:
- Host: Mac, Darwin 24.3.0 arm64 (uname: Darwin Mac 24.3.0 Darwin Kernel Version 24.3.0 arm64)
- Toolchain: Python 3.11.15 (.venv from requirements.txt), cargo 1.99.1, rustc 1.99.1
- UTC run window: 2026-11-06T16:37Z-16:41Z (date -u 2026-11-06T16:41:19Z at import check)
- Raw output files (local run, not committed): /tmp/qip-r7-4-evidence/deg03-with-rust.txt,
  conformance-with-rust.txt, conformance-without-rust.txt, full-with-rust.txt,
  full-without-rust.txt, fail-direction-with-rust.txt,
  fail-direction-without-rust.txt, import-zero.txt
- Raw output (verbatim tail lines, also reproduced below in TESTS).

TESTS (both modes):
With Rust (cargo build --workspace built target/debug/quberon-secure-core-cli):
  command: .venv/bin/python -m pytest conformance/test_conformance.py::test_QIP_DEG_03_persistence_failure_and_reachable_refusal -q -rs
  raw:
    1 passed, 1 warning in 0.44s
  command: .venv/bin/python -m pytest conformance/ -q -rs
  raw:
    28 passed, 1 warning in 4.29s
  command: .venv/bin/python -m pytest -q
  raw:
    211 passed, 2 warnings in 39.22s
  command: .venv/bin/python -m pytest tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter -q
  raw:
    2 passed, 1 warning in 0.24s
Without Rust (target/debug/quberon-secure-core-cli temporarily hidden and PATH=/usr/bin:/bin:/usr/sbin:/sbin, restored after):
  command: .venv/bin/python -m pytest conformance/ -q -rs
  raw:
    SKIPPED [1] conformance/test_conformance.py:23: NOT TESTED in this run: secure-core binary unavailable, so the authorized reset path cannot be exercised
    27 passed, 1 skipped, 1 warning in 3.83s
    (the single skip is QIP-LATCH-03; QIP-DEG-03 passed in this mode)
  command: .venv/bin/python -m pytest -q
  raw:
    199 passed, 12 skipped, 2 warnings in 37.11s
  command: .venv/bin/python -m pytest tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter -q
  raw:
    2 passed, 1 warning in 0.24s
Import side-effect check (empty temp dir, PYTHONPATH to this repo):
  command: python -c "import app.main; print('import ok')" then find <dir> -type f | wc -l
  raw:
    import ok
           0

STILL NOT TRUE:
- QIP-R7.4 is not traced in docs/specs/intervention-profile/QIP-v0.1.md: Section 11 still reads UNIMPLEMENTED for QIP-R7.4, and this node has not changed that. No QIP class (including AUTHORIZE) is claimed.
- Adapter non-invocation is directly counted only for the in-process SimulatedRobotAdapter in the conformance reference adapter. Non-invocation of any real or manufacturer adapter is NOT TESTED.
- The reachable refusal is injected with a stub authority raising SecureCoreRejected; a real Rust secure-core rejection of a signed envelope, signing/verification, and sequence/epoch behaviour under refusal are NOT TESTED.
- QIP-R7.4's "unless independently observed" branch is explicitly untestable in this adapter: no independent observation source exists to inject, so only the UNKNOWN (no independent observation) case is passed; the independent-observation case is NOT TESTED, not passed.
- Real persistence failure (injection flips the app's degraded flag, not storage corruption), restart recovery, physical stopping/response time, load/starvation, network partition, real-controller behaviour, audit retention/clock trust/custody, recognizer qualification, and any certification, physical-safety, latency, or regulatory-compliance claim are NOT TESTED / not supported by this repository.

NEEDS A HUMAN DECISION:
- Profile owner: run the QIP-v0.1 Section 11 amendment procedure (fetch, rebase, grep merged identifiers, verify passing not-skipped raw output) and decide whether QIP-R7.4 may move from UNIMPLEMENTED to QIP-DEG-03 for the simulator scope only, with the NOT TESTED branches above retained.
handoff: docs/specs/intervention-profile/QIP-v0.1.md needs Section 11 QIP-R7.4 traceability amendment by the profile owner because a work node may not amend QIP traceability itself
