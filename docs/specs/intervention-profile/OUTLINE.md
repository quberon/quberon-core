# Intervention profile outline (gate zero)

Status: research outline only; **not normative text**. The words below describe candidate evidence topics, not requirements, certification criteria, or deployment authorization.

## Scope boundary

This outline records the questions a future intervention profile may need to answer for a robot adapter and intervention path. It does not define a physical emergency-stop device, replace a machinery risk assessment, allocate PL/SIL, or establish conformity with any standard or law.

The N4 manufacturer-interface matrix is a declared dependency. At this base, `research/humanoids/registry/api-surfaces.jsonl` is empty. Accordingly, all R1-R11 items below are stated design-decision topics or test-derived observations only; none is represented as an observed manufacturer-interface requirement.

## Candidate outline

| ID | Candidate topic | Current provenance class | Gate-zero note |
|---|---|---|---|
| R1 | Intervention request identity and target scope | stated design decision | Represent robot/system target, intervention kind, event/command identity, and source identity without assuming vendor field names. |
| R2 | Authentication and authorization boundary | stated design decision | Record who or what submitted the intervention and which policy admitted it. Do not infer physical safety from application authorization. |
| R3 | Stop priority and independence from non-critical traffic | stated design decision; existing tests | Study bounded, independently serviced STOP capacity so unrelated planner/status traffic cannot consume the whole intervention path. |
| R4 | Idempotency, duplicate detection, and conflict handling | stated design decision; existing tests | Preserve stable identities; distinguish exact duplicates from conflicting reuse and from stale historical events. |
| R5 | Latching and restart/reset separation | stated design decision; existing tests | Model stop-latched state separately from observed robot state. Reset is a distinct permission-gated action and must not itself imply task start. |
| R6 | Command result versus observed physical state | stated design decision; existing tests | Report requested/accepted/acknowledged/unknown and observed state separately. Never turn an adapter error or missing observation into a stopped claim. |
| R7 | Unavailability versus reachable refusal | stated design decision; existing tests | Preserve the project rule that unavailable authority differs from a reachable authority that refuses. Intervention availability and permission gating may have different failure direction. |
| R8 | Evidence, timestamps, replay bounds, and custody | stated design decision; existing tests | Retain timestamps, scope, sequence/idempotency data, decision/result, and signed/unsigned provenance. Blockchain remains outside the control path. |
| R9 | Human and machine intervention inputs | stated design decision; existing tests | Treat voice, gesture, UI, protective sensing, and other recognizers as explicitly scoped inputs with conservative matching and freshness/quality evidence. Do not label an unqualified recognizer as a safety-rated device. |
| R10 | Adapter capability and manufacturer-interface mapping | N4-dependent gap | Future work must map manufacturer-documented stop/status/reset surfaces, semantics, preconditions, transport, timing, and failure indications. No mapping exists at gate zero. |
| R11 | Verification, lifecycle, and conformance evidence | stated design decision; existing tests plus gaps | Require named tests and raw evidence for supported claims, with version/change control and deployment-specific validation. Passing project tests is not standards conformance. |

## Deferred decisions

- Which robot classes and deployments are in scope.
- Whether a manufacturer surface is a normal stop, protective stop, emergency-stop interface, safety-rated monitored stop, or only an application command.
- Required response-time budgets, diagnostic coverage, PL/SIL targets, sensing types, separation distances, force/pressure limits, or validation protocols.
- Required field names, transports, schemas, and capability negotiation.
- Legal classification and conformity-assessment route for any product or integration.

Those decisions require N4 evidence, deployment hazard analysis, licensed standards review, and qualified engineering/legal assessment. They are intentionally not fabricated here.
