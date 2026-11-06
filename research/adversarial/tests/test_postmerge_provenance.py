"""Postmerge summary must describe the run that produced its count.

The committed postmerge-summary.json reported total_results=63012 with
no complete/commit/finished_utc/toolchain/generator. These tests pin
(a) the backfilled historical file to its committed evidence -- with
nulls, not inventions, where that evidence is silent -- and (b) future
run.py summaries to carrying the same fields at write time.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from provenance import REQUIRED_FIELDS, enrich_summary, is_citable  # noqa: E402

HERE = os.path.dirname(__file__)
ADV = os.path.join(HERE, "..")
POSTMERGE = os.path.join(ADV, "results", "postmerge-summary.json")


def _postmerge():
    with open(POSTMERGE) as f:
        return json.load(f)


def test_postmerge_summary_is_self_describing():
    data = _postmerge()
    for k in REQUIRED_FIELDS:
        assert k in data, k
    assert data["total_results"] == 63012
    assert data["escapes"] == [] and data["s0_violations"] == []


def test_postmerge_provenance_matches_committed_evidence_not_invention():
    data = _postmerge()
    # evidence/adversarial-postmerge.md: code under test + command;
    # evidence/postmerge-full-run.txt: final JSON block, then RC=0.
    assert data["complete"] is True and data["citable"] is True
    assert data["commit"] == "c19501c8b8e4008fcc6724964baa57be158f62bd"
    assert data["toolchain"]["git_commit"] == data["commit"]
    assert "--mutations 50000" in data["generator"]["command"]
    assert data["generator"]["cases"] == 56506
    assert data["provenance"]["backfilled"] is True
    assert (data["provenance"]["results_jsonl_sha256_from_evidence_md"]
            == "3ca8169cf409cd196c02a692d2b9c6536e76e157f54aee272c8f18a7b384d9ee")
    # No UTC timestamp or toolchain is recorded in the committed
    # postmerge evidence: null, never a fabricated date/version.
    assert data["started_utc"] is None and data["finished_utc"] is None
    assert data["toolchain"]["python"] is None
    assert data["toolchain"]["cargo"] is None
    assert is_citable(POSTMERGE) is True


def test_backfill_check_passes():
    proc = subprocess.run(
        [sys.executable, os.path.join(ADV, "backfill_provenance.py"), "--check"],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_enrich_complete_and_partial():
    done = enrich_summary({"total_results": 3}, complete=True, reason="finished",
                          commit="abc123", toolchain_info={"python": "3.11"},
                          generator={"script": "run.py"})
    for k in REQUIRED_FIELDS:
        assert k in done, k
    assert done["citable"] is True and "WARNING" not in done
    assert done["finished_utc"]  # a live run observes its own finish time
    partial = enrich_summary({"total_results": 1}, complete=False,
                             reason="S0 violation: stopped early")
    assert partial["complete"] is False and partial["citable"] is False
    assert "PARTIAL" in partial["WARNING"]


def test_small_run_writes_citable_self_describing_summary(tmp_path):
    out, summary = tmp_path / "r.jsonl", tmp_path / "s.json"
    proc = subprocess.run(
        [sys.executable, os.path.join(ADV, "run.py"),
         "--corpus", os.path.join(ADV, "corpus", "hand-written.jsonl"),
         "--paths", "direct", "--out", str(out), "--summary", str(summary)],
        capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(summary.read_text())
    for k in REQUIRED_FIELDS:
        assert k in data, k
    assert data["complete"] is True and data["citable"] is True
    assert data["reason"] == "finished"
    assert data["started_utc"] and data["finished_utc"]
    assert data["commit"] and data["toolchain"]["python"]
    assert data["generator"]["script"] == "research/adversarial/run.py"
    assert data["provenance"]["source"]  # ops.longrun or named fallback
    assert is_citable(summary) is True
