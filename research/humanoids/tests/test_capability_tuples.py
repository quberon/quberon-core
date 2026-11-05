"""Wave 5 F6 capability-tuple tests: honesty guards, not world facts."""
import copy
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "humanoids" / "tools"))
import validate_registry as vr  # noqa: E402

HUM = ROOT / "research" / "humanoids"
TUPLES = HUM / "capability-tuples" / "capability-tuples.jsonl"


def tuples():
    return [json.loads(l) for l in TUPLES.read_text().splitlines() if l.strip()]


def copy_tree(tmp_path):
    dst = tmp_path / "humanoids"
    shutil.copytree(HUM, dst, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    return dst


def rewrite(dst, recs):
    (dst / "capability-tuples" / "capability-tuples.jsonl").write_text(
        "\n".join(json.dumps(r) for r in recs) + "\n")


def test_capability_tuples_validate_and_count():
    report = vr.validate(HUM)
    assert report["ok"], report["errors"]
    assert report["counts"]["capability_tuple"] == 78
    assert report["capability_tuple_epistemic_counts"] == {
        "inferred": 1, "not_found": 65, "observed": 6, "unknown": 6}
    recs = tuples()
    assert len(recs) == 78 and len({r["tuple_id"] for r in recs}) == 78
    # Every candidate has explicit R10 stop/status/reset tuples.
    for cid in {r["entity"]["candidate_id"] for r in recs}:
        caps = {r["capability"] for r in recs if r["entity"]["candidate_id"] == cid}
        assert {"intervention_stop", "status_observation", "latch_reset"} <= caps
    # No promotion, no QIP mapping claim anywhere.
    assert all(r["entity"]["canonical_name"] is None for r in recs)
    assert all(r["entity"]["entity_verification_status"] == "candidate_unverified" for r in recs)
    assert all(r["qip_r10"]["mapping_claimed"] is False for r in recs)


def test_observed_requires_method_and_inferred_is_not_claimed():
    recs = {r["tuple_id"]: r for r in tuples()}
    assert recs["cap-unitree-status"]["epistemic_status"] == "observed"
    assert "GetFsmId" in recs["cap-unitree-status"]["adapter"]["api_or_method"]
    unitree_stop = recs["cap-unitree-stop"]
    assert unitree_stop["epistemic_status"] == "inferred"
    assert unitree_stop["qip_r10"]["mapping_status"] == "inferred_not_claimed"


def test_fabricated_observed_tuple_is_rejected(tmp_path):
    dst = copy_tree(tmp_path)
    recs = [json.loads(l) for l in (dst / "capability-tuples" / "capability-tuples.jsonl").read_text().splitlines()]
    bad = copy.deepcopy(recs[0])
    bad["epistemic_status"] = "observed"  # no api_or_method added
    recs[0] = bad
    rewrite(dst, recs)
    report = vr.validate(dst)
    assert not report["ok"] and any("observed tuple requires" in e for e in report["errors"])


def test_qip_mapping_claim_is_rejected(tmp_path):
    dst = copy_tree(tmp_path)
    recs = [json.loads(l) for l in (dst / "capability-tuples" / "capability-tuples.jsonl").read_text().splitlines()]
    recs[0]["qip_r10"]["mapping_claimed"] = True
    rewrite(dst, recs)
    report = vr.validate(dst)
    assert not report["ok"] and any("mapping_claimed must be false" in e for e in report["errors"])
