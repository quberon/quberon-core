# The fail-direction asymmetry — a standalone argument

Status: argued normative artefact for the Quberon Intervention Profile
(QIP). This document states and defends one rule, traces it to the two
project tests that currently carry it, and records what it does not
establish. It is not a safety standard, confers no certification, and
must not be represented as certification, approval, physical-safety
validation, or conformity with any machinery, robotics, or
functional-safety standard or law. It specifies semantics for a
simulation-scoped intervention interface only (QIP v0.1 page-one notice
applies in full). No performance level, safety integrity level,
response-time budget, or device requirement is allocated here.

Naming, to prevent a known collision: the node brief that commissioned
this artefact calls the fail-direction asymmetry "R4". That label is
not reused normatively here, because in this repository R4 already
means two other things — QIP-R4 is idempotency/duplicates/staleness
(QIP-v0.1.md Section 7) and GRAPH-HARNESS R4 is parallelism. The
normative home of the rule argued below is QIP-R7.1–R7.4
(QIP-v0.1.md Section 9) together with graph.md rules R-IMM-1 and
R-IMM-2. Nothing is renumbered by this document.

## 1. Thesis

Failure direction is not a property of a system. It is a property of
an (action, authority-state) pair.

An intervention interface must therefore decide, separately:

  1. which way the requested action moves the system — toward
     inhibiting motion (STOP) or toward permitting motion (latch
     reset, task start); and
  2. what the authorising authority actually did — returned a positive
     decision (accepted), returned a negative decision (rejected), or
     returned no decision at all (unavailable).

The asymmetry follows from keeping those two axes distinct:

  - No decision is not a negative decision. Absence of an attestation
    must not be allowed to veto an authenticated request to inhibit
    motion, or the attestation service becomes a single point of
    failure for stopping. So, when the authority is unavailable, STOP
    executes — but only unsigned, visibly labelled unsigned, with the
    latch retained.
  - A negative decision is not an absence. A reachable authority that
    rejects has produced evidence about this request (replay, expiry,
    scope mismatch, malformed output). Collapsing "rejected" into
    "unavailable" would make rejection meaningless and would erase
    exactly the signal that distinguishes a confused or hostile
    request from an outage. So, when the authority rejects, STOP is
    blocked: the adapter is not invoked, the latch is retained, and
    the observed state is reported as UNKNOWN.
  - Permission is the opposite direction. Reset and task move toward
    motion, so for them the absence of a decision can never be
    enough. Reset and task always fail closed: no unsigned reset, no
    unsigned task.

In one line: attestation unavailability may waive the signature on a
stop; it may never waive the decision required to permit motion; and
an explicit refusal waives nothing at all.

## 2. Definitions (as implemented, not as wished)

Authority: the Rust secure-core client boundary in
integrations/secure_core.py, consulted by the single STOP convergence
path `execute_stop` in app/main.py. All STOP modalities (button,
voice, gesture, intervention endpoint) converge on that one path.

Accepted: the core returned outcome ACCEPTED with code
ACCEPTED_SIMULATION_STOP_AUTHORIZATION and matching robot/simulation
scope (integrations/secure_core.py, `authorize_stop`).

Unavailable: no decision was obtained. In the code this is: no core
client provisioned (`core_client is None`), or SecureCoreUnavailable
raised — binary not found, or the subprocess could not run, including
spawn failure and timeout in `_run_cli`. Client code:
integrations/secure_core.py:50-55, 193-204.

Rejected: a decision or a boundary verdict against this request was
obtained. In the code this is SecureCoreRejected — non-ACCEPTED
decision, signing failure, malformed / oversized / non-object core
output, or decision scope mismatch (integrations/secure_core.py:
58-66, 205-260) — and, at the app boundary, any non-Unavailable
exception from the authorisation call, which execute_stop records as
a rejection (app/main.py:437-446).

Adapter: SimulatedRobotAdapter, the component whose `stop()`,
`reset_simulation()` and `simulated_task()` invocations are counted
by the tests. Invocation is the observable that separates "the stop
was requested" from "the stop surface was actuated".

Latch: retained stop-latched state (store.stop_latched). It is set by
STOP, retained through both degraded branches below, and cleared only
by the distinct, separately authorised reset action (QIP-R5.1/R5.2).

UNKNOWN: the explicit non-claim for command/observed state used when
no observation supports a stronger value (QIP-R6.2). UNKNOWN is a
report, not a synonym for stopped and not a synonym for moving.

Scope condition: the asymmetry below is stated for the state in which
the application persistence layer is healthy (`persistence_ok`). The
persistence-degraded state is a separate, stricter branch and is
treated in Section 5.

## 3. The normative rule

FDA-1 (STOP, authority unavailable). An authenticated, CSRF-checked
STOP request MUST still invoke the adapter exactly once when the
authority is unavailable. The result MUST be labelled unsigned in
both the response (`secure_core.status = "unavailable"`, with
decision, sequence and audit_record null) and the audit record
(auth_result `UNSIGNED/core_unavailable`). The latch MUST be
retained. What is waived is the signed attestation only — never
authentication, authorisation of the principal, CSRF, idempotency,
or the latch. (QIP-R7.2; graph.md R-IMM-1.)

FDA-2 (STOP, authority rejects). When a reachable authority rejects,
the adapter MUST NOT be invoked. The response MUST be a failure
(HTTP 503 in the reference implementation), the latch MUST be
retained, command and observed state MUST be reported as UNKNOWN,
and the outcome MUST be recorded distinctly from unavailability
(`secure_core.status = "rejected"`, audit auth_result
`secure_core_rejected`). A rejection MUST NOT be re-labelled
unsigned, and an unsigned record MUST NOT be counted as signed.
(QIP-R7.4, QIP-R8.2; graph.md R-IMM-2.)

FDA-3 (reset and task always fail closed). Latch reset and any
task/motion-permitting action MUST NOT proceed when the authority is
unavailable: no adapter invocation for reset or task, HTTP 503 in
the reference implementation, latch retained, and reset MUST NOT
itself start a task. There is no unsigned reset and no unsigned
motion. (QIP-R7.3, QIP-R5.2/R5.3; graph.md R-IMM-1.)

FDA-4 (unavailable and rejected are distinct, forever). Unavailable
and rejected MUST be recorded and returned as distinct outcomes with
distinct operator-facing meaning at every layer — client exception,
HTTP response, status reporting, and audit record. Any code path
that merges them (one exception type, one status string, one audit
label) breaks this profile even if the adapter behaviour happens to
match. (QIP-R7.1, QIP-R6.1; graph.md R-IMM-2.)

FDA-5 (no state inference across the boundary). Neither branch may
upgrade a report: an unsigned STOP is not a signed authorisation, an
adapter acknowledgement is not an observed stop, and a blocked STOP
is not an observed "still moving". Observed state comes only from
the observation source; where there is none, the report is UNKNOWN.
(QIP-R6.1–R6.3, QIP-R8.2.)

FDA-6 (accepted is the only signed path). Only a positive authority
decision yields a signed STOP (`secure_core.status = "accepted"`
with the decision code, sequence and audit record carried through).
Accepted, unavailable-unsigned and rejected are the complete set of
STOP/authority outcomes; a fourth, unlabelled outcome is a defect.

### Decision table (reference implementation behaviour)

| Action | Authority | Adapter invoked | HTTP | Latch | Reported state | Attestation label |
|---|---|---|---|---|---|---|
| STOP | accepted | yes, once | 200 | retained/set | adapter result, observed separately | accepted (signed) |
| STOP | unavailable | yes, once | 200 | retained/set | adapter result, observed separately | `unavailable`; audit `UNSIGNED/core_unavailable` |
| STOP | rejected | no | 503 | retained | command UNKNOWN, observed UNKNOWN | `rejected`; audit `secure_core_rejected` |
| reset | unavailable | no | 503 | retained | unchanged, not re-claimed | none issued |
| reset | client present | yes (reset surface only) | 200 | cleared only on acknowledged reset | adapter result | no core motion decision exists (see §7) |
| task | unavailable | no | 503 (409 if latch check fires first) | retained | unchanged | none issued |
| task | client present, latched | no | 409 | retained | unchanged | none issued |

Two readings of this table matter. First, the only cell in which an
action proceeds without a positive decision is STOP/unavailable, and
it is also the only cell whose evidence record is required to carry a
visible defect label (UNSIGNED). Second, reset/task do not consult
the authority for a motion decision at all: the Rust core's closed
action enum can represent STOP only, so for motion-permitting
actions the gate is authority *availability* plus the latch, not a
signed permission (app/main.py:288-303). FDA-3 is therefore a
fail-closed availability gate, not a claim that the core authorised
the motion.

## 4. Argument

1. Direction of travel determines what an outage may cost. For a
   motion-permitting action, proceeding on no decision risks the
   outcome the latch exists to prevent — motion nobody authorised.
   For a motion-inhibiting action, *blocking* on no decision risks
   the symmetric harm: a stop nobody could execute. A single global
   failure policy (always closed, or always open) can only minimise
   one of these. Splitting the policy by direction of travel is the
   minimum structure that addresses both.

2. Epistemic state determines what the authority's silence means.
   Unavailability is the absence of evidence about the request: the
   request was never judged. Rejection is evidence about the request:
   it was judged and found wanting (replay, expiry, scope mismatch),
   or the channel that judged it produced output that cannot be
   trusted (malformed, oversized, scope-confused). Treating silence
   as refusal lets an outage veto stops (argument 1). Treating
   refusal as silence lets a request that has already failed scrutiny
   execute anyway, which deletes the distinction the audit record
   exists to preserve, and makes replay/scope defences advisory.

3. What is waived in the unavailable branch is narrow and named. The
   unsigned STOP still requires an authenticated, role-authorised,
   CSRF-checked principal on the single convergence path; it still
   passes idempotency/conflict handling; it still sets and retains
   the latch; and it is permanently labelled UNSIGNED in the audit
   record. The design therefore does not "fail open" in the access-
   control sense: no protected object becomes accessible. It fails
   toward inhibition while degrading the *evidence quality* of the
   act, and it says so in the record. The residual attack is real and
   is stated, not hidden: an attacker who can disable the core can
   force stops to be unsigned. But that attacker gains only the
   ability to inhibit (a denial-of-service against the simulator),
   never to permit: the same outage that strips the signature also
   blocks reset and task (FDA-3). The asymmetry is what confines the
   blast radius of an attestation outage to inhibition.

4. Rejection blocking STOP is the deliberately hard edge, and its
   justification is integrity, not comfort. If a reachable authority
   has rejected this request — for example because its sequence was
   already used, or its scope does not match — executing the stop
   anyway would teach every downstream consumer that rejection is a
   comment, not a decision. It would also make the two failure
   branches indistinguishable in outcome, so an operator (or an
   auditor, or a court) could no longer tell from behaviour whether
   the authority was absent or opposed. The cost is acknowledged in
   Section 6: in this branch a stop the operator wanted does not
   execute through this interface. That cost is accepted here only
   because this profile governs a software intervention interface in
   simulation, and expressly does not replace, gate, or sit in series
   with any physical emergency-stop function (see Section 6.3).

5. The latch is the memory that makes the asymmetry safe to use.
   Both degraded branches retain the latch, and reset is a separate,
   separately authorised, fail-closed action that never starts a
   task. So neither degraded branch can be the first half of a
   two-step escape (force outage → unsigned stop → unsigned reset →
   motion): the second step does not exist. Without latch retention
   plus FDA-3, FDA-1 would be an escape hatch; with them, the
   degraded mode is a cul-de-sac that ends in inhibition.

## 5. The persistence exception (a stricter branch, not a contradiction)

When application persistence is degraded (`persistence_ok` false),
STOP, task and reset all return 503, the latch is retained, observed
state is UNKNOWN, and durability is explicitly not claimed
(app/main.py:407-410, 540-541, 567-568; conformance QIP-DEG-03).
This does not contradict FDA-1. FDA-1 waives a missing *attestation*
when the act can still be recorded and latched durably. Where the
system cannot even guarantee that the latch and the audit event will
survive, an executed-but-unrecorded stop would manufacture confidence
the system cannot back. The rule is therefore ordered: durability of
the latch/record is a precondition; attestation is the degradable
layer; permission is never degradable.

## 6. Counterarguments, taken seriously

### 6.1 "Fail-safe defaults say fail closed everywhere."

Saltzer and Schroeder's fail-safe defaults (1975) base access
decisions on permission rather than exclusion: the default is lack
of access, and a mistake in an explicit-permission mechanism tends
to fail by refusing. That principle governs FDA-3 in full — reset
and task are permissions to move toward motion, and they default to
denial. The tension is only apparent for STOP: a STOP is not an
access grant to a protected object, it is an inhibition request, and
the "object" protected by refusing it would be continued motion.
Applying a permission-default to inhibition reflexively, without
asking which outcome the default protects, is exactly the move this
artefact argues against. Where the classic principle and this rule
genuinely collide, this rule says so (FDA-2: a refused authorisation
is not executed) rather than pretending no collision exists.

### 6.2 "This is just OCSP soft-fail, which is a known failure."

The closest prior art is certificate revocation checking. RFC 6960
defines the OCSP status values good / revoked / unknown, and notes
that "revoked" means the certificate should be rejected while
"unknown" means the status could not be determined by this responder,
leaving the client to decide. Browser practice then split into
soft-fail (proceed when revocation information cannot be fetched)
and hard-fail (block). Soft-fail is widely criticised — in Adam
Langley's phrase quoted by Cloudflare, soft-fail revocation checks
are "like a seat-belt that snaps when you crash", because an attacker
who controls the network can manufacture the unavailability that
triggers the soft fail.

This rule borrows the tri-state (accepted / rejected / unavailable
are good / revoked / unknown, kept forever distinct) and rejects the
part of soft-fail that earned the criticism, in three ways. First,
what soft-fails here is not a check on the party requesting access;
the requester is still authenticated and authorised, and what is
waived is the countersignature, not the scrutiny. Second, the
attacker who manufactures unavailability gains strictly less than
in the OCSP case: a revoked-certificate attacker gains *admission*
(the protected outcome); an attacker here gains only *inhibition*,
and simultaneously loses reset/task, which fail closed on the same
outage. Third, the degraded act is loudly and permanently labelled
UNSIGNED in the audit record, where browser soft-fail is silent.
The analogy is therefore instructive in both directions: it supplies
the vocabulary and the warning, and the differences are the design.

### 6.3 "Blocking a STOP on rejection is itself dangerous."

Correct — for a physical emergency-stop function, it would be
unacceptable for a software authorisation verdict to stand between
an operator and a stop. That is why this profile's scope boundary is
load-bearing, not decorative: QIP specifies the semantics of a
software intervention interface in simulation; it does not define,
replace, or sit in series with a machinery emergency-stop function,
and it allocates no safety function at all (QIP v0.1 page-one
notice). Within that scope, the rejected branch's cost is loss of
one software stop request and an UNKNOWN report that invites human
escalation through other means, while its benefit is that replay,
scope-confusion and channel-corruption signals are never silently
executed. Any future deployment that connects an interface governed
by this profile to a real robot must re-decide FDA-2 with a
deployment-specific risk assessment and qualified assessors; this
artefact must not be cited as having decided it for them.

### 6.4 "Fail open for STOP even on rejection; a stop can only help."

This collapses FDA-4 and makes the authority decorative: if every
authority outcome — accepted, unavailable, rejected — ends with the
adapter invoked, the authority's only remaining product is a label
nobody is obliged to read. It also destroys the evidentiary value of
the audit trail, because behaviour no longer correlates with the
authority's judgement. The asymmetry's whole claim is that the label
and the behaviour must move together, or neither means anything.

### 6.5 "Two branches are complexity; complexity is the enemy."

True, and priced in. The implementation cost is visible in
execute_stop: one try, one Unavailable branch, one rejection branch,
one shared adapter invocation. The profile's defence is Saltzer and
Schroeder's own economy-of-mechanism test in reverse: the simpler
one-branch policies were considered above (6.1, 6.4) and each was
shown to sacrifice a property — stop availability, refusal meaning,
or permission closure — that the system elsewhere claims. Complexity
that is load-bearing is documented; complexity that is not, is not
added: there is no fourth authority state, no retry-forever, no
cached-decision reuse in this rule.

## 7. Prior art and review depth

Review-depth markers follow PRIOR-ART.md and are preserved verbatim:
`scope and abstract reviewed; full text not reviewed`;
`official full public text reviewed`; `official overview reviewed`;
`official repository/source text reviewed`. No requirement in this
artefact is derived from a work carrying the first marker.

| Work | Source | Review depth | What it contributes / does not contribute |
|---|---|---|---|
| Saltzer & Schroeder, *The Protection of Information in Computer Systems* (1975) | https://web.mit.edu/Saltzer/www/publications/protection/Basic.html | official repository/source text reviewed | Fail-safe defaults, complete mediation, economy of mechanism. Supports FDA-3 directly; for FDA-1/FDA-2 it supplies the principle this rule qualifies (§6.1). It does not state the asymmetry. |
| RFC 6960, OCSP (2013) | https://www.rfc-editor.org/rfc/rfc6960.txt | official full public text reviewed | The good/revoked/unknown tri-state and the note that revoked ⇒ reject while unknown leaves the decision to the client. Vocabulary and precedent for FDA-4; no intervention semantics. |
| Cloudflare, *High-reliability OCSP stapling and why it matters* | https://blog.cloudflare.com/high-reliability-ocsp-stapling | official overview reviewed | Soft-fail vs hard-fail practice and the Langley "seat-belt" criticism used in §6.2. Vendor engineering writing; cited for the counterargument, not for authority. |
| EN ISO 13850 / ISO 13850:2015, emergency stop function | https://www.iso.org/standard/59970.html | scope and abstract reviewed; full text not reviewed | Frames the machinery emergency-stop function this profile does not specify (§6.3). No clause, device, or timing claim is imported. |
| ISO 13849-1:2023; IEC 61508 series | https://www.iso.org/standard/69883.html ; https://webstore.iec.ch/en/publication/5515 | scope and abstract reviewed; full text not reviewed | Safety-related control / functional-safety lifecycle context only. No PL, SIL, architecture, or lifecycle claim is made or imported. |
| Regulation (EU) 2023/1230 (Machinery) | https://eur-lex.europa.eu/eli/reg/2023/1230/oj | official full public text reviewed | Legal context for the scope boundary (via QIP v0.1 page-one notice). Not a conformity assessment for anything in this repo. |
| NIST SP 800-207, Zero Trust Architecture | https://csrc.nist.gov/pubs/sp/800/207/final | official full public text reviewed (via docs/SECURE-CORE.md reference list) | Per-request, scope-bound authorisation rather than network trust; motivates why the authority's per-request verdict is worth distinguishing at all. |

Originality claim, stated at the strength the evidence supports:
within the works reviewed for PRIOR-ART.md and this artefact, none
states the combination — (a) authority-unavailable STOP proceeds
unsigned and labelled, (b) authority-rejected STOP does not invoke
the adapter and reports UNKNOWN, (c) permission-to-move actions fail
closed on the same unavailability — as a single normative rule for an
intervention interface. That is a claim about this review, not a
proof of worldwide novelty; a wider literature and patent search has
not been performed (see "Still not true" in the node report).

## 8. Traceability: the two tests that carry the rule

At the base of this node the asymmetry existed as graph.md rules
R-IMM-1/R-IMM-2, prose in docs/SECURE-CORE.md ("Which direction does
this fail?"), QIP-R7.1–R7.4, and two test functions. The two load-
bearing tests are, verbatim:

1. `tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not`
   With `secure_core=None` and adapter invocations counted by
   monkeypatching SimulatedRobotAdapter: STOP returns HTTP 200,
   command_state ACKNOWLEDGED, stop_latched true, and exactly one
   adapter stop invocation; secure_core is exactly
   {status: "unavailable", decision: null, sequence: null,
   audit_record: null, scope: SIMULATION_ONLY_STOP_AUTHORIZATION};
   the persisted audit event's auth_result is
   `UNSIGNED/core_unavailable`. Admin reset then returns HTTP 503
   with zero reset-adapter invocations and the latch still true, and
   a simulated task returns 409 or 503 with the latch still true.
   This test carries FDA-1, FDA-3, FDA-4 and FDA-6's unavailable row.

2. `tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter`
   With a stub reachable core raising SecureCoreRejected with
   decision {code: REPLAY_REJECTED, sequence: 7,
   audit_record: "deadbeef"}: STOP returns HTTP 503, adapter stop
   invocation count is exactly zero, secure_core.status is
   "rejected" with the decision code, sequence and audit_record
   carried through, and the status endpoint then reports
   stop_latched true and observed_state UNKNOWN. This test carries
   FDA-2, FDA-4, FDA-5 and FDA-6's rejected row.

Corroborating, not substituting: conformance/test_conformance.py
QIP-DEG-01 (no-core unsigned STOP, reset 503, latch retained),
QIP-DEG-02 (failing adapter latches, UNKNOWN), and QIP-DEG-03
(persistence-degraded all-503 branch of Section 5, plus reachable-
refusal 503 / "rejected" / UNKNOWN / audit `secure_core_rejected`
through the neutral adapter interface). Note the known staleness this
creates: QIP-v0.1.md Section 11 still marks QIP-R7.1 and QIP-R7.4
UNIMPLEMENTED because its trace table predates the Wave 5 F1
DEG-03 injection work. Updating that table is outside this node's
owned paths for the profile text as a whole and is handed off in the
node report rather than silently edited here.

What the two tests do not cover, and this artefact does not claim:
a real (non-stub) Rust core rejection reaching execute_stop end to
end in these two functions (test 2's RejectingCore is a stub; real-
core decision paths are exercised elsewhere in
tests/test_secure_core.py), timeout-classified-as-unavailable
behaviour at the app boundary, restart persistence of the latch
across the degraded branches, and any timing, load, or network-
partition behaviour.

### Falsifiability

This rule is false, and should be amended, if any of the following
is observed on the reference implementation: an unavailable-core
STOP that is recorded as signed or that fails to invoke the adapter;
a rejected STOP that invokes the adapter or reports an observed
state other than UNKNOWN; an unavailable-core reset or task that
invokes its adapter or clears the latch; or a status/audit surface
on which "unavailable" and "rejected" cannot be told apart. Each is
expressible as a mutation of the two named tests (swap the
Unavailable/Rejected branches; delete the audit label; drop the
invocation counter) and each mutation must make the suite fail —
that, and not this prose, is the gate.

## 9. Limits

This artefact argues semantics for a simulation-scoped software
interface. It establishes nothing about any physical robot, any real
manufacturer stop/reset surface (QIP R10 remains an evidence gap),
response time under load, behaviour on real failing storage, or
conformity with any standard or law. The unsigned STOP is a
deliberate simulation availability choice with a named residual
risk (§4.3), not a physical-safety claim, and FDA-2 in particular
must be re-decided by qualified assessors before any non-simulation
use (§6.3).
