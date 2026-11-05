"""Frontier Phase 1: humanoid registry integrity tests.

These tests guard honesty invariants, not world facts: seed names are
preserved, nothing is verified without evidence, and no universe-size
claim (e.g. an unsupported total company count) enters the registry.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "humanoids" / "tools"))
import validate_registry as vr  # noqa: E402

SEEDS = ["Leju Robot", "Kepler", "Tesla Optimus", "Sanctuary AI", "Fourier",
         "Boston Dynamics", "X-humanoid", "Unitree", "Engineai", "Robot Era",
         "Pndbotics", "Xpeng", "UBTech", "DEEP Robotics", "Physicalintelligence",
         "Limx Dynamics", "Tencent", "Pudu Robotics", "Booster Robotics", "RoMeLa",
         "JAKA Robotics", "AgiBot", "MagicLab", "Apptronik", "Agility"]


def candidates():
    path = ROOT / "research" / "humanoids" / "registry" / "candidates.jsonl"
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def test_registry_validates_clean():
    report = vr.validate(ROOT / "research" / "humanoids")
    assert report["ok"], report["errors"]
    assert report["counts"]["company"] == 25


def test_seed_names_preserved_exactly_and_unverified():
    recs = candidates()
    assert sorted(r["candidate_names"][0] for r in recs) == sorted(SEEDS)
    for r in recs:
        assert r["candidate_names"][0] in r["aliases"]
        assert r["verification"]["status"] == "candidate_unverified"
        assert r["canonical_name"] is None
        assert r["verification"]["evidence_source_ids"] == []
        assert r["sources"] == [] and r["provenance_claim_ids"] == []


def test_index_makes_no_universe_size_claim():
    index = json.loads((ROOT / "research/humanoids/registry/index.json").read_text())
    assert index["universe_size_claim"] is None
    assert index["verified_count"] == 0
    assert index["candidate_count"] == 25


def test_all_six_schemas_are_json_schema_documents():
    sdir = ROOT / "research" / "humanoids" / "schemas"
    files = sorted(sdir.glob("*.schema.json"))
    assert len(files) == 6
    for f in files:
        doc = json.loads(f.read_text())
        assert doc["$schema"].endswith("2020-12/schema") and doc["$id"]
        assert doc["type"] == "object" and doc["required"]


def test_verified_without_evidence_is_rejected(tmp_path):
    root = tmp_path / "humanoids"
    (root / "schemas").mkdir(parents=True); (root / "registry").mkdir()
    src = ROOT / "research" / "humanoids"
    for f in (src / "schemas").glob("*.json"):
        (root / "schemas" / f.name).write_text(f.read_text())
    for f in (src / "registry").iterdir():
        (root / "registry" / f.name).write_text(f.read_text())
    recs = [json.loads(l) for l in (root / "registry/candidates.jsonl").read_text().splitlines()]
    bad = copy.deepcopy(recs[0]); bad["verification"]["status"] = "verified"; bad["canonical_name"] = "Fabricated Co"
    (root / "registry/candidates.jsonl").write_text(json.dumps(bad) + "\n")
    report = vr.validate(root)
    assert not report["ok"] and any("fabrication guard" in e for e in report["errors"])


def test_phase1_docs_carry_required_disclaimers():
    legal = (ROOT / "docs/frontier-phase1/LEGAL-RESEARCH-ROADMAP.md").read_text()
    assert "not legal advice" in legal.lower()
    for term in ["EU AI Act", "Machinery Regulation", "GDPR", "Cyber Resilience Act",
                 "robots.txt", "export control"]:
        assert term.lower() in legal.lower(), term
    stop = (ROOT / "docs/frontier-phase1/VOICE-GESTURE-STOP-TRAINING-ROADMAP.md").read_text()
    for term in ["false-positive", "false-negative", "fail-closed", "abstention", "consent"]:
        assert term.lower() in stop.lower(), term
