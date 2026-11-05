"""Unit tests for tools/repro/repro.py (stdlib only; no network, no cargo)."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPRO = Path(__file__).resolve().parents[1] / "repro.py"
spec = importlib.util.spec_from_file_location("repro", REPRO)
assert spec is not None and spec.loader is not None
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)

DILIGENCE = """| README claim | Evidence | Clean-clone command |
|---|---|---|
| Simulated STOP | tests/test_app.py; docs/DILIGENCE.md | make test |
| Hardware badge | TEST-RESULTS rows | none in clone - hardware record |
| Missing thing | tests/does_not_exist_xyz.py | make test |
"""

QIP = """| Requirement | Lowest class | W4-N4 test ID or UNIMPLEMENTED |
|---|---|---|
| QIP-R1.1 | INTERVENE | QIP-ID-01 |
| QIP-R2.3 | AUTHORIZE | UNIMPLEMENTED |
"""


def test_sha256_known(tmp_path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"abc")
    assert repro.sha256_file(p) == hashlib.sha256(b"abc").hexdigest()


def test_parse_diligence_and_qip():
    d = repro.parse_diligence(DILIGENCE)
    assert [r["claim"] for r in d] == ["Simulated STOP", "Hardware badge", "Missing thing"]
    assert "tests/test_app.py" in d[0]["evidence_paths"]
    q = repro.parse_qip(QIP)
    assert q == [{"requirement": "QIP-R1.1", "lowest_class": "INTERVENE",
                  "trace": "QIP-ID-01"},
                 {"requirement": "QIP-R2.3", "lowest_class": "AUTHORIZE",
                  "trace": "UNIMPLEMENTED"}]


def test_checklist_unsupported_is_explicit(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("x")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "DILIGENCE.md").write_text("x")
    runs = {"python_tests": {"status": "PASS"}, "cargo_tests": {"status": "SKIPPED"}}
    cl = repro.build_checklist(tmp_path, DILIGENCE, QIP, runs)
    by = {c.get("claim") or c.get("requirement"): c for c in cl}
    assert by["Simulated STOP"]["status"] == "EVIDENCE_PRESENT"
    assert by["Hardware badge"]["status"] == "NOT_CLONE_VERIFIABLE"
    assert by["Missing thing"]["status"] == "EVIDENCE_MISSING"
    assert by["QIP-R2.3"]["status"] == "UNSUPPORTED_EXPLICIT"
    # A trace is never upgraded to a conformance/class claim.
    assert by["QIP-R1.1"]["status"] == "TRACE_PRESENT_NO_CLASS_CLAIM"
    assert by["Clean-clone build/test reproduction on this host"]["status"] == \
        "SUPPORTED_FOR_THIS_RUN"


def test_record_only_main_no_fake_pass(tmp_path):
    repo = tmp_path / "repo"
    (repo / "docs" / "specs" / "intervention-profile").mkdir(parents=True)
    (repo / "docs" / "DILIGENCE.md").write_text(DILIGENCE)
    (repo / "docs" / "specs" / "intervention-profile" / "QIP-v0.1.md").write_text(QIP)
    rc = repro.main(["--repo", str(repo), "--out", "out", "--mode", "record-only"])
    assert rc == 0  # nothing executed, nothing failed; skips are not passes
    manifest = json.loads((repo / "out" / "environment-manifest.json").read_text())
    assert all(r["status"] == "SKIPPED" for r in manifest["runs"].values())
    md = (repo / "out" / "claim-to-evidence.md").read_text()
    assert "UNSUPPORTED_EXPLICIT" in md and "NOT certification" in md
    assert "QIP-R2.3" in md
    run_row = [c for c in json.loads((repo / "out" / "claim-to-evidence.json").read_text())
               if c["kind"] == "repro-run"][0]
    assert run_row["status"] == "UNSUPPORTED_EXPLICIT"  # record-only proves nothing


def test_markdown_lists_no_artifacts_explicitly(tmp_path):
    manifest = {"schema": repro.SCHEMA, "generated_at_utc": "t",
                "git": {"commit": "abc"}, "runs": {}}
    md = repro.render_markdown(manifest, [], [])
    assert "none found" in md
