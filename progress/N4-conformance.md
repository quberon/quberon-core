# N4-conformance — progress (Wave 4, Tier 1)

Node: Wave4 N4 | Owns: conformance/** and progress/N4-conformance.md only
(append to progress/n7-requests.md only if needed — not needed, no request)
Base: origin/main baa18a1522aeb9dc5865afbbfffe89fc94de2ece (= HEAD at start)
Gate sources: docs/specs/intervention-profile/OUTLINE.md (R1-R11),
TRACEABILITY.md (gate-zero gaps), graph.md (R-IMM-1..5), current tests/.
Attempts: 1 of 3 used (attempt 1 passed locally and clean-clone-style; no
gate was weakened).

## Deliverable

conformance/adapter_interface.py — implementation-neutral surface
(AdapterUnderTest + NeutralResult, neutral roles/vocabulary; no vendor
field names). conformance/quberon_adapter.py — reference mapping for ONE
implementation (quberon-core simulator via app.main HTTP). Swapping the
adapter module runs the identical suite against another system.
conformance/test_conformance.py — 28 tests with stable IDs for N5:
QIP-ID-01..04, QIP-AUTH-01..04, QIP-INT-01..05, QIP-LATCH-01..03,
QIP-STATE-01..03, QIP-AUDIT-01..03, QIP-PROP-01..03, QIP-DEG-01..03.
Do not renumber; append only.

## Exact results (this branch, with Rust core built)

Command: .venv/bin/python -m pytest conformance/ -q -rs
Raw: 27 passed, 1 skipped, 1 warning in 4.35s
SKIPPED QIP-DEG-03: "NOT TESTED: no implementation-neutral way to inject
persistence failure or secure-core reachable-refusal through
AdapterUnderTest yet; gap, not a pass"
Without Rust binary (same command, before cargo build): 26 passed,
2 skipped (QIP-LATCH-03 also NOT TESTED in that run).
Full-repo gate and clean-clone-style run: see "Verification" after push.

## Cumulative class verdicts (explicit met / shortfall)

| Class | IDs | Passed/Tested | Cumulative verdict |
|---|---|---|---|
| ID | QIP-ID-01..04 | 4/4 | MET for quberon-core simulator scope (R1 partial: no vendor-neutral envelope schema, no manufacturer target mapping — gap remains) |
| AUTH | QIP-AUTH-01..04 | 4/4 | MET for app auth scope (R2 partial: not a safety-rated authorization architecture) |
| INT | QIP-INT-01..05 | 5/5 | MET for endpoint/idempotency/stale & audit-only-kind scope (R3/R4/R9 partial: no load/deadline/starvation, no recognizer qualification) |
| LATCH | QIP-LATCH-01..03 | 3/3 with core; 2/3 + 1 NOT TESTED without | MET conditionally on secure-core availability; shortfall in no-Rust runs is reported as skip, never pass (R5; no physical reset evidence) |
| STATE | QIP-STATE-01..03 | 3/3 | MET for simulated adapter vocabulary SIMULATED_STOPPED/UNKNOWN (R6 partial: no independent physical-state sensing or latency bound) |
| AUDIT | QIP-AUDIT-01..03 | 3/3 | MET for in-app event record existence/dedup/auth (R8 partial: no retention, clock trust, export, tamper-evidence/custody) |
| PROPOSAL | QIP-PROP-01..03 | 3/3 | MET for advisory/latch-boundary scope (mock provider only; live provider NOT TESTED here) |
| DEGRADED | QIP-DEG-01..03 | 2/3, QIP-DEG-03 NOT TESTED | SHORTFALL: unsigned-STOP/blocked-reset (R-IMM-1) and failing-adapter UNKNOWN pass; persistence-failure and reachable-refusal (R-IMM-2) not neutrally injectable yet — gap remains a gap |

Cumulative: 27 passed, 1 skipped (NOT TESTED), 0 failed of 28.
This is NOT 28/28 and NOT standards conformance (R11 caveat).

## NOT TESTED (mandatory; gaps remain gaps)

- QIP-DEG-03 (skipped test in-suite): persistence failure, reachable
  secure-core refusal vs unavailability distinction beyond DEG-01.
- R10 entirely: any real manufacturer interface/mapping, capability
  negotiation (registry api-surfaces.jsonl empty at gate zero).
- Physical stopping/response time, load/starvation/network partition,
  real-controller restart/reconnect, physical reset function.
- Independent physical-state sensing; signed-attestation verification with
  a present core beyond indirect coverage; audit retention/export/custody;
  clock trust; recognizer/sensor qualification; live planner provider.
- Standards, PL/SIL, hazard analysis, legal conformity (R11).

## Verification (filled with raw output before merge)

- Local: pytest conformance/ -q -> 27 passed, 1 skipped (with core);
  26 passed, 2 skipped (without core). See above.
- Clean-clone-style and make test / CI: recorded in PR; report updated in a
  follow-up commit on this branch if numbers differ. No claim ahead of that
  evidence (R-IMM-4).
