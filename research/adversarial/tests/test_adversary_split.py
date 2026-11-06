"""Fail-direction tests for the ind-1 adversary/defender split.

The adversary (adversary.py) must not be the lineage that wrote the code
under test: it consumes only public_interface.json + QIP, stamps every
artefact with generator.model and generator.sees_implementation=false,
and the checkers here must be able to FAIL on a bad stamp / bad input.
Prior corpora keep their existing honest generator.model labels and are
classified legacy -- never relabelled independent.
"""
import ast
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ADV_DIR = HERE.parent
sys.path.insert(0, str(ADV_DIR))

import adversary  # noqa: E402

REPO = ADV_DIR.parents[1]
CORPUS = ADV_DIR / "corpus"


def _rows(name):
    return [json.loads(l) for l in (CORPUS / name).read_text().splitlines() if l.strip()]


def test_adversary_imports_no_defender_code():
    tree = ast.parse((ADV_DIR / "adversary.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"integrations", "app", "adapters", "run", "invariants",
                 "generate", "mutate", "conformance", "fastapi"}
    assert not (imported & forbidden), imported
    src = (ADV_DIR / "adversary.py").read_text()
    for token in ("from integrations", "import app", "from invariants", "from run import"):
        assert token not in src


def test_public_context_rejects_implementation_inputs(tmp_path):
    iface, _ = adversary.load_public_context()
    assert iface["allowed_actions"]
    # Implementation source offered as the interface must be refused.
    with pytest.raises(adversary.AdversaryInputError):
        adversary.load_public_context(REPO / "integrations" / "meta.py")
    # A random non-allowlisted file must be refused.
    other = tmp_path / "notes.md"
    other.write_text("anything")
    with pytest.raises(adversary.AdversaryInputError):
        adversary.load_public_context(other)
    # An allowlist-named file that is not the real QIP must be refused.
    fake_qip = tmp_path / "QIP-v0.1.md"
    fake_qip.write_text("unrelated text")
    with pytest.raises(adversary.AdversaryInputError):
        adversary.load_public_context(qip_path=fake_qip)


def test_public_context_records_hashes_of_actual_inputs():
    _, inputs = adversary.load_public_context()
    by_role = {i["role"]: i for i in inputs}
    iface_bytes = (ADV_DIR / "public_interface.json").read_bytes()
    qip_bytes = (REPO / "docs/specs/intervention-profile/QIP-v0.1.md").read_bytes()
    assert by_role["public-interface"]["sha256"] == hashlib.sha256(iface_bytes).hexdigest()
    assert by_role["qip"]["sha256"] == hashlib.sha256(qip_bytes).hexdigest()
    # The public interface must not point the adversary at implementation.
    blob = (ADV_DIR / "public_interface.json").read_text()
    for token in ("integrations/", "app/main", "validate_plan"):
        assert token not in blob


def test_every_independent_artefact_carries_split_stamp():
    rows = _rows("independent.jsonl")
    assert rows, "independent corpus is empty"
    _, inputs = adversary.load_public_context()
    expected_hashes = {i["name"]: i["sha256"] for i in inputs}
    for r in rows:
        assert adversary.validate_artefact(r) == [], r["id"]
        gen = r["generator"]
        assert gen["model"] == "none-programmatic-templates"
        assert gen["sees_implementation"] is False
        for item in gen["inputs"]:
            assert expected_hashes[item["name"]] == item["sha256"]
    assert len({r["payload"] for r in rows}) == len(rows)  # deduplicated
    assert {r["class"] for r in rows}  # classes present
    benign = [r for r in rows if r["class"] == "benign-control"]
    assert benign and all(r["expectation"] == "accept" for r in benign)


def test_artefact_stamp_checker_can_fail():
    good = _rows("independent.jsonl")[0]
    bad_sees = json.loads(json.dumps(good))
    bad_sees["generator"]["sees_implementation"] = True
    assert adversary.validate_artefact(bad_sees)
    assert adversary.classify_artefact(bad_sees) != "independent"
    bad_model = json.loads(json.dumps(good))
    del bad_model["generator"]["model"]
    assert adversary.validate_artefact(bad_model)
    bad_input = json.loads(json.dumps(good))
    bad_input["generator"]["inputs"] = [{"role": "x", "name": "meta.py", "sha256": "0" * 64}]
    assert adversary.validate_artefact(bad_input)
    assert adversary.classify_artefact(good) == "independent"


def test_generated_cases_are_deterministic():
    iface, inputs = adversary.load_public_context()
    a = adversary.generate_cases(iface, inputs, per_class=2)
    b = adversary.generate_cases(iface, inputs, per_class=2)
    assert a == b
    for r in a:
        assert adversary.validate_artefact(r) == []


def test_prior_corpora_keep_honest_legacy_labels():
    prov = json.loads((ADV_DIR / "provenance.json").read_text())
    assert prov["independent_generator"]["generator"]["model"] == "none-programmatic-templates"
    assert prov["independent_generator"]["generator"]["sees_implementation"] is False
    legacy = {e["file"]: e for e in prov["legacy_prior_corpora"]}
    prior_files = sorted(p.name for p in CORPUS.glob("*.jsonl") if p.name != "independent.jsonl")
    assert sorted(k.split("/")[-1] for k in legacy) == prior_files
    for name in prior_files:
        rows = _rows(name)
        entry = legacy[f"corpus/{name}"]
        assert entry["classification"] == "legacy-prior-corpus"
        assert entry["cases"] == len(rows)
        # Existing honest model label(s) in the file are preserved verbatim.
        observed = {str((r.get("generator") or {}).get("model")) for r in rows}
        assert observed == set(entry["generator_models_observed"])
        assert all((r.get("generator") or {}).get("model") for r in rows)
        # Prior artefacts are NOT classified independent.
        assert adversary.classify_artefact(rows[0]) == "legacy"


def test_new_generator_stamps_in_legacy_code_paths():
    import generate
    import mutate
    assert generate.GEN["model"] == "none-programmatic-templates"
    assert generate.GEN["sees_implementation"] is False
    base = {"summary": "inspect", "robot_id": "quberon-demo-001",
            "requested_action": "SIMULATE_INSPECTION",
            "required_capabilities": ["inspect"], "human_confirmation_required": True}
    out = mutate.generate_mutations([{"payload": json.dumps(base)}], target=3)
    assert out and all(
        m["generator"]["model"] == "none-programmatic-templates"
        and m["generator"]["sees_implementation"] is False for m in out)
