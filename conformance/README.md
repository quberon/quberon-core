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

- QIP-R3.3 (INTERVENE) — EXPLICITLY UNTESTABLE via this suite, recorded
  by the unconditional skip
  `test_QIP_R3_3_priority_must_not_be_represented_as_guarantee` in
  test_conformance.py: the requirement constrains how priority handling
  is *represented* (it MUST NOT be represented as a real-time or
  physical stop-time guarantee), not any adapter behaviour. No
  AdapterUnderTest operation returns a claim/representation about
  timing guarantees, and the profile allocates no response-time budget
  or stop-time threshold that a measurement could pass/fail against.
  Absence of a guarantee field in a NeutralResult, disclaimers in
  in-repo prose, and latency runs (e.g. progress/F3-stop-load.md,
  scoped by its own text to R3.1/R3.2) are at most partial coverage
  and are NOT rounded up to a trace. QIP-R3.3 stays UNIMPLEMENTED in
  QIP-v0.1 Section 11; amending that table is the profile owner's
  procedure (Section 11), not this suite's. Assessment, if any, is
  human/governance review of claims against raw output.
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
- Independent physical-state sensing, observation latency (R6 limits).
- Audit retention, clock trust, external export, tamper-evidence recovery,
  custody chain (R8 limits); signed-attestation verification when a core
  IS present is only indirectly covered (QIP-DEG-01 covers its absence).
- Recognizer qualification (voice/gesture sensors, ESPE, human factors):
  QIP-INT-04/05 test endpoint policy only, not recognition (R9 limits).
- Standards/PL/SIL/hazard/legal conformity of any kind (R11).
