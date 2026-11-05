"""Unit tests for invariants.py, including deliberately failing fixtures.

Gate proof (M2 spec section 3): an invariant checker that cannot fail is
not a checker. Every invariant gets one passing and one failing fixture.
Raw output of this file's deliberately-failing demonstration is committed
at research/adversarial/evidence/invariant-failing-fixtures.txt (produced
by demonstrate_failures() run as a script, NOT by pytest assertions alone).
"""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from invariants import CHECKS, check_all  # noqa: E402

GOOD_PLAN = {"robot_id": "quberon-demo-001", "requested_action": "SIMULATE_INSPECTION",
             "required_capabilities": ["inspect"], "human_confirmation_required": True}
BASE = {
    "path": "direct", "expectation": "reject", "plan": GOOD_PLAN,
    "validation": {"allowed_as_proposal": False, "errors": ["x"], "latch_blocks_task": True},
    "response_text": '{"allowed_as_proposal": false}', "response_json": None,
    "http_status": 200, "exception": None, "latency_ms": 1, "response_bytes": 30,
    "latch_before": b"True", "latch_after": b"True",
    "adapter_calls_before": 0, "adapter_calls_after": 0,
    "new_audit_actions": [], "secure_core_calls_before": 0, "secure_core_calls_after": 0,
    "forbidden_strings": ["SENTINEL_SECRET_XYZ"],
}


def obs(**kw):
    o = copy.deepcopy(BASE)
    o.update(kw)
    return o


def test_all_pass_on_good_rejection():
    inv, viol = check_all(obs())
    assert all(v == "pass" for v in inv.values()), viol


# --- Deliberately failing fixtures: one per invariant ---
FAILING = {
    "I1": obs(exception="ValueError: boom"),
    "I2": obs(validation={"allowed_as_proposal": True, "errors": []},
              plan={**GOOD_PLAN, "requested_action": "MOVE_ARM"}),
    "I3": obs(validation={"allowed_as_proposal": True, "errors": []},
              plan={**GOOD_PLAN, "required_capabilities": ["inspect", "status"]}),
    "I4": obs(latch_after=b"False"),
    "I5": obs(adapter_calls_after=1),
    "I6": obs(new_audit_actions=["SIMULATE_INSPECTION"]),
    "I7": obs(secure_core_calls_after=1),
    "I8": obs(latency_ms=5000),
    "I9": obs(response_text="leaked SENTINEL_SECRET_XYZ here"),
    "I10": obs(expectation="accept"),  # benign but rejected in BASE validation
}


def test_each_invariant_can_fail():
    for iid, fixture in FAILING.items():
        status, detail = CHECKS[iid](fixture)
        assert status == "fail", f"{iid} did NOT fail on its failing fixture"
        assert detail


def test_each_failing_fixture_passes_its_other_invariants_where_isolated():
    # I2/I3/I10 fixtures interact by design (accepted-plan checks); assert the
    # targeted invariant is among violations rather than exclusivity.
    for iid, fixture in FAILING.items():
        _, viol = check_all(fixture)
        assert iid in [v["invariant"] for v in viol], (iid, viol)


def test_i1_http500_and_traceback_fail():
    assert CHECKS["I1"](obs(http_status=500))[0] == "fail"
    assert CHECKS["I1"](obs(response_text="Traceback (most recent call last)"))[0] == "fail"


def test_i8_response_size_fails():
    assert CHECKS["I8"](obs(response_bytes=70000))[0] == "fail"


def test_i9_object_repr_fails():
    assert CHECKS["I9"](obs(response_text="<Foo object at 0xdeadbeef>"))[0] == "fail"


def test_i10_passes_for_accepted_benign():
    o = obs(expectation="accept",
            validation={"allowed_as_proposal": True, "errors": []})
    assert CHECKS["I10"](o)[0] == "pass"


def test_severities_include_s0_for_i4_i5_i7():
    from invariants import SEVERITY
    assert SEVERITY["I4"] == SEVERITY["I5"] == SEVERITY["I7"] == "S0"


if __name__ == "__main__":
    for iid, fixture in FAILING.items():
        print(iid, CHECKS[iid](fixture))
    print("good:", check_all(obs()))
