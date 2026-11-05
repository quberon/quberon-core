# Quberon Intervention Profile (QIP) v0.1

Status: normative profile text, version 0.1 (draft for Wave 4 review)
Base: origin/main baa18a1522aeb9dc5865afbbfffe89fc94de2ece
Owners: Wave 4 N5 (this document only; no implementation is claimed here)

----------------------------------------------------------------------
PAGE-ONE NOTICE — READ FIRST

This document is NOT a safety standard.
It confers NO certification, and conformance with it MUST NOT be
represented as certification, approval, or conformity with any
machinery, robotics, or functional-safety standard or law.
This profile COMPLEMENTS rather than replaces machinery and
functional-safety duties. It does not discharge, reduce, or substitute
for:

  - a deployment-specific machinery risk assessment;
  - duties under applicable machinery law (for example, in the EU,
    Regulation (EU) 2023/1230, whose official full public text was
    reviewed for legal context only);
  - functional-safety design, validation, or assessment duties for
    safety-related parts of control systems, whatever standards a
    qualified assessor selects for the deployment;
  - the duties of manufacturers, integrators, and operators of any
    real robot, cell, or application this profile is used alongside.

QIP v0.1 specifies only the semantics of an intervention interface —
identity, authorisation, result/observation separation, and evidence —
for a simulation-scoped system. It allocates no performance level
(PL), no safety integrity level (SIL), no response-time budget, no
force, pressure, speed, or separation limit, and no device requirement.
Those allocations are deployment decisions that require licensed
standards review and qualified engineering and legal assessment.
----------------------------------------------------------------------

## 1. Conformance language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD,
SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL in this document are to be
interpreted as described in RFC 2119 as clarified by RFC 8174, and
apply only when they appear in all capitals as shown here.

A requirement is identified as QIP-R<n>.<m>, where <n> is the outline
topic R1–R11 inherited unchanged from OUTLINE.md (gate zero). Each
requirement names:

  - its lowest conformance class (Section 2); a claim to a higher
    class includes every requirement of every lower class; and
  - its traceability (Section 11): either a verified Wave 4 N4 test
    identifier, or the explicit marker UNIMPLEMENTED.

In v0.1 no QIP class is claimed (see Section 10/11): rows trace to the
actual Wave 4 N4 identifiers where N4 assertions cover the requirement,
and every other requirement is explicitly UNIMPLEMENTED. Existing
project tests informed the wording of several
requirements as stated design decisions (see TRACEABILITY.md), but no
existing test is, by itself, a QIP conformance test, and none is
cited below as verified QIP traceability. No requirement in this
document is derived from the scope or abstract of a paywalled
standard; Annex A preserves the review-depth record that enforces
that exclusion.

## 2. Conformance classes (cumulative)

Four classes are defined. They are cumulative: each class includes
all normative requirements of the classes before it.

  Class OBSERVE (O)
    Read-only exposure of intervention-relevant state. An OBSERVE
    implementation can report requested, accepted, acknowledged,
    refused, unavailable, and observed state without conflating them,
    and can declare what it cannot do (R6, R10, R11).

  Class INTERVENE (I) = OBSERVE + intervention submission
    Adds submission of a scoped STOP intervention, priority isolation
    from non-intervention traffic, idempotency and staleness handling,
    latching with separated reset, and scoped human/machine input
    handling (R1, R3, R4, R5, R9).

  Class AUTHORIZE (A) = INTERVENE + authorisation boundary
    Adds authenticated and authorised submission, scope-pinned
    authorisation decisions, and the distinct handling of an
    unavailable authorising authority versus a reachable authority
    that refuses (R2, R7).

  Class EVIDENCE (E) = AUTHORIZE + evidence production
    Adds complete, provenance-labelled audit evidence, replay bounds,
    and claim discipline sufficient for a third party to reproduce
    what was requested, decided, invoked, and observed (R8, R11).

An implementation MUST NOT claim a class unless it satisfies every
MUST and MUST NOT of that class and of every lower class. An
implementation MUST NOT claim a class on the basis of a partial,
planned, or UNIMPLEMENTED requirement.

## 3. Terminology

  Intervention request: a single, identified request to stop (STOP)
    directed at one identified target. v0.1 defines no other
    intervention kind.
  Target: the robot/system identity the request is scoped to.
  Principal: the authenticated human or service identity submitting
    a request, where the claimed class requires one.
  Authority: an authorising component that returns an accept or a
    refusal decision for a scoped request, or is unavailable.
  Adapter: the component that would invoke a target-side stop surface
    in response to an accepted intervention.
  Acknowledgement: a report that a request was accepted, received, or
    invoked. An acknowledgement is not an observation.
  Observed state: state reported by an observation source, recorded
    separately from any acknowledgement.
  Latch: retained stop-latched state that survives until a distinct,
    separately authorised reset action clears it.
  Unavailable: the authority could not be reached or could not
    produce a decision. Unavailable is not a refusal.
  Refusal: a reachable authority examined the request and returned a
    negative decision.

## 4. R1 — Intervention request identity and target scope (INTERVENE)

QIP-R1.1 (INTERVENE) An intervention request MUST carry an explicit
target identity, an explicit intervention kind, an event or command
identity, and a source identity, without assuming vendor field names.
QIP-R1.2 (INTERVENE) A receiver MUST reject a request whose target
identity does not match the receiver's own target, and MUST NOT act
on it for any other target.
QIP-R1.3 (INTERVENE) A receiver MUST reject a request whose
intervention kind is not a kind it has declared under QIP-R10.1.

## 5. R2 — Authentication and authorisation boundary (AUTHORIZE)

QIP-R2.1 (AUTHORIZE) An AUTHORIZE implementation MUST authenticate
the principal submitting an intervention before acting on it.
QIP-R2.2 (AUTHORIZE) It MUST authorise the principal for the
requested intervention kind and target scope before acting; an
authenticated but unauthorised principal MUST be refused.
QIP-R2.3 (AUTHORIZE) Application-level authorisation MUST NOT be
represented as a safety-rated authorisation architecture or as
evidence of physical safety.

## 6. R3 — Stop priority and independence (INTERVENE)

QIP-R3.1 (INTERVENE) STOP intervention capacity MUST be serviced
independently of planner, status, and other non-intervention traffic,
such that saturation of non-intervention traffic does not consume all
intervention capacity.
QIP-R3.2 (INTERVENE) When non-intervention capacity is saturated,
the response to that traffic MUST be a bounded refusal (for example
"busy"); it MUST NOT silently delay a STOP request behind it.
QIP-R3.3 (INTERVENE) Priority handling under this section is a
software scheduling property of this profile only; it MUST NOT be
represented as a real-time or physical stop-time guarantee.

## 7. R4 — Idempotency, duplicates, staleness (INTERVENE)

QIP-R4.1 (INTERVENE) An exact duplicate of an already-actioned
request — same identity, same content — MUST NOT re-invoke the
adapter and MUST return the original outcome.
QIP-R4.2 (INTERVENE) Reuse of a request identity with different
content MUST be rejected as a conflict and MUST NOT invoke the
adapter.
QIP-R4.3 (INTERVENE) A stale request — one superseded by a later
reset and subsequent activity, or outside its declared freshness
bound — MUST be rejected as stale and MUST NOT invoke the adapter.

## 8. R5 — Latching and restart/reset separation (INTERVENE)

QIP-R5.1 (INTERVENE) Once a STOP has been actioned, the latch MUST
be retained across process restart until cleared under QIP-R5.2.
QIP-R5.2 (INTERVENE) Clearing the latch (reset) MUST be a distinct
action from STOP, MUST require its own authorisation at AUTHORIZE
and above, and MUST NOT itself start a task or permit motion.
QIP-R5.3 (INTERVENE) While latched, task or motion-permitting
actions MUST be refused.

## 9. R6, R7 — Observation, and unavailable versus refused

### R6 — Command result versus observed state (OBSERVE)

QIP-R6.1 (OBSERVE) Requested, accepted, acknowledged, refused,
unavailable, and observed state MUST be reported as distinct values;
no one of them MUST be inferred from another.
QIP-R6.2 (OBSERVE) An adapter failure, missing observation, or
absent acknowledgement MUST be reported as UNKNOWN (or equivalent
explicit non-claim); it MUST NOT be reported as stopped.
QIP-R6.3 (OBSERVE) A stopped observation MUST originate from an
observation source; an adapter acknowledgement alone MUST NOT be
presented as an observed stop.

### R7 — Unavailability versus reachable refusal (AUTHORIZE)

QIP-R7.1 (AUTHORIZE) Authority unavailability and reachable refusal
MUST be recorded and returned as distinct outcomes, with distinct
operator-facing meaning.
QIP-R7.2 (AUTHORIZE) Where this profile's recorded project rule
applies — intervention does not fail closed on attestation
unavailability, while permission does — a STOP MAY proceed with its
attestation explicitly labelled unsigned when the authority is
unavailable; the unsigned status MUST be visible in the result and
in the evidence record.
QIP-R7.3 (AUTHORIZE) Permission-gated actions (task enablement,
latch reset) MUST fail closed when the authority is unavailable:
they MUST NOT proceed on an unsigned or absent decision.
QIP-R7.4 (AUTHORIZE) When a reachable authority refuses, the adapter
MUST NOT be invoked, the latch MUST be retained, and the observed
state MUST be reported as UNKNOWN unless independently observed.

## 10. R8, R9, R10, R11 — Evidence, inputs, capabilities, claims

### R8 — Evidence, timestamps, replay bounds, custody (EVIDENCE)

QIP-R8.1 (EVIDENCE) Every intervention decision MUST produce an
evidence record containing at least: request identity, target,
intervention kind, principal (where applicable), decision and its
basis, adapter invocation or non-invocation, observed state as
separately recorded, timestamp, and a monotonic sequence or epoch
value sufficient to detect rollback or reordering.
QIP-R8.2 (EVIDENCE) Signed and unsigned records MUST be labelled as
such; an unsigned record MUST NOT be presented, exported, or counted
as signed.
QIP-R8.3 (EVIDENCE) Replay of recorded intervention traffic MUST be
bounded so that replayed requests are subject to QIP-R4.3 staleness
rejection and cannot re-invoke an adapter as if new.
QIP-R8.4 (EVIDENCE) Nothing on the intervention control path MUST
depend on a blockchain; any settlement or anchoring, if present,
MUST be off the control path and downstream of the custody record.

### R9 — Human and machine intervention inputs (INTERVENE)

QIP-R9.1 (INTERVENE) Voice, gesture, UI, protective-sensing, and
other recogniser inputs MUST be accepted only within their declared
scope, confidence, finality, and freshness criteria; an input outside
those criteria MUST NOT invoke an intervention.
QIP-R9.2 (INTERVENE) A recogniser input of this section MAY request
STOP only; it MUST NOT clear a latch, grant a capability, or permit
motion.
QIP-R9.3 (INTERVENE) Synthetic, fixture, or replayed recogniser input
MUST be labelled as such in the evidence record and MUST NOT be
represented as live sensor qualification.

### R10 — Adapter capability and manufacturer-interface mapping (OBSERVE)

QIP-R10.1 (OBSERVE) An implementation MUST declare the intervention
kinds, target scope, status values, and reset semantics it supports,
and MUST declare unsupported kinds as unsupported rather than
approximating them.
QIP-R10.2 (OBSERVE) An implementation MUST NOT claim a mapping to a
manufacturer stop, status, or reset interface unless that interface
has been observed in manufacturer-provided material recorded with
its source. At v0.1 no such mapping is recorded (the N4
manufacturer-interface matrix remains an explicit gap), so every
such mapping is UNIMPLEMENTED and MUST NOT be claimed.

### R11 — Verification, lifecycle, and conformance evidence (OBSERVE / EVIDENCE)

QIP-R11.1 (OBSERVE) A class claim MUST name the class, this profile
version, and the exact test identifiers relied on, and MUST be
accompanied by the raw output of those tests; a summary without the
underlying output does not satisfy this requirement.
QIP-R11.2 (OBSERVE) Passing project or profile tests MUST NOT be
represented as standards conformance, certification, or physical
safety validation.
QIP-R11.3 (EVIDENCE) Changes to normative text, class assignment, or
traceability status MUST be versioned with the profile; an
implementation MUST state the profile version it claims against,
and a claim against a superseded version MUST be labelled as such.

## 11. Traceability to Wave 4 N4 (actual stable taxonomy, pre-merge)

N4 is concurrent with this node. Its shipped stable taxonomy (branch
wave4/n4, commit 310fc208555f59a2027f8e3496555e05244b229e, read
2026-11-05; "do not renumber; append new IDs only") is:

    QIP-ID-01..04 (R1)  QIP-AUTH-01..04 (R2)  QIP-INT-01..05 (R3/R4/R9 partial)
    QIP-LATCH-01..03 (R5)  QIP-STATE-01..03 (R6)  QIP-AUDIT-01..03 (R8 partial)
    QIP-PROP-01..03 (proposal boundary)  QIP-DEG-01..03 (R7; DEG-03 is a skipped gap)

Per the Wave 4 order, this profile MUST be re-verified against the
actual identifiers on merged origin/main (fetch, rebase, grep the
merged conformance/ tree and its raw output, amend this table) before
it is merged. Until that verification, a row below either names the
actual N4 test identifier whose assertions cover the requirement, or
carries the explicit marker UNIMPLEMENTED; naming an identifier here
is a trace, not a pass claim, and no QIP class is claimed in v0.1.
QIP-PROP-01..03 have no normative counterpart in R1-R11 beyond
QIP-R5.3/QIP-R9.2's no-reset rule and are not used as traces below.
Partial coverage is marked UNIMPLEMENTED, not rounded up to a trace.

| Requirement | Lowest class | W4-N4 test ID or UNIMPLEMENTED |
|---|---|---|
| QIP-R1.1 | INTERVENE | QIP-ID-01 |
| QIP-R1.2 | INTERVENE | QIP-ID-02, QIP-ID-03 |
| QIP-R1.3 | INTERVENE | UNIMPLEMENTED (QIP-INT-05 covers audit-only kinds only) |
| QIP-R2.1 | AUTHORIZE | QIP-AUTH-01 |
| QIP-R2.2 | AUTHORIZE | QIP-AUTH-02, QIP-AUTH-04 |
| QIP-R2.3 | AUTHORIZE | UNIMPLEMENTED |
| QIP-R3.1 | INTERVENE | UNIMPLEMENTED (no load/priority test in N4) |
| QIP-R3.2 | INTERVENE | UNIMPLEMENTED |
| QIP-R3.3 | INTERVENE | UNIMPLEMENTED |
| QIP-R4.1 | INTERVENE | QIP-INT-02 |
| QIP-R4.2 | INTERVENE | QIP-INT-03 |
| QIP-R4.3 | INTERVENE | QIP-INT-04 |
| QIP-R5.1 | INTERVENE | UNIMPLEMENTED (restart persistence not in N4) |
| QIP-R5.2 | INTERVENE | QIP-LATCH-02, QIP-LATCH-03 |
| QIP-R5.3 | INTERVENE | QIP-LATCH-01 |
| QIP-R6.1 | OBSERVE | QIP-STATE-02 |
| QIP-R6.2 | OBSERVE | QIP-STATE-01 |
| QIP-R6.3 | OBSERVE | QIP-STATE-03 |
| QIP-R7.1 | AUTHORIZE | UNIMPLEMENTED (QIP-DEG-03 skipped: NOT TESTED, gap not pass) |
| QIP-R7.2 | AUTHORIZE | QIP-DEG-01 |
| QIP-R7.3 | AUTHORIZE | QIP-DEG-01 |
| QIP-R7.4 | AUTHORIZE | UNIMPLEMENTED (QIP-DEG-03 skipped: NOT TESTED, gap not pass) |
| QIP-R8.1 | EVIDENCE | UNIMPLEMENTED (QIP-AUDIT-01 covers event existence/id/ts only) |
| QIP-R8.2 | EVIDENCE | QIP-DEG-01 |
| QIP-R8.3 | EVIDENCE | UNIMPLEMENTED |
| QIP-R8.4 | EVIDENCE | UNIMPLEMENTED |
| QIP-R9.1 | INTERVENE | UNIMPLEMENTED (QIP-INT-04 covers stale voice input only) |
| QIP-R9.2 | INTERVENE | QIP-INT-05 |
| QIP-R9.3 | INTERVENE | UNIMPLEMENTED |
| QIP-R10.1 | OBSERVE | UNIMPLEMENTED (R10: N4 records no manufacturer/capability mapping) |
| QIP-R10.2 | OBSERVE | UNIMPLEMENTED (R10 gap, explicit in N4 README) |
| QIP-R11.1 | OBSERVE | UNIMPLEMENTED |
| QIP-R11.2 | OBSERVE | UNIMPLEMENTED |
| QIP-R11.3 | EVIDENCE | UNIMPLEMENTED |

Amendment rule (pre-merge, mandatory): after N4 merges, fetch
origin/main, rebase this profile onto it, grep the merged tree and
N4's raw test output for each identifier above, keep a trace only
where the identifier and a passing (not skipped) raw result are both
present, downgrade any other row to UNIMPLEMENTED, and record the
commands and raw output in progress/N5-qip-v01.md. That verification,
plus CI, is the precondition for merging this profile.

## Annex A — Prior-art review depth (non-normative, preserved verbatim)

Review-depth markers from PRIOR-ART.md are preserved unchanged:

  - `scope and abstract reviewed; full text not reviewed` — public
    catalogue material for a paywalled standard only. No detailed
    requirement claim is made.
  - `official full public text reviewed` — public legislation or
    specification text was available and reviewed.
  - `official overview reviewed` — an official public project/product
    overview was reviewed; it is not treated as a standard.
  - `official repository/source text reviewed` — public source text
    in the named official repository was reviewed.

Works carrying the marker `scope and abstract reviewed; full text not
reviewed` at gate zero: EN ISO 13850 / ISO 13850:2015; ISO
10218-1:2025; ISO 10218-2:2025; ISO/TS 15066:2016; ISO 13849-1:2023;
the IEC 61508 series; the IEC 61496 series. No normative requirement
in this profile is derived from any of them: their public abstracts
were used only to keep evidence classes distinct (machinery risk
reduction, safety-related control integrity, protective sensing,
software/process quality, and orchestration are different claims).
Regulation (EU) 2023/1230 carries `official full public text
reviewed` and is cited only for legal context in the page-one
notice. Full provenance, source URLs, and limits for every work
remain in PRIOR-ART.md, which this annex does not supersede.

## Annex B — Relation to gate zero (non-normative)

OUTLINE.md and TRACEABILITY.md remain the gate-zero research record:
R1–R11 as stated design decisions or test-derived observations, with
R10 an explicit N4-dependent gap. This profile converts those topics
into normative interface-semantics requirements without widening
their evidence: it adds no manufacturer mapping (QIP-R10.2), no
threshold, and no conformance claim beyond the classes of Section 2,
each of which is UNIMPLEMENTED until Section 11 verification occurs.
