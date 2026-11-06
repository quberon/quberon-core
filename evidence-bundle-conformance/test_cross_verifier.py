"""ind-3 cross-verifier: a second, independent evidence-bundle verifier.

independent_verify.py was written from crates/quberon-evidence-bundle/
SPEC.md without reading the Rust source and without importing or loading
tools/quberon-verify or bundle_check.py. This suite tests it from outside
(the F2 pattern): exact parity with tools/quberon-verify on both
committed fixtures, verdict parity on a deterministic mutation corpus,
and documented spec defects (SPEC-DEFECTS.md) where SPEC.md cannot
adjudicate a disagreement.

SIMULATION ONLY; no physical/certification claim. See SPEC-DEFECTS.md.
"""
import ast
import io
import json
import subprocess
import sys
import zipfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

HERE = Path(__file__).parent
ROOT = HERE.parents[0]
sys.path.insert(0, str(HERE))
import independent_verify as iv

FIXTURE = ROOT / "tools/quberon-verify/tests/fixtures/simulated-stop.qeb"
TAMPERED = ROOT / "tools/quberon-verify/tests/fixtures/tampered-replay.qeb"
REFERENCE_CLI = ROOT / "tools/quberon-verify/quberon-verify"
REFERENCE = SourceFileLoader(
    "quberon_verify_reference", str(REFERENCE_CLI)).load_module()

COMMON_KEYS = ("verdict", "format_version", "checks", "errors",
               "supported_claims", "unsupported_claims")


def reference_report(path):
    return REFERENCE.validate(str(path))


def write_bundle(tmp_path, files, name="mutated.qeb"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for entry in sorted(files):
            info = zipfile.ZipInfo(entry, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o600 << 16
            z.writestr(info, files[entry])
    path = tmp_path / name
    path.write_bytes(buf.getvalue())
    return path


def read_fixture(path=FIXTURE):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def json_entry(files, name, mutate):
    obj = json.loads(files[name])
    mutate(obj)
    files[name] = (json.dumps(obj, indent=2) + "\n").encode()
    return files


def flip_byte(files, name, offset=0):
    data = bytearray(files[name])
    data[offset] ^= 1
    files[name] = bytes(data)
    return files


def set_entry(files, name, value):
    files[name] = value
    return files


def pop_entry(files, name):
    files.pop(name, None)
    return files


# --- Independence -----------------------------------------------------------

def test_independent_verifier_imports_stdlib_only():
    tree = ast.parse((HERE / "independent_verify.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= {"hashlib", "io", "json", "struct", "sys", "zipfile"}
    assert "subprocess" not in imported and "importlib" not in imported


def test_independent_verifier_does_not_load_reference_source():
    source = (HERE / "independent_verify.py").read_text()
    # No dynamic loading / exec of another implementation. (The docstring
    # names the reference only to state that it is NOT used.)
    assert "SourceFileLoader" not in source
    assert "load_module" not in source
    assert "exec(" not in source and "eval(" not in source


# --- Exact parity on every committed fixture --------------------------------

@pytest.mark.parametrize("fixture,expected_verdict,expected_rc",
                         [(FIXTURE, "PASS_LIMITED_CLAIMS", 0),
                          (TAMPERED, "REJECT", 1)])
def test_fixture_exact_parity(fixture, expected_verdict, expected_rc):
    mine = iv.validate_path(fixture)
    theirs = reference_report(fixture)
    assert mine["verdict"] == theirs["verdict"] == expected_verdict
    for key in COMMON_KEYS:
        assert mine[key] == theirs[key], (key, mine[key], theirs[key])
    assert mine["supported_claims"] == (
        iv.SUPPORTED_CLAIMS if expected_verdict.startswith("PASS") else [])
    assert "physical_stop_or_safety_rated_estop" in mine["unsupported_claims"]
    assert "certification_or_regulatory_compliance" not in mine["supported_claims"]


@pytest.mark.parametrize("fixture,expected_rc",
                         [(FIXTURE, 0), (TAMPERED, 1)])
def test_fixture_cli_exit_code_parity(fixture, expected_rc, tmp_path):
    mine = subprocess.run([sys.executable, str(HERE / "independent_verify.py"),
                           str(fixture)], capture_output=True, text=True)
    theirs = subprocess.run([sys.executable, str(REFERENCE_CLI), str(fixture)],
                            capture_output=True, text=True)
    assert mine.returncode == theirs.returncode == expected_rc
    assert json.loads(mine.stdout)["verdict"] == json.loads(theirs.stdout)["verdict"]


def test_cli_usage_exit_2_and_missing_file_rejects(tmp_path):
    r = subprocess.run([sys.executable, str(HERE / "independent_verify.py")],
                       capture_output=True, text=True)
    assert r.returncode == 2
    assert json.loads(r.stdout)["verdict"] == "REJECT"
    missing = subprocess.run(
        [sys.executable, str(HERE / "independent_verify.py"),
         str(tmp_path / "nope.qeb")], capture_output=True, text=True)
    assert missing.returncode == 1
    assert json.loads(missing.stdout)["errors"] == ["BUNDLE_EMPTY_OR_NOT_ZIP"]


# --- Differential mutation corpus -------------------------------------------
# Each mutation is a deterministic edit of the good fixture. Verdict parity
# is required for all of them; exact error-list parity is required for the
# EXACT subset (mutations whose outcome SPEC.md + fixture data determine).

def _mutations():
    return {
        "flip_replay_task_output": lambda f: flip_byte(f, "copper/replay-task-outputs.bin"),
        "flip_original_copper": lambda f: flip_byte(f, "copper/original_0.copper", 100),
        "flip_comparison": lambda f: flip_byte(f, "copper/comparison.txt", 0),
        "envelope_sequence_plus1": lambda f: json_entry(
            f, "secure-core/envelope.json", lambda o: o.__setitem__("sequence", o["sequence"] + 1)),
        "envelope_signature_flip": lambda f: json_entry(
            f, "secure-core/envelope.json",
            lambda o: o.__setitem__("signature", ("0" if o["signature"][0] != "0" else "1") + o["signature"][1:])),
        "envelope_action_go": lambda f: json_entry(
            f, "secure-core/envelope.json", lambda o: o.__setitem__("action", "GO")),
        "audit_record_hash_zero": lambda f: json_entry(
            f, "secure-core/audit.json", lambda o: o[0].__setitem__("record_hash", "0" * 64)),
        "audit_seq_gap": lambda f: json_entry(
            f, "secure-core/audit.json", lambda o: o[0].__setitem__("seq", 2)),
        "audit_empty": lambda f: set_entry(f, "secure-core/audit.json", b"[]"),
        "env_remove_git_commit": lambda f: json_entry(
            f, "environment.json", lambda o: o.pop("git_commit")),
        "env_git_commit_uppercase": lambda f: json_entry(
            f, "environment.json", lambda o: o.__setitem__("git_commit", o["git_commit"].upper())),
        "env_empty_arch": lambda f: json_entry(
            f, "environment.json", lambda o: o.__setitem__("arch", "")),
        "delete_replay_outputs": lambda f: pop_entry(f, "copper/replay-task-outputs.bin"),
        "add_unlisted": lambda f: set_entry(f, "extra.txt", b"unlisted"),
        "add_unsafe_path": lambda f: set_entry(f, "../evil.txt", b"x"),
        "manifest_version_99": lambda f: json_entry(
            f, "manifest.json", lambda o: o.__setitem__("version", 99)),
        "manifest_format_other": lambda f: json_entry(
            f, "manifest.json", lambda o: o.__setitem__("format", "other")),
        "manifest_physical_claim": lambda f: json_entry(
            f, "manifest.json", lambda o: o.__setitem__("physical_state_claim", "STOPPED")),
        "manifest_not_simulation_only": lambda f: json_entry(
            f, "manifest.json", lambda o: o.__setitem__("simulation_only", False)),
        "manifest_listed_size_wrong": lambda f: json_entry(
            f, "manifest.json", lambda o: o["files"][0].__setitem__("size", 1)),
        "claims_supported_shortened": lambda f: json_entry(
            f, "manifest.json", lambda o: o["claims"].__setitem__("supported_if_valid", o["claims"]["supported_if_valid"][:-1])),
        "claims_unsupported_extra": lambda f: json_entry(
            f, "manifest.json", lambda o: o["claims"]["unsupported"].append("certification_granted")),
        "attestation_signature_flip": lambda f: json_entry(
            f, "attestation.json",
            lambda o: o.__setitem__("signature", ("0" if o["signature"][0] != "0" else "1") + o["signature"][1:])),
        "attestation_manifest_hash_wrong": lambda f: json_entry(
            f, "attestation.json", lambda o: o.__setitem__("manifest_sha256", "0" * 64)),
        "decision_code_other": lambda f: json_entry(
            f, "secure-core/decision.json", lambda o: o.__setitem__("code", "ACCEPTED_OTHER")),
        "decision_physical_claim": lambda f: json_entry(
            f, "secure-core/decision.json", lambda o: o.__setitem__("physical_state_claim", "STOPPED")),
        "decision_sequence_mismatch": lambda f: json_entry(
            f, "secure-core/decision.json", lambda o: o.__setitem__("sequence", 99)),
        "envelope_kid_other": lambda f: json_entry(
            f, "secure-core/envelope.json", lambda o: o.__setitem__("kid", "other-key")),
        "comparison_authorized_false": lambda f: set_entry(
            f, "copper/comparison.txt",
            f["copper/comparison.txt"].replace(b"authorized=true", b"authorized=false")),
    }


EXACT_ERROR_MUTATIONS = {
    "flip_replay_task_output", "flip_original_copper", "envelope_sequence_plus1",
    "envelope_signature_flip", "envelope_action_go", "audit_record_hash_zero",
    "audit_seq_gap", "audit_empty", "env_remove_git_commit",
    "env_git_commit_uppercase", "delete_replay_outputs", "add_unlisted",
    "manifest_version_99", "manifest_physical_claim", "claims_supported_shortened",
    "attestation_signature_flip", "decision_code_other", "decision_physical_claim",
    "decision_sequence_mismatch", "comparison_authorized_false",
}


@pytest.mark.parametrize("mutation_name", sorted(_mutations()))
def test_mutation_verdict_parity(mutation_name, tmp_path):
    files = _mutations()[mutation_name](read_fixture())
    path = write_bundle(tmp_path, files)
    mine = iv.validate_path(path)
    theirs = reference_report(path)
    assert mine["verdict"] == theirs["verdict"] == "REJECT", (
        mutation_name, mine, theirs)
    if mutation_name in EXACT_ERROR_MUTATIONS:
        assert mine["errors"] == theirs["errors"], (
            mutation_name, mine["errors"], theirs["errors"])
        assert mine["checks"] == theirs["checks"], (
            mutation_name, mine["checks"], theirs["checks"])


def test_not_a_zip_and_empty_zip_parity(tmp_path):
    garbage = tmp_path / "garbage.qeb"
    garbage.write_bytes(b"not a zip at all")
    assert iv.validate_path(garbage)["errors"] == ["BUNDLE_EMPTY_OR_NOT_ZIP"]
    assert reference_report(garbage)["errors"] == ["BUNDLE_EMPTY_OR_NOT_ZIP"]
    empty = write_bundle(tmp_path, {}, "empty.qeb")
    assert iv.validate_path(empty)["verdict"] == "REJECT"
    assert reference_report(empty)["verdict"] == "REJECT"
    assert "MANIFEST_MISSING" in iv.validate_path(empty)["errors"]


def test_duplicate_entry_rejected_by_both(tmp_path):
    files = read_fixture()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for entry in sorted(files):
            z.writestr(entry, files[entry])
        z.writestr("environment.json", files["environment.json"])
    path = tmp_path / "dup.qeb"
    path.write_bytes(buf.getvalue())
    assert iv.validate_path(path)["verdict"] == "REJECT"
    assert reference_report(path)["verdict"] == "REJECT"
    assert "DUPLICATE_ENTRY" in iv.validate_path(path)["errors"]


# --- Documented spec defects (SPEC-DEFECTS.md) -------------------------------

def test_attestation_descriptive_fields_are_a_documented_gap(tmp_path):
    # SD-5: kid/domain in attestation.json are unchecked by the reference;
    # this verifier matches that verdict for parity. This test documents
    # the gap -- it does not claim the behaviour is desirable.
    files = json_entry(read_fixture(), "attestation.json",
                       lambda o: o.__setitem__("kid", "some-other-key"))
    files = json_entry(files, "attestation.json",
                       lambda o: o.__setitem__("domain", "WRONG/DOMAIN"))
    path = write_bundle(tmp_path, files)
    assert iv.validate_path(path)["verdict"] == "PASS_LIMITED_CLAIMS"
    assert reference_report(path)["verdict"] == "PASS_LIMITED_CLAIMS"
    assert "SD-5" in (HERE / "SPEC-DEFECTS.md").read_text()


def test_malformed_types_reject_not_crash(tmp_path):
    # SD-8: the reference crashes on these inputs (observed, recorded in
    # SPEC-DEFECTS.md). SPEC.md requires REJECT; assert only this
    # verifier's behaviour so a reference fix closes the defect cleanly.
    cases = {
        "audit_object": lambda f: set_entry(
            f, "secure-core/audit.json", json.dumps({"seq": 1}).encode()),
        "manifest_files_string": lambda f: json_entry(
            f, "manifest.json", lambda o: o.__setitem__("files", "x")),
        "env_git_commit_int": lambda f: json_entry(
            f, "environment.json", lambda o: o.__setitem__("git_commit", 123)),
        "envelope_version_string": lambda f: json_entry(
            f, "secure-core/envelope.json", lambda o: o.__setitem__("version", "1")),
    }
    for name, mutate in cases.items():
        path = write_bundle(tmp_path, mutate(read_fixture()), name + ".qeb")
        report = iv.validate_path(path)
        assert report["verdict"] == "REJECT", (name, report)


def test_spec_defects_file_covers_all_ids():
    text = (HERE / "SPEC-DEFECTS.md").read_text()
    for defect_id in ("SD-1", "SD-2", "SD-3", "SD-4", "SD-5",
                      "SD-6", "SD-7", "SD-8", "SD-9"):
        assert defect_id in text


def test_no_certification_or_physical_claim_in_pass():
    report = iv.validate_path(FIXTURE)
    assert report["verdict"] == "PASS_LIMITED_CLAIMS"
    assert report["claim_boundary"] == "SIMULATION_ONLY_NO_PHYSICAL_NO_CERTIFICATION"
    assert "certification_or_regulatory_compliance" in report["unsupported_claims"]
