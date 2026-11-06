"""QIP-R11.2 (OBSERVE) -- explicitly untestable in this suite.

QIP-R11.2 (docs/specs/intervention-profile/QIP-v0.1.md Section R11):
"Passing project or profile tests MUST NOT be represented as standards
conformance, certification, or physical safety validation."

This file records why no conformance test can trace that requirement.
It is deliberately SKIPPED, never passing: a skipped test is NOT
TESTED, not a pass, and this file is not a trace. QIP-R11.2 therefore
stays UNIMPLEMENTED in Section 11 until the profile owner (not a work
node) amends traceability by the Section 11 procedure.

Why untestable here, rather than partially testable:

1. No observable surface. The obligation governs how any actor
   *represents* test results -- in documents, PRs, issues, external
   statements, and future claims that do not exist yet. The neutral
   surface under test (adapter_interface.py: AdapterUnderTest /
   NeutralResult) has no operation that makes, returns, or enumerates
   representations or claims, so no adapter call can observe a
   violation or its absence.
2. Unbounded universe. The set of representations to check is not
   enumerable by this suite: any wording, in any artefact, on any
   medium, at any future time. Compliance is a property of human
   editorial/governance conduct, not of system behaviour.
3. Any automated substitute would be partial. Grepping enumerated
   repo files for forbidden phrases would cover only those files and
   phrasings at one instant, could not reliably distinguish a claim
   from its negation (e.g. "NOT standards conformance" is compliant),
   and would miss paraphrases and all out-of-repo representations.
   Per the node's rule, partial coverage stays UNIMPLEMENTED and
   must never be rounded up to a trace -- so no such grep test is
   added as evidence.

What would be needed instead: human review of each concrete claim
artefact at the time it is made (cf. QIP-R11.1: a claim must name its
class, profile version, exact test IDs, and raw output), followed by
a profile-owner amendment under QIP-v0.1.md Section 11 if the owner
decides a status change is warranted. This node makes no such change.
"""
import pytest


@pytest.mark.skip(
    reason=(
        "QIP-R11.2 EXPLICITLY UNTESTABLE in conformance: it prohibits "
        "representing passing tests as standards conformance, "
        "certification, or physical-safety validation -- a property of "
        "unbounded human representations, not of any "
        "AdapterUnderTest-observable behaviour. No trace claimed; "
        "requirement remains UNIMPLEMENTED (see this file's docstring "
        "and README.md NOT TESTED)."
    )
)
def test_QIP_R11_2_representation_prohibition_is_not_adapter_testable():
    # Never executed. Reaching here would turn an untestable
    # representation rule into a passing test -- exactly the rounding
    # QIP-R11.2 and the node's partial-coverage rule forbid.
    raise AssertionError("unreachable: QIP-R11.2 must stay skipped, not passed")
