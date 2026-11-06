NODE: qip-qip-r3-1
TIER: 1
BRANCH: node/qip-qip-r3-1
COMMITS: see final message / git log on this branch (single node commit; hash recorded there, not self-referenced here)
STATUS: partial

TASK AS READ
QIP-R3.1 (INTERVENE) in docs/specs/intervention-profile/QIP-v0.1.md Section 11:
"UNIMPLEMENTED (no load/priority test in N4)". Instruction: trace it to a passing
conformance test or record it as explicitly untestable; partial coverage stays
UNIMPLEMENTED; never round a gap up to a trace. Section 11 amendment belongs to
the profile owner; this node does not amend QIP-v0.1.md or TRACEABILITY.md.

WHAT WAS OBSERVED BEFORE CHANGING ANYTHING
- app/main.py:270: planner capacity is a dedicated threading.BoundedSemaphore(2)
  (app.state.plan_semaphore). app/main.py:592-593: a saturated planner returns
  {"provider_status": "busy", "error": "planner concurrency limit",
  "stop_unaffected": True} non-blocking. execute_stop (app/main.py:402) never
  touches that semaphore.
- integrations/secure_core.py:98,231 (grep "try_acquire", 7 hits total): the
  PriorityRateLimiter OTHER bucket is acquired by no production caller; only
  "STOP" is acquired (SecureCoreClient.authorize_stop). Bucket isolation is
  therefore exercised only by tests/test_secure_core.py::
  test_rate_limiter_stop_isolated_from_other_traffic, a unit test, not a
  conformance test, and cannot be driven through the neutral adapter.
- Status (GET /api/robots/{id}/status) has no bounded capacity pool. The
  capacity status/task/STOP do share is Store.lock and the ASGI threadpool
  (progress/F3-stop-load.md finding 2: status+task load inflated STOP median
  ~1.1 ms to ~7.0 ms in that local harness; task load there was rejected-task
  load on the shared lock).
- loadtest/ (Wave 5 F3) is separate local simulated evidence with no
  conformance test ID; it does not close R3.1 either (its own report says so).

CHANGED (owned paths only: conformance/**, progress/qip-qip-r3-1.md)
- conformance/adapter_interface.py: appended neutral saturation point
  AdapterUnderTest.saturate_non_intervention_traffic() (raises
  NotImplementedError by default, scope explicitly planner/proposal capacity
  only) and capability "non_intervention_saturation_injectable": False in the
  default capabilities(). No existing method or ID was changed or renumbered.
- conformance/quberon_adapter.py: capability True for this adapter;
  saturate_non_intervention_traffic() holds every slot of the app's existing
  plan_semaphore for the adapter's life. Conformance-side only; no
  app/control-path code changed.
- conformance/conftest.py: appended fixture adapter_planner_saturated
  (fresh adapter + saturation, following the DEG-03 injection fixtures).
- conformance/test_conformance.py: taxonomy line QIP-INT-01..05 -> ..06
  (append only); appended test_QIP_INT_06_stop_serviced_when_planner_saturated
  with skip-guard _needs_saturation (capability False => NOT TESTED skip,
  never a pass). Test asserts, deterministically and with no timing value:
  saturated planner -> submit_proposal is 200 with provider_status "busy" and
  stop_unaffected True (bounded refusal); STOP -> 200 / ACKNOWLEDGED /
  stop_latched True; status -> 200 / latched; a further proposal after STOP
  is still "busy" (STOP neither consumed nor released planner capacity).
- conformance/README.md: new "QIP-INT-06 planner saturation" section and an
  expanded NOT TESTED entry recording the explicitly untestable remainder
  (below). This file also states QIP-R3.1 stays UNIMPLEMENTED.

RESULT FOR QIP-R3.1 (honest disposition)
- PARTIAL: QIP-INT-06 is a passing conformance test for the planner branch
  of R3.1 only. It is NOT a trace for QIP-R3.1 as written.
- EXPLICITLY UNTESTABLE in this suite (recorded, not rounded up): R3.1 also
  covers "status, and other non-intervention traffic". (a) Status saturation:
  status has no bounded pool to saturate; the shared Store.lock/threadpool
  cannot be saturated deterministically through the neutral TestClient
  adapter, and holding Store.lock would block STOP by construction rather
  than measure independence. (b) Secure-core OTHER-bucket saturation: no
  production caller acquires OTHER, so no neutral adapter operation can
  saturate it. (c) Deadline/starvation/threaded-or-network load behaviour:
  no conformance mechanism exists; F3 loadtest evidence is separate, local,
  simulated, and carries no test ID. Any of these would need work outside
  this node's owned paths (app/main.py, integrations/secure_core.py, or a
  threaded harness design) and a profile-owner decision first.

EVIDENCE (command, toolchain, host, UTC, raw output path)
- Host: Darwin (macOS 15.3.1) arm64; Python 3.11 (.venv/bin/python --version
  via Makefile PYTHON=python3.11); cargo/rustc from /opt/homebrew/bin for the
  with-Rust run. Date (UTC): 2026-11-06T15:21:24Z.
- Raw output files (this machine, /tmp/qip-r3-evidence/): cargo-build.log,
  with-rust-conformance.log, with-rust-full.log, without-rust-conformance.log,
  without-rust-full.log, fail-direction.log, import-app-main.log.
  Verbatim tails are reproduced below because a summary line is not evidence.
- Commands run:
  cargo build --workspace                                   -> exit 0
  .venv/bin/python -m pytest conformance/ -q -rs            (with Rust)
  .venv/bin/python -m pytest -q                             (with Rust, full)
  PATH=$PWD/.venv/bin:/usr/bin:/bin .venv/bin/python -m pytest conformance/ -q -rs
  PATH=$PWD/.venv/bin:/usr/bin:/bin .venv/bin/python -m pytest -q
    (which cargo/rustc under that PATH: not found, exit 1; note the built
    target/debug binary still exists on disk, so this replicates the gate's
    PATH condition, it does not remove built artifacts)
  .venv/bin/python -m pytest conformance/ -q -rs -k "DEG or STATE_01"
  (cd empty dir; PYTHONPATH=<repo>) python -c "import app.main" + file count
  test_QIP_INT_06 alone, 5 consecutive runs

RAW OUTPUT (verbatim tails)
[cargo-build.log]
     Compiling quberon-secure-core v0.1.0 (/Users/quberon1/Library/Application Support/Quberon/worktrees/qip-qip-r3-1/crates/quberon-secure-core)
     Compiling quberon-secure-core-cli v0.1.0 (/Users/quberon1/Library/Application Support/Quberon/worktrees/qip-qip-r3-1/apps/quberon-secure-core-cli)
      Finished `dev` profile [unoptimized + debuginfo] target(s) in 4.13s
  CARGO_EXIT:0 (target/debug/quberon-secure-core-cli present)

[with-rust-conformance.log]
  29 passed, 1 warning in 4.54s
  CONFORMANCE_WITH_RUST_EXIT:0

[with-rust-full.log]
  212 passed, 2 warnings in 39.51s
  FULL_WITH_RUST_EXIT:0

[without-rust-conformance.log]
  29 passed, 1 warning in 4.31s
  CONF_NO_RUST_EXIT:0

[without-rust-full.log]
  212 passed, 2 warnings in 38.81s
  FULL_NO_RUST_EXIT:0

[fail-direction.log]  (-k "DEG or STATE_01": DEG-01, DEG-02, DEG-03, STATE-01)
  4 passed, 25 deselected, 1 warning in 0.79s
  FAILDIR_EXIT:0

[import-app-main.log]
  import ok
  IMPORT_EXIT:0
  (directory listing empty; find . -type f | wc -l -> 0)

[INT-06 x5]
  1 passed, 1 warning in 0.18s
  1 passed, 1 warning in 0.17s
  1 passed, 1 warning in 0.17s
  1 passed, 1 warning in 0.17s
  1 passed, 1 warning in 0.17s

[baseline before changes, no Rust binary built yet]
  27 passed, 1 skipped (QIP-LATCH-03 NOT TESTED: secure-core binary
  unavailable) -- conformance/test_conformance.py, pytest -q -rs

TESTS (both modes)
- Exit gate: python -m pytest conformance/ -q -> 29 passed with Rust built
  (0 skipped; QIP-LATCH-03 and QIP-INT-06 both exercised), 29 passed with
  Rust removed from PATH.
- Full suite: 212 passed with Rust; 212 passed with Rust removed from PATH.
- Both fail-direction tests included in the 4-test DEG/STATE-01 selection
  above (all passed; DEG-03 was not skipped for this adapter because both
  injection capabilities are True).
- import app.main in an empty directory created zero files.

STILL NOT TRUE (mandatory, non-empty)
- QIP-R3.1 is still UNIMPLEMENTED in QIP-v0.1.md Section 11. QIP-INT-06
  covers only deterministic planner-semaphore saturation in process; it
  does not trace R3.1, R3.2, or R3.3, and no QIP class is claimed.
- Status/other-traffic saturation, secure-core OTHER-bucket isolation
  through the adapter, deadline/starvation bounds, threaded/network load,
  restart/reconnect, and network partition remain untested in conformance.
- No real-time, latency, deadline, physical stop-time, certification,
  physical-safety, or regulatory-compliance claim is supported by anything
  in this node or this repository. All behaviour observed is the in-repo
  simulator over FastAPI TestClient.
- The without-Rust runs above still had the previously built
  target/debug binary on disk; they test PATH absence, not a clean
  no-binary tree. The pre-change baseline (27 passed, 1 skipped) is the
  observed no-binary conformance result.

NEEDS A HUMAN DECISION
- Profile owner: whether QIP-INT-06 (planner branch) plus the separate F3
  loadtest evidence ever justify amending QIP-R3.1 traceability under
  QIP-v0.1.md Section 11, or whether R3.1 stays UNIMPLEMENTED until status/
  other-traffic saturation is testable. This node recommends keeping it
  UNIMPLEMENTED on INT-06 alone.
- Profile owner / system owner: whether to commission out-of-node work
  (app or secure-core call sites, e.g. a production OTHER-bucket acquirer,
  or a threaded conformance harness) to make the remainder testable. No
  such change was made here; none is in this node's owned paths.
