NODE: qip-qip-r3-2
TIER: 1
BRANCH: node/qip-qip-r3-2
COMMITS: single node commit on this branch; hash recorded in the final message / git log (not self-referenced here)
STATUS: partial

TASK AS READ
QIP-R3.2 (INTERVENE) in docs/specs/intervention-profile/QIP-v0.1.md Section 6:
"When non-intervention capacity is saturated, the response to that traffic
MUST be a bounded refusal (for example "busy"); it MUST NOT silently delay
a STOP request behind it." Section 11 traces QIP-R3.2 as UNIMPLEMENTED with
no reason recorded. Instruction: trace it to a passing conformance test or
record it as explicitly untestable; partial coverage stays UNIMPLEMENTED;
never round a gap up to a trace. Section 11 amendment belongs to the
profile owner; this node does not amend QIP-v0.1.md or TRACEABILITY.md.

WHAT WAS OBSERVED BEFORE CHANGING ANYTHING
- app/main.py:270: planner capacity is a dedicated
  threading.BoundedSemaphore(2) (app.state.plan_semaphore).
  app/main.py:592-593: a saturated planner returns non-blocking
  {"provider_status": "busy", "error": "planner concurrency limit",
  "stop_unaffected": True} (HTTP 200, refusal in body vocabulary).
  execute_stop (app/main.py:402) never touches that semaphore.
- Status (GET /api/robots/{id}/status) has no bounded capacity pool.
  The capacity status/task/STOP do share is Store.lock and the ASGI
  threadpool (progress/F3-stop-load.md finding 2 observed status+task
  load inflating STOP median in that local harness).
- Baseline on this branch before changes: pytest conformance/ -q =
  27 passed, 1 skipped.
- loadtest/ (Wave 5 F3) is separate local simulated evidence with no
  conformance test ID; it does not close R3.2 (its own report says so).

CHANGED (owned paths only: conformance/**, progress/qip-qip-r3-2.md)
- conformance/adapter_interface.py: appended neutral saturation point
  AdapterUnderTest.saturate_non_intervention_traffic() (raises
  NotImplementedError by default; scope explicitly planner/proposal
  capacity only) and capability
  "non_intervention_saturation_injectable": False in the default
  capabilities(). No existing method or ID changed or renumbered.
- conformance/quberon_adapter.py: capability True for this adapter;
  saturate_non_intervention_traffic() holds every slot of the app's
  existing plan_semaphore for the adapter's life. Conformance-side
  only; no app/control-path code changed.
- conformance/conftest.py: appended fixture adapter_planner_saturated
  (fresh adapter + saturation, following the DEG-03 injection fixtures).
- conformance/test_conformance.py: taxonomy line QIP-INT-01..05 -> ..06
  (append only); appended
  test_QIP_INT_06_saturated_planner_busy_refusal_and_stop_not_delayed
  with skip-guard _needs_saturation (capability False => NOT TESTED
  skip, never a pass). The test asserts, deterministically and with no
  timing value: saturated planner -> submit_proposal is 200 with
  provider_status "busy" and stop_unaffected True (bounded refusal);
  STOP while saturation is still held -> 200 / ACKNOWLEDGED /
  stop_latched True; a further proposal after STOP is still "busy"
  (STOP neither consumed nor released planner capacity); status still
  reports latched.
- conformance/README.md: new "QIP-INT-06 planner saturation" section
  and an expanded NOT TESTED entry recording the explicitly untestable
  remainder (below). This file also states QIP-R3.2 stays UNIMPLEMENTED.

RESULT FOR QIP-R3.2 (honest disposition)
- PARTIAL: QIP-INT-06 is a passing conformance test for the planner
  branch of R3.2 only. It is NOT a trace for QIP-R3.2 as written.
- EXPLICITLY UNTESTABLE in this suite (recorded in conformance/README.md
  NOT TESTED, not rounded up): R3.2 also covers "status, and other
  non-intervention traffic". (a) Status saturation: status has no
  bounded pool to saturate through the neutral adapter; the shared
  Store.lock/threadpool cannot be saturated deterministically through
  the synchronous TestClient adapter, and holding Store.lock would
  block STOP by construction rather than measure independence.
  (b) Any delay bound / "silently delay" as a timed property: no
  conformance mechanism exists and no timing is asserted; the test
  only proves STOP returns while planner capacity is held indefinitely.
  (c) Real concurrent planner load: injection holds the semaphore
  directly; it is not load. Any of these would need work outside this
  node's owned paths (app/main.py or a threaded harness design) and a
  profile-owner decision first.

EVIDENCE (command, toolchain, host, UTC, raw output path)
- Host: Darwin Quberon1.local 24.3.0 arm64 (macOS 15.3.1);
  Python 3.11.15 (.venv/bin/python); cargo 1.99.1 / rustc 1.99.1
  (/opt/homebrew/bin) for the with-Rust run. UTC: 2026-11-06T15:40:14Z.
- Raw output files (this machine, /tmp/qip-r3-2-evidence/):
  cargo-build.log, int06.log, with-rust-conformance.log,
  with-rust-full.log, without-rust-conformance.log,
  without-rust-full.log, fail-direction.log, import-app-main.log.
  Verbatim tails are reproduced below because a summary line where raw
  output was requested is not evidence.
- Commands run:
  cargo build --workspace                                    -> exit 0
  .venv/bin/python -m pytest conformance/ -q -rs             (with Rust)
  .venv/bin/python -m pytest -q                              (with Rust, full)
  PATH=$PWD/.venv/bin:/usr/bin:/bin .venv/bin/python -m pytest conformance/ -q -rs
  PATH=$PWD/.venv/bin:/usr/bin:/bin .venv/bin/python -m pytest -q
    (which cargo/rustc under that PATH: not found, exit 1; note the built
    target/debug binary still exists on disk, so this replicates the
    gate's PATH condition, it does not remove built artifacts)
  .venv/bin/python -m pytest conformance/ -q -rs -k "DEG or STATE_01"
  (cd empty dir; PYTHONPATH=<repo>) .venv/bin/python -c "import app.main"
    + file count in that dir afterwards
  test_QIP_INT_06 alone, plus 5 consecutive -k INT_06 runs

RAW OUTPUT (verbatim tails)
[cargo-build.log]
     Compiling quberon-secure-core v0.1.0 (/Users/quberon1/Library/Application Support/Quberon/worktrees/qip-qip-r3-2/crates/quberon-secure-core)
     Compiling quberon-secure-core-cli v0.1.0 (/Users/quberon1/Library/Application Support/Quberon/worktrees/qip-qip-r3-2/apps/quberon-secure-core-cli)
      Finished `dev` profile [unoptimized + debuginfo] target(s) in 3.81s
  CARGO_EXIT:0

[int06.log] (single test, -q -rs)
  1 passed, 1 warning in 0.15s
  EXIT:0
  plus 5 consecutive -k INT_06 runs, each:
  1 passed, 28 deselected, 1 warning in 0.14s

[with-rust-conformance.log]
  29 passed, 1 warning in 4.48s
  CONF_WITH_RUST_EXIT:0

[with-rust-full.log]
  212 passed, 2 warnings in 39.65s
  FULL_WITH_RUST_EXIT:0

[without-rust-conformance.log]
  29 passed, 1 warning in 4.36s
  CONF_NO_RUST_EXIT:0

[without-rust-full.log]
  212 passed, 2 warnings in 38.60s
  FULL_NO_RUST_EXIT:0

[fail-direction.log]  (-k "DEG or STATE_01": DEG-01, DEG-02, DEG-03, STATE-01)
  4 passed, 25 deselected, 1 warning in 0.76s
  FAILDIR_EXIT:0

[import-app-main.log]  (import run in an empty temp dir)
  import-ok
  IMPORT_EXIT:0
  files-after-import-count: 0

TESTS (both modes)
- With Rust (cargo built, cargo on PATH): conformance 29 passed;
  full suite 212 passed. Exit 0 both.
- Without Rust on PATH (PATH=.venv/bin:/usr/bin:/bin; built binary
  still on disk): conformance 29 passed; full suite 212 passed.
  Exit 0 both.
- Exit gate command exactly: python -m pytest conformance/ -q exits 0
  in both modes above (run as .venv/bin/python, Python 3.11.15).
- Fail-direction subset (DEG-01..03, STATE-01): 4 passed.
- import app.main in an empty dir: import-ok, exit 0, 0 files created.

STILL NOT TRUE
- QIP-R3.2 is NOT traced and remains UNIMPLEMENTED in QIP-v0.1.md
  Section 11. QIP-INT-06 covers only the planner/proposal branch, via
  conformance-side semaphore injection, in simulation. No traceability
  amendment was made by this node.
- No claim is made about: saturation of status/task/other traffic,
  any delay or deadline bound, starvation, network partition, threaded
  or network load, the Rust secure-core under load, Pi or hardware
  behaviour, or physical stop time (QIP-R3.3). No latency claim is
  made; no timing value is asserted anywhere in the new test.
- The "busy" refusal is HTTP 200 with provider_status "busy" in the
  app's existing vocabulary; no HTTP-level refusal code was added and
  no app/control-path code was changed.
- No QIP class is claimed. Nothing here is certification, physical-
  safety, latency, or regulatory-compliance evidence.

NEEDS A HUMAN DECISION
- Profile owner: whether QIP-INT-06's planner-branch evidence, together
  with the explicitly untestable remainder recorded in
  conformance/README.md, warrants any Section 11 amendment for
  QIP-R3.2, or whether R3.2 stays UNIMPLEMENTED until status/other-
  traffic saturation and a delay bound are testable. That amendment
  procedure (fetch, rebase, grep merged tree, raw output, CI) belongs
  to the profile owner, not this work node.
- If R3.2 is ever to be fully testable, a human must first decide the
  design question outside this node's paths: what bounded capacity, if
  any, status/task traffic should have, and what (if any) delay bound
  is assertable without becoming a real-time claim.
