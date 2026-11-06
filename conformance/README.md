# QIP conformance suite (Wave 4 N4)

Implementation-neutral, runnable adapter-interface suite for the Quberon
Intervention Profile outline (docs/specs/intervention-profile/OUTLINE.md
R1-R11, TRACEABILITY.md). Passing this suite is NOT standards conformance,
NOT certification, and NOT evidence about any physical robot (R11 caveat).

## Layout

- adapter_interface.py — the neutral surface (AdapterUnderTest, NeutralResult,
  neutral roles anonymous/viewer/operator/admin, neutral result vocabulary).
  No vendor field names are required by this file.
- quberon_adapter.py — reference mapping for ONE implementation: quberon-core
  (app.main simulator over HTTP/TestClient). Another system writes its own
  module like this and runs test_conformance.py unchanged.
- conftest.py — fixtures binding the suite to quberon-core, plus
  no-core (DEGRADED), failing-adapter (STATE/DEGRADED), persistence-
  degraded and refusing-core (QIP-DEG-03) variants.

## QIP-DEG-03 injection (Wave 5 F1)

AdapterUnderTest now declares two implementation-neutral injection
points, inject_persistence_failure() and inject_secure_core_refusal(),
plus matching capabilities (False by default: an adapter that cannot
inject reports the state NOT TESTED, never a pass). The interface names
states, not mechanisms. quberon_adapter implements them conformance-side
only: persistence injection sets the same persistence_ok=False degraded
flag the app's SQLite-error/init-failure paths set, and refusal
injection installs a reachable stub authority raising the app's existing
SecureCoreRejected (decision code REFUSED_CONFORMANCE_INJECTION). No
app/control-path code was changed. QIP-DEG-03 then observes, neutrally:
persistence-degraded -> status reports persistence_ok False, latch
retained, observed UNKNOWN, stop/task/reset all 503; reachable refusal
-> stop 503, secure_core_status "rejected" (distinct from DEG-01
"unavailable"), command/observed UNKNOWN, latch retained, audit
auth_result "secure_core_rejected".
- test_conformance.py — the suite. Stable test IDs QIP-<CLASS>-<nn> are in
  every test function name; N5 and later nodes reference them verbatim.
  Do not renumber; append new IDs only.

## QIP-INT-06 planner saturation (qip-qip-r3-1, QIP-R3.1 partial)

AdapterUnderTest now declares one implementation-neutral saturation
point, saturate_non_intervention_traffic(), plus the matching capability
(non_intervention_saturation_injectable, False by default: an adapter
that cannot saturate reports NOT TESTED, never a pass). The interface
names the planner/proposal capacity only. quberon_adapter implements it
conformance-side only: it holds every slot of the app's existing planner
BoundedSemaphore(2) for the adapter's life, so the next proposal takes
the app's existing non-blocking bounded refusal (provider_status
"busy", stop_unaffected True). No app/control-path code was changed and
no timing is asserted (QIP-R3.3). QIP-INT-06 then observes, neutrally:
planner-saturated -> proposal bounded-refused; STOP still 200 /
ACKNOWLEDGED / latched; status still 200 / latched; planner still
bounded-refused after STOP (STOP neither consumed nor released planner
capacity).

This is partial coverage of QIP-R3.1, not a trace for it. QIP-R3.1 as
written also covers status and other non-intervention traffic, and that
remainder is explicitly NOT TESTED / untestable in this suite (below).
QIP-R3.1 therefore stays UNIMPLEMENTED in QIP-v0.1.md Section 11 until
the profile owner amends traceability under that section's procedure;
this node does not amend it.

## Classes and outline mapping

ID (R1) · AUTH (R2) · INT intervention/idempotency/inputs (R3/R4/R9 partial)
· LATCH (R5) · STATE (R6) · AUDIT (R8 partial) · PROPOSAL planner boundary
(frontier rule: model proposes, deterministic law disposes) ·
DEGRADED fail-direction (R7, graph.md R-IMM-1/R-IMM-2).

## Run

    python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
    cargo build --workspace            # optional; enables QIP-LATCH-03
    .venv/bin/python -m pytest conformance/ -q

Without the Rust secure-core binary, motion-permitting reset cannot be
exercised: QIP-LATCH-03 skips, and the no-core DEGRADED tests still run.
Skips are NOT TESTED, never passes (see progress/N4-conformance.md).

## NOT TESTED (explicit gaps — remain gaps)

- QIP-DEG-03 injection limits: a REAL disk/SQLite persistence failure
  (injection flips the app's degraded flag, it does not corrupt storage),
  and a REAL Rust secure-core rejection of a signed envelope (injection
  uses a stub authority; no signing/verification is exercised). Restart
  recovery from either degraded state. Adapter non-invocation is observed
  via UNKNOWN/latch/audit outcomes, not via an invocation counter.
- Any real manufacturer interface, vendor stop/status/reset mapping,
  capability negotiation (R10: registry api-surfaces.jsonl was empty at
  gate zero) — no adapter for any real robot exists here.
- Physical stopping time, response-time/deadline/load/starvation, network
  partition, restart/reconnect against a real controller (R3/R4 limits).
  QIP-INT-06 covers only deterministic planner-semaphore saturation in
  process (above). Explicitly untestable in this TestClient suite, and
  therefore still a gap for QIP-R3.1 as written: (a) status/other-traffic
  saturation -- status has no bounded capacity pool to saturate, and the
  capacity status/task/STOP do share (Store.lock, the ASGI threadpool)
  cannot be saturated through the neutral adapter deterministically;
  holding Store.lock would block STOP by construction, not measure
  independence; (b) secure-core rate-limiter bucket isolation -- no
  production caller acquires the OTHER bucket (integrations/secure_core.py
  acquires only "STOP"), so there is no neutral operation that can
  saturate OTHER through the adapter; the unit test in
  tests/test_secure_core.py is not a conformance test; (c) any deadline,
  starvation bound, or concurrency behaviour under real threaded/network
  load (the F3 loadtest harness in loadtest/ is separate local simulated
  evidence, not a conformance test ID). No latency claim is made.
- Independent physical-state sensing, observation latency (R6 limits).
- Audit retention, clock trust, external export, tamper-evidence recovery,
  custody chain (R8 limits); signed-attestation verification when a core
  IS present is only indirectly covered (QIP-DEG-01 covers its absence).
- Recognizer qualification (voice/gesture sensors, ESPE, human factors):
  QIP-INT-04/05 test endpoint policy only, not recognition (R9 limits).
- Standards/PL/SIL/hazard/legal conformity of any kind (R11).
