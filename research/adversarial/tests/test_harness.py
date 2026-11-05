import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from generate import payload_for  # noqa: E402
from mutate import generate_mutations, mutate_payload  # noqa: E402

BASE = {"summary": "inspect", "robot_id": "quberon-demo-001",
        "requested_action": "SIMULATE_INSPECTION",
        "required_capabilities": ["inspect"], "human_confirmation_required": True}


def test_mutate_deterministic():
    assert mutate_payload(BASE, 7) == mutate_payload(BASE, 7)


def test_generate_mutations_unique_and_count():
    cases = [{"payload": json.dumps({**BASE, "summary": f"inspect {i}"})} for i in range(20)]
    out = generate_mutations(cases, target=50)
    assert len(out) == 50
    assert len({c["payload"] for c in out}) == 50


def test_generator_covers_subclasses_and_benign_accepts():
    raw, exp, _ = payload_for("13", "benign-control", "inspection", 0)
    assert exp == "accept" and json.loads(raw)["requested_action"] == "SIMULATE_INSPECTION"
