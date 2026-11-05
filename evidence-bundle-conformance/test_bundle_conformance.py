"""Cross-implementation conformance vectors for quberon-evidence-bundle v1.
Consumes vectors.json + the committed N3 fixture; compares this checker
against the pre-existing Python verifier (tools/quberon-verify) on verdict.
SIMULATION ONLY; no physical/certification claim."""
import json, subprocess, sys
from pathlib import Path
import pytest
HERE = Path(__file__).parent; ROOT = HERE.parents[0]
sys.path.insert(0, str(HERE))
import bundle_check as bc
FIXTURE = ROOT/"tools/quberon-verify/tests/fixtures/simulated-stop.qeb"
TAMPERED = ROOT/"tools/quberon-verify/tests/fixtures/tampered-replay.qeb"
EXISTING = ROOT/"tools/quberon-verify/quberon-verify"
VECTORS = json.loads((HERE/"vectors.json").read_text())

def existing_verdict(path):
    r = subprocess.run([sys.executable, str(EXISTING), str(path)], capture_output=True, text=True)
    return json.loads(r.stdout)["verdict"], r.returncode

def test_vectors_file_wellformed():
    assert VECTORS["format"] == "quberon-evidence-bundle-conformance-vectors"
    assert VECTORS["claim_boundary"] == "SIMULATION_ONLY_NO_PHYSICAL_NO_CERTIFICATION"
    cats = {v["category"] for v in VECTORS["vectors"]}
    assert cats == {"canonical_bytes","hash_chain","signature","replay_binding","manifest_completeness","tamper_classes","rebuild_and_resign_limitation"}
    ids = [v["id"] for v in VECTORS["vectors"]]; assert len(ids) == len(set(ids)) == 17
    import hashlib; assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == VECTORS["fixture_sha256"]

def test_all_vectors_match_expected():
    out = bc.check_vectors(VECTORS, FIXTURE)
    assert out["base_verdict"] == "PASS_LIMITED_CLAIMS"
    assert out["all_ok"], out

def test_fixture_parity_with_existing_verifier():
    mine = bc.validate(FIXTURE); theirs, rc = existing_verdict(FIXTURE)
    assert mine["verdict"] == theirs == "PASS_LIMITED_CLAIMS" and rc == 0
    assert mine["checks"] == json.loads(subprocess.run([sys.executable,str(EXISTING),str(FIXTURE)],capture_output=True,text=True).stdout)["checks"]

def test_committed_tampered_fixture_parity():
    mine = bc.validate(TAMPERED); theirs, rc = existing_verdict(TAMPERED)
    assert mine["verdict"] == theirs == "REJECT" and rc == 1
    assert "REPLAY_TASK_OUTPUTS_MISMATCH" in mine["errors"]

@pytest.mark.parametrize("vector", [v for v in VECTORS["vectors"] if v["category"]=="tamper_classes"], ids=lambda v: v["tamper_id"])
def test_tamper_classes_reject_in_both_implementations(vector, tmp_path):
    data = bc.apply_tamper(FIXTURE.read_bytes(), vector["tamper_id"])
    mine = bc.validate_bytes(data)
    assert mine["verdict"] == "REJECT"
    for code in vector["expected"]["errors_contains"]: assert any(e.startswith(code) for e in mine["errors"]), mine
    p = tmp_path/"t.qeb"; p.write_bytes(data)
    theirs, rc = existing_verdict(p)
    # Verdict parity is required; exact error lists may differ in extra codes
    # (e.g. this checker and the Rust/Python pair treat copper bindings alike here).
    assert theirs == "REJECT" and rc == 1

def test_rebuild_and_resign_limitation_is_explicit():
    files = bc._read_all(FIXTURE.read_bytes()); orig_key = json.loads(files["secure-core/verifying-key.json"])["verifying_key_hex"]
    rebuilt = bc.rebuild_and_resign(FIXTURE.read_bytes())
    # Without a trust anchor: internally consistent (the documented limitation).
    assert bc.validate_bytes(rebuilt)["verdict"] == "PASS_LIMITED_CLAIMS"
    # With the original key pinned externally: rejected.
    pinned = bc.validate_bytes(rebuilt, pinned_key_hex=orig_key)
    assert pinned["verdict"] == "REJECT" and "PINNED_KEY_MISMATCH" in pinned["errors"]
    # Existing verifier agrees on the internal verdict, proving the limitation
    # is a property of bundled-key verification, not of this checker.
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".qeb", delete=False) as f: f.write(rebuilt); name=f.name
    try: assert existing_verdict(name)[0] == "PASS_LIMITED_CLAIMS"
    finally: os.unlink(name)
    vec = [v for v in VECTORS["vectors"] if v["category"]=="rebuild_and_resign_limitation"][0]
    assert vec["expected"]["limitation"] is True
    assert "authenticity_against_attacker_who_rebuilds_and_resigns_bundle_with_own_key" in bc.UNSUPPORTED

def test_no_certification_or_physical_claim_in_pass():
    r = bc.validate(FIXTURE)
    assert r["claim_boundary"] == "SIMULATION_ONLY_NO_PHYSICAL_NO_CERTIFICATION"
    assert "physical_stop_or_safety_rated_estop" in r["unsupported_claims"]
    assert "certification_or_regulatory_compliance" in r["unsupported_claims"]
