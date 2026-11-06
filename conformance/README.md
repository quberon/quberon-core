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

- QIP-R2.3 (AUTHORIZE) — EXPLICITLY UNTESTABLE by this suite
  (QIP-AUTH-05, always skipped = NOT TESTED, never a trace, never a
  pass). R2.3 forbids *representing* application-level authorisation as
  a safety-rated authorisation architecture or as evidence of physical
  safety. That predicates over all human-facing representations (docs,
  UI, exports, logs, marketing, future surfaces), while the neutral
  adapter can only sample status/stop/task/proposal/intervene/events
  results, and the profile defines no neutral claim vocabulary whose
  absence would decide the question. Asserting the quberon binding's
  sampled payloads contain no forbidden phrase, or carry its
  implementation-specific disclaimers (`adapter_mode="SIMULATION"`,
  `safety_notice`, secure-core scope
  `SIMULATION_ONLY_STOP_AUTHORIZATION`), would be partial coverage and
  would pass even if an unsampled representation violated R2.3.
  QIP-AUTH-01 (R2.1) and QIP-AUTH-02/QIP-AUTH-04 (R2.2) do not cover
  R2.3. It stays UNIMPLEMENTED in QIP-v0.1 Section 11 until the profile
  owner defines a human claim-audit procedure outside this runtime
  suite or amends the requirement. This does not assert that quberon
  makes no such representation anywhere; no such audit was performed
  here.
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
