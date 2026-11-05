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
  no-core (DEGRADED) and failing-adapter (STATE/DEGRADED) variants.
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

- QIP-DEG-03: persistence failure and secure-core reachable-refusal via a
  neutral injection point (test exists, deliberately skipped).
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
