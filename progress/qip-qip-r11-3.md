NODE: qip-qip-r11-3
TIER: 1
BRANCH: node/qip-qip-r11-3
COMMITS: see final message / git log on this branch (work not yet committed at time of writing this file; commit hash recorded in final message)
STATUS: done (explicitly-untestable disposition recorded; QIP-R11.3 stays UNIMPLEMENTED, not traced)
CHANGED:
  - conformance/test_conformance.py (QIP-R11.3 section: passing untestable-basis test + always-skipped explicit UNTESTABLE record; header note)
  - conformance/README.md (EXPLICITLY UNTESTABLE section for QIP-R11.3)
  - progress/qip-qip-r11-3.md (this report)
EVIDENCE:
  command (with Rust): .venv/bin/python -m pytest conformance/ -q -rs
  command (without Rust core): QUBERON_SECURE_CORE_BIN=/nonexistent/quberon-secure-core-cli .venv/bin/python -m pytest conformance/ -q -rs
    (binary hidden via the app's existing QUBERON_SECURE_CORE_BIN override, simulating no secure-core binary; cargo itself was present on PATH for this local run -- the universal gate's fresh-clone no-Rust run is ops/gate.sh's, not observed here)
  command (exit gate): .venv/bin/python -m pytest conformance/ -q
  toolchain: Python 3.11.15 (.venv/bin/python, /Users/quberon1/.local/bin/python3.11); cargo 1.99.1 (Homebrew) for with-Rust build (cargo build --workspace, target/debug/quberon-secure-core-cli present)
  host: Darwin Quberon1.local 24.3.0 arm64 (macOS 15.3.1)
  UTC: 2026-11-06T14:47:45Z (runs immediately before this timestamp)
  raw output path: this file, progress/qip-qip-r11-3.md (raw outputs reproduced verbatim below; no separate log file is committed by this node)

  RAW OUTPUT (with Rust, -q -rs):
  .............................s                                           [100%]
  =============================== warnings summary ===============================
  .venv/lib/python3.11/site-packages/starlette/testclient.py:40
    /Users/quberon1/Library/Application Support/Quberon/worktrees/qip-qip-r11-3/.venv/lib/python3.11/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
      _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

  -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
  =========================== short test summary info ============================
  SKIPPED [1] conformance/test_conformance.py:309: UNTESTABLE: QIP-R11.3 is explicitly untestable through the neutral AdapterUnderTest surface -- (a) versioning of normative/class/traceability changes is a profile-document process obligation with no neutral operation to observe it; (b) no claim/class/profile-version value is exposed and no QIP class is claimed in v0.1, so no stated version can be checked; (c) no superseded profile version or claim surface exists on which a superseded claim or its label could be constructed or observed. QIP-R11.3 stays UNIMPLEMENTED; this skip is not a pass and not a trace.
  29 passed, 1 skipped, 1 warning in 4.53s

  RAW OUTPUT (without Rust core, -q -rs):
  ...............s.............s                                           [100%]
  =============================== warnings summary ===============================
  .venv/lib/python3.11/site-packages/starlette/testclient.py:40
    /Users/quberon1/Library/Application Support/Quberon/worktrees/qip-qip-r11-3/.venv/lib/python3.11/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
      _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

  -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
  =========================== short test summary info ============================
  SKIPPED [1] conformance/test_conformance.py:26: NOT TESTED in this run: secure-core binary unavailable, so the authorized reset path cannot be exercised
  SKIPPED [1] conformance/test_conformance.py:309: UNTESTABLE: QIP-R11.3 is explicitly untestable through the neutral AdapterUnderTest surface -- (a) versioning of normative/class/traceability changes is a profile-document process obligation with no neutral operation to observe it; (b) no claim/class/profile-version value is exposed and no QIP class is claimed in v0.1, so no stated version can be checked; (c) no superseded profile version or claim surface exists on which a superseded claim or its label could be constructed or observed. QIP-R11.3 stays UNIMPLEMENTED; this skip is not a pass and not a trace.
  28 passed, 2 skipped, 1 warning in 4.22s

  RAW OUTPUT (exit gate, -q):
  .............................s                                           [100%]
  29 passed, 1 skipped, 1 warning in 4.74s (DeprecationWarning block as above)

  BASIS PROBE (observed before writing the tests, .venv/bin/python driving conformance.quberon_adapter.make_quberon_adapter):
  status_code 200
  status keys ['actor', 'adapter_mode', 'capabilities', 'csrf_token', 'observed_state', 'persistence_ok', 'robot_id', 'role', 'safety_notice', 'secure_core_available', 'secure_core_message', 'server_time_utc', 'stop_latched']
  capabilities {'secure_core_available': False, 'adapter_mode_simulation': True, 'persistence_failure_injectable': True, 'secure_core_refusal_injectable': True}
  any qip/profile/version/claim key: []

TESTS (both modes):
  with Rust: 29 passed, 1 skipped (skip = QIP-R11.3 explicit UNTESTABLE record only; QIP-LATCH-03 passed with target/debug core built)
  without Rust core: 28 passed, 2 skipped (skips = QIP-LATCH-03 NOT TESTED no-core + QIP-R11.3 explicit UNTESTABLE)
  Full suite, both fail-direction tests, and import-app.main-zero-files were NOT run by this node; they are the universal gate run by ops/gate.sh. No claim is made about them here.
  Clean-clone verification (observed after commit 074c884): git clone --branch node/qip-qip-r11-3 to /tmp/qip-r11-3-clone, python3.11 venv + pip install -r requirements.txt, then in that clone: .venv/bin/python -m pytest conformance/ -q = 28 passed, 2 skipped (no Rust core in clean clone: QIP-LATCH-03 NOT TESTED + QIP-R11.3 UNTESTABLE), exit 0.

DISPOSITION DETAIL:
  QIP-R11.3 text (QIP-v0.1.md R11): "Changes to normative text, class assignment, or traceability status MUST be versioned with the profile; an implementation MUST state the profile version it claims against, and a claim against a superseded version MUST be labelled as such."
  (a) Versioning-of-changes clause: profile-document/owner process obligation; no AdapterUnderTest operation can make/observe/inspect such a change or its history; a repo-file assertion would break suite implementation-neutrality. Untestable here.
  (b) State-profile-version clause: status/capabilities expose no claim/class/profile-version value (basis probe + passing basis test), and QIP-v0.1 claims no class in v0.1, so there is no claim whose stated version could be checked. Untestable here.
  (c) Superseded-claim labelling clause: only profile v0.1 exists; no superseded version and no claim surface on which to construct a superseded claim or observe its label. Untestable here.
  Partial assertions (e.g. only (b)'s absence, or the QIP header showing "v0.1") were NOT rounded up to a trace. QIP-R11.3 stays UNIMPLEMENTED.

STILL NOT TRUE:
  - QIP-R11.3 is not implemented, not traced, and not passed; the only new passing test asserts absence of a testable surface, which is not R11.3 conformance.
  - No implementation in this repo states a QIP profile version it claims against, and no QIP class is claimed.
  - No superseded profile version exists, so superseded-claim labelling has never been exercised.
  - Whether future normative/class/traceability changes will in fact be versioned with the profile is a future owner-process property; nothing in this node observes or guarantees it.
  - Full-suite (both Rust modes), fail-direction, and import-side-effect results were not observed by this node.
  - No certification, physical-safety, latency, or regulatory-compliance claim is supported by this repository or by this node.

NEEDS A HUMAN DECISION:
  - Profile owner: amend QIP-v0.1.md Section 11 for QIP-R11.3 via the Section 11 amendment procedure (this work node may not), either keeping UNIMPLEMENTED with this explicit-untestable reason or defining the future testable surface (neutral (class, profile-version) claim surface + current/superseded fixtures + defined superseded label).
handoff: docs/specs/intervention-profile/QIP-v0.1.md needs Section 11 QIP-R11.3 row kept UNIMPLEMENTED with the explicit-untestable reason recorded in conformance/test_conformance.py and conformance/README.md because a work node may not amend QIP traceability itself and Section 11 defines the amendment procedure as belonging to the profile owner
