"""Self-describing summary provenance: a count must carry its run.

Fail-direction: every provenance field is stripped in turn and
require_self_describing must reject the result; a bare (pre-fix shape)
summary with only total_results must also be rejected.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from run import (PROVENANCE_FIELDS, enrich_summary,  # noqa: E402
                 require_self_describing, summarize)

HERE = Path(__file__).parent
RESULTS = HERE.parent / "results"
CORPUS_DIR = HERE.parent / "corpus"
UTC = "2026-11-06T00:00:00Z"
COMMIT = "a" * 40
TOOLCHAIN = {"python": "3.11.15", "rustc": "rustc 1.99.1"}


def _full_cases():
    cases = {}
    for path in sorted(CORPUS_DIR.glob("*.jsonl")):
        if path.name == "mutations.jsonl":
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                c = json.loads(line)
                cases[c["id"]] = c
    return cases


def test_summarize_carries_all_provenance_fields():
    s = summarize([], {}, complete=True, finished_utc=UTC, commit=COMMIT, toolchain=TOOLCHAIN)
    for field in PROVENANCE_FIELDS:
        assert field in s and s[field] not in (None, "", {}, [])
    assert s["complete"] is True
    assert s["total_results"] == 0
    assert require_self_describing(s) is s


def test_summarize_defaults_to_incomplete_never_complete():
    # A summary built without an explicit finished run must not claim
    # completeness; that is how a partial/S0-stopped run is represented.
    s = summarize([], {})
    assert s["complete"] is False
    assert require_self_describing(s) is s


def test_generator_is_aggregated_from_cases_actually_run():
    s = summarize([], _full_cases(), complete=True, finished_utc=UTC,
                  commit=COMMIT, toolchain=TOOLCHAIN)
    # Generated + hand-written cases: both generator dicts, verbatim.
    assert isinstance(s["generator"], list) and len(s["generator"]) == 2
    models = {g["model"] for g in s["generator"]}
    assert models == {"BLOCKED-no-real-model-template-corpus", "hand-written"}
    assert all(g["seed"] == 20261105 for g in s["generator"])


@pytest.mark.parametrize("field", list(PROVENANCE_FIELDS))
def test_require_self_describing_fails_without_each_field(field):
    s = enrich_summary({"total_results": 63012}, _full_cases(), complete=True,
                       finished_utc=UTC, commit=COMMIT, toolchain=TOOLCHAIN)
    del s[field]
    with pytest.raises(ValueError):
        require_self_describing(s)


def test_bare_total_results_summary_is_rejected():
    # The exact pre-fix summary shape: a count with no run behind it.
    with pytest.raises(ValueError):
        require_self_describing({"total_results": 63012})
    with pytest.raises(ValueError):
        require_self_describing({**enrich_summary(
            {"total_results": 63012}, {}, complete=True, finished_utc=UTC,
            commit=COMMIT, toolchain=TOOLCHAIN), "complete": "yes"})


def test_committed_summary_is_self_describing_and_matches_results():
    summary = json.loads((RESULTS / "summary.json").read_text())
    assert require_self_describing(summary) is summary
    assert summary["complete"] is True
    lines = [l for l in (RESULTS / "results.jsonl").read_text().splitlines()
             if l.strip()]
    assert summary["total_results"] == len(lines)
    # finished_utc must be a real UTC timestamp, commit a real commit
    # that is HEAD or an ancestor of HEAD (the run that produced it).
    datetime.strptime(summary["finished_utc"], "%Y-%m-%dT%H:%M:%SZ")
    commit = summary["commit"]
    assert len(commit) == 40 and all(c in "0123456789abcdef" for c in commit)
    repo = HERE.parents[2]
    ok = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                         commit, "HEAD"], capture_output=True)
    assert ok.returncode == 0, f"summary commit {commit} is not in this history"
    # Full run = template + hand-written + deterministic mutations.
    gens = summary["generator"]
    assert isinstance(gens, list)
    assert {g["model"] for g in gens} == {
        "BLOCKED-no-real-model-template-corpus", "hand-written",
        "none-deterministic-mutation"}
    toolchain = summary["toolchain"]
    assert toolchain["python"] and toolchain["platform"]
    assert "rustc" in toolchain and "cargo" in toolchain
