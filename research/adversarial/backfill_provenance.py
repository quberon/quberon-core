"""Backfill provenance into results/postmerge-summary.json, honestly.

Reads only committed evidence (evidence/adversarial-postmerge.md and
evidence/postmerge-full-run.txt) and adds the self-describing fields that
summary lacked: complete, citable, commit, started_utc, finished_utc,
toolchain, generator.

Nothing is invented: a value with no committed source becomes null. The
postmerge log contains no UTC timestamp and the markdown names no
toolchain, so this summary gets finished_utc=null and null toolchain
entries -- the fields exist and the absence is explicit, instead of a
fabricated date or version. Completion is not assumed either: the log
must end with the runner's final JSON block followed by RC=0, and its
total_results must match the summary's, or this script refuses.

Idempotent apart from the write itself: re-running rewrites the same
provenance from the same evidence; pre-existing result keys are not
recomputed or reordered in meaning (they are preserved as parsed).

Usage:
  python research/adversarial/backfill_provenance.py [--check]
--check exits 1 (printing what is missing) if the summary lacks the
required provenance fields. The atomic write follows ops.longrun
semantics via research/adversarial/provenance.py (which prefers
ops.longrun when importable).
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from provenance import REQUIRED_FIELDS  # noqa: E402

RESULTS = HERE / "results"
EVIDENCE = HERE / "evidence"
SUMMARY = RESULTS / "postmerge-summary.json"


def _write_preserving_order(path, data):
    """Atomic write like ops.longrun, without sort_keys: backfilling must
    not reorder the pre-existing result keys of a historical artefact."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _must(pattern, text):
    m = re.search(pattern, text)
    assert m is not None, f"evidence pattern not found: {pattern}"
    return m


def postmerge_provenance(summary):
    md = (EVIDENCE / "adversarial-postmerge.md").read_text()
    log = (EVIDENCE / "postmerge-full-run.txt").read_text()
    commit = _must(r"`([0-9a-f]{40})`", md).group(1)
    command = _must(r"- Command: `([^`]+)`", md).group(1)
    sha = _must(r"SHA-256 `([0-9a-f]{64})`", md).group(1)
    # Completion evidence: final runner JSON block, then RC=0, and the
    # counts must agree with the summary being annotated.
    assert log.rstrip().endswith("RC=0"), "postmerge log does not end RC=0"
    logged = _must(r'"total_results": (\d+)', log).group(1)
    assert int(logged) == summary["total_results"], (
        f"log total_results={logged} != summary {summary['total_results']}")
    return dict(
        complete=True,
        reason="finished (RC=0 in evidence/postmerge-full-run.txt)",
        commit=commit,
        started_utc=None,
        finished_utc=None,
        toolchain={"python": None, "cargo": None, "rustc": None,
                   "platform": None, "machine": None, "host": None,
                   "executable": None, "git_commit": commit,
                   "cpu_count": None},
        generator={"script": "research/adversarial/run.py",
                   "command": command,
                   "model": "none-deterministic-template-corpus "
                            "(per adversarial-postmerge.md)",
                   "cases": 56506, "mutations": 50000},
        extra={"provenance_sources": ["evidence/adversarial-postmerge.md",
                                      "evidence/postmerge-full-run.txt"],
               "results_jsonl_sha256_from_evidence_md": sha,
               "backfilled": True,
               "backfill_note": ("finished_utc/toolchain are null: no UTC "
                                 "timestamp or toolchain is recorded in "
                                 "the committed postmerge evidence.")})


def backfill(path=SUMMARY):
    data = json.loads(Path(path).read_text())
    spec = postmerge_provenance(data)
    data["complete"] = spec["complete"]
    data["citable"] = bool(spec["complete"])
    data["reason"] = spec["reason"]
    data["commit"] = spec["commit"]
    data["started_utc"] = spec["started_utc"]
    data["finished_utc"] = spec["finished_utc"]
    data["toolchain"] = spec["toolchain"]
    data["generator"] = spec["generator"]
    extra = spec["extra"]
    assert isinstance(extra, dict)
    prov: dict = {"source": "research/adversarial/backfill_provenance.py"}
    for k, v in extra.items():
        prov[k] = v
    data["provenance"] = prov
    _write_preserving_order(Path(path), data)
    return data


def check(path=SUMMARY):
    try:
        data = json.loads(Path(path).read_text())
    except Exception as e:  # unreadable is not citable
        return [f"{path}: unreadable ({e})"]
    bad = [f"missing {k}" for k in REQUIRED_FIELDS if k not in data]
    if data.get("complete") and not data.get("citable"):
        bad.append("complete but not citable")
    tc = data.get("toolchain")
    if not isinstance(tc, dict) or "git_commit" not in tc:
        bad.append("toolchain missing git_commit")
    gen = data.get("generator")
    if not isinstance(gen, dict) or not gen.get("script"):
        bad.append("generator missing script")
    return bad


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--check"]:
        bad = check()
        if bad:
            print("postmerge-summary.json: " + "; ".join(bad))
            return 1
        print("postmerge-summary.json carries required provenance fields")
        return 0
    if argv:
        print(__doc__)
        return 2
    data = backfill()
    print(f"postmerge-summary.json: complete={data['complete']} "
          f"citable={data['citable']} commit={data['commit']} "
          f"finished_utc={data['finished_utc']} "
          f"total_results={data.get('total_results')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
