#!/usr/bin/env python3
"""Second, independent verifier for quberon-evidence-bundle v1.

Written from crates/quberon-evidence-bundle/SPEC.md only. The Rust crate
source was not read. It does not import, load, or shell out to
tools/quberon-verify or to bundle_check.py (the F2 checker); agreement
with tools/quberon-verify is established only by the differential tests
in test_cross_verifier.py, from outside both implementations.

Sources for every constant, in order of authority:
  * SPEC.md: domain separators, length-prefixed canonical payload_hash
    form, audit hash form and genesis, environment field list, bundle
    entry list, attestation message form, rejection classes, and the
    unsupported-claims enumeration in the Claims section.
  * The committed fixture's own manifest.json claims lists and the
    JSON field names observable in the fixture entries: SPEC.md does
    not enumerate the supported-claims strings, the exact error-code
    strings, the check-name strings, the envelope/decision field
    literals (other than action STOP and ACCEPTED_*), the
    comparison.txt tokens, or the attestation/decision JSON schemas.
    Those gaps are recorded in SPEC-DEFECTS.md (SD-1..SD-5); the
    observable fixture values are used so a second implementer can
    reproduce a verdict at all. This is a spec defect, not a licence
    to upgrade any claim.

SIMULATION ONLY. NO PHYSICAL CONTROL. NOT A SAFETY-RATED E-STOP.
NO CERTIFICATION CLAIM. A PASS is PASS_LIMITED_CLAIMS only, and only
for the key bundled inside the artifact (see SPEC-DEFECTS.md SD-9 /
the rebuild-and-resign limitation).

Usage:
  python3 independent_verify.py <bundle.qeb>
Exit 0 iff PASS_LIMITED_CLAIMS, 1 on REJECT, 2 on usage. JSON on stdout.
Stdlib only, offline.
"""
import hashlib
import io
import json
import struct
import sys
import zipfile

# --- Constants stated in SPEC.md -------------------------------------------
PAYLOAD_DOMAIN = b"QUBERON-SECURE-CORE/PAYLOAD/v1\x00"
SIGN_DOMAIN = b"QUBERON-SECURE-CORE/SIGN/v1\x00"
AUDIT_DOMAIN = b"QUBERON-SECURE-CORE/AUDIT/v1\x00"
ATTEST_DOMAIN = b"QUBERON-EVIDENCE-BUNDLE/ATTEST/v1\x00"
GENESIS_PREV_HASH = "0" * 64
BUNDLE_ENTRIES = (
    "copper/comparison.txt",
    "copper/original-task-outputs.bin",
    "copper/original_0.copper",
    "copper/replay-task-outputs.bin",
    "copper/replay_0.copper",
    "environment.json",
    "secure-core/audit.json",
    "secure-core/decision.json",
    "secure-core/envelope.json",
    "secure-core/verifying-key.json",
)
ENVIRONMENT_FIELDS = (
    "arch", "cargo_version", "copper_config_sha256", "copper_cu29_version",
    "created_utc", "git_commit", "os", "python_version", "rustc_version",
    "secure_core_cli_sha256", "secure_core_source_sha256",
)
# Unsupported list: enumerated in SPEC.md, Claims section.
UNSUPPORTED_CLAIMS = [
    "physical_stop_or_safety_rated_estop",
    "certification_or_regulatory_compliance",
    "signer_authority_beyond_bundled_self_asserted_key",
    "production_key_custody_hsm_or_tpm",
    "hardware_or_pi_execution",
    "latency_or_real_time_behaviour",
    "external_security_audit",
    "authenticity_against_attacker_who_rebuilds_and_resigns_bundle_with_own_key",
]
# Supported list: NOT enumerated in SPEC.md (SD-1). Values below are the
# exact strings carried in the committed fixture's manifest claims, which
# is the only SPEC-conformant place a second implementer can observe them.
SUPPORTED_CLAIMS = [
    "bundle_internal_integrity_sha256",
    "audit_chain_hash_linked",
    "envelope_signature_valid_for_bundled_key",
    "secure_core_decision_accepted_simulation_stop",
    "copper_replay_task_outputs_byte_identical",
    "copper_logs_byte_identical",
    "stop_recorded_in_copper_comparison",
]
# Field literals observable only in fixture JSON (SD-2/SD-4/SD-5).
ACCEPTED_DECISION_CODE = "ACCEPTED_SIMULATION_STOP_AUTHORIZATION"
COMPARISON_TOKENS = ("command=STOP", "authorized=true", "byte_identical=true")


# --- Ed25519 verification (RFC 8032, extended coordinates) ------------------
# Independent formulation: points are (X, Y, Z, T) extended twisted-Edwards
# coordinates for a=-1, unlike the affine formulation used elsewhere in
# this repository. Only verification is implemented; this verifier never signs.
_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)
_IDENTITY = (0, 1, 1, 0)


def _recover_x(y):
    xx = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    x = pow(xx, (_P + 3) // 8, _P)
    if (x * x - xx) % _P:
        x = x * _SQRT_M1 % _P
    return x if x % 2 == 0 else _P - x


def _decode_point(raw):
    if len(raw) != 32:
        raise ValueError("point must be 32 bytes")
    bits = int.from_bytes(raw, "little")
    y = bits & ((1 << 255) - 1)
    if y >= _P:
        raise ValueError("non-canonical y")
    x = _recover_x(y)
    if (x & 1) != (bits >> 255):
        x = _P - x
    return (x, y, 1, x * y % _P)


def _point_add(p, q):
    a = (p[1] - p[0]) * (q[1] - q[0]) % _P
    b = (p[1] + p[0]) * (q[1] + q[0]) % _P
    c = 2 * _D * p[3] * q[3] % _P
    dd = 2 * p[2] * q[2] % _P
    e, f, g, h = b - a, dd - c, dd + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _point_double(p):
    a = p[0] * p[0] % _P
    b = p[1] * p[1] % _P
    c = 2 * p[2] * p[2] % _P
    e = ((p[0] + p[1]) ** 2 - a - b) % _P
    g = b - a
    f = g - c
    h = -a - b
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _scalar_mult(point, scalar):
    result = _IDENTITY
    addend = point
    while scalar:
        if scalar & 1:
            result = _point_add(result, addend)
        addend = _point_double(addend)
        scalar >>= 1
    return result


def _points_equal(p, q):
    return ((p[0] * q[2] - q[0] * p[2]) % _P == 0
            and (p[1] * q[2] - q[1] * p[2]) % _P == 0)


_BASE_Y = 4 * pow(5, _P - 2, _P) % _P
_BASE_X = _recover_x(_BASE_Y)
_BASE = (_BASE_X, _BASE_Y, 1, _BASE_X * _BASE_Y % _P)


def ed25519_verify(public_key, message, signature):
    try:
        if len(public_key) != 32 or len(signature) != 64:
            return False
        r_point = _decode_point(signature[:32])
        a_point = _decode_point(public_key)
        s = int.from_bytes(signature[32:], "little")
        if s >= _L:
            return False
        h = int.from_bytes(
            hashlib.sha512(signature[:32] + public_key + message).digest(),
            "little") % _L
        return _points_equal(_scalar_mult(_BASE, s),
                             _point_add(r_point, _scalar_mult(a_point, h)))
    except Exception:
        return False


# --- Canonical hashes (SPEC.md, Algorithms) ---------------------------------
def _sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def _length_prefixed(buffer, chunk):
    return buffer + struct.pack(">Q", len(chunk)) + chunk


def canonical_payload_hash(envelope):
    """SHA-256 of domain + length-prefixed fields; ints big-endian."""
    buf = _length_prefixed(b"", PAYLOAD_DOMAIN)
    buf = _length_prefixed(buf, struct.pack(">I", envelope["version"]))
    for field in ("kid", "issuer", "robot_id", "simulation_id", "subject"):
        buf = _length_prefixed(buf, envelope[field].encode())
    if envelope.get("action") != "STOP":
        raise ValueError("ACTION_NOT_STOP")
    buf = _length_prefixed(buf, b"STOP")
    buf = _length_prefixed(buf, struct.pack(">Q", envelope["epoch"]))
    buf = _length_prefixed(buf, struct.pack(">Q", envelope["sequence"]))
    buf = _length_prefixed(buf, struct.pack(">q", envelope["issued_at_unix"]))
    buf = _length_prefixed(buf, struct.pack(">q", envelope["expires_at_unix"]))
    return _sha256_hex(buf)


def audit_record_hash(seq, prev_hash, payload_hash, decision_code):
    return _sha256_hex(AUDIT_DOMAIN + struct.pack(">q", seq)
                       + prev_hash.encode() + payload_hash.encode()
                       + decision_code.encode())


# --- Verifier ----------------------------------------------------------------
class _Verdict:
    def __init__(self):
        self.checks = []
        self.errors = []

    def report(self):
        passed = not self.errors
        return {
            "verdict": "PASS_LIMITED_CLAIMS" if passed else "REJECT",
            "format_version": 1,
            "checks": self.checks,
            "errors": self.errors,
            "supported_claims": SUPPORTED_CLAIMS if passed else [],
            "unsupported_claims": UNSUPPORTED_CLAIMS,
            "claim_boundary": "SIMULATION_ONLY_NO_PHYSICAL_NO_CERTIFICATION",
        }


def _load_json(files, name):
    try:
        value = json.loads(files[name])
    except Exception:
        return None
    return value


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_bytes(data):
    v = _Verdict()
    # Stage 1: container. SPEC: single portable ZIP; unsafe/duplicate reject.
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        names = archive.namelist()
        if len(names) != len(set(names)):
            v.errors.append("DUPLICATE_ENTRY")
        files = {}
        for name in names:
            if name.startswith("/") or ".." in name.split("/") or "\\" in name:
                v.errors.append("UNSAFE_PATH:%s" % name)
                continue
            files[name] = archive.read(name)
        v.checks.append("zip_container_read")
    except Exception:
        v.errors.append("BUNDLE_EMPTY_OR_NOT_ZIP")
        return v.report()

    # Stage 2: manifest and format/version + claim boundary.
    if "manifest.json" not in files:
        v.errors.append("MANIFEST_MISSING")
        return v.report()
    manifest_raw = files["manifest.json"]
    manifest = _load_json(files, "manifest.json")
    if not isinstance(manifest, dict):
        v.errors.append("MANIFEST_MALFORMED")
        return v.report()
    if manifest.get("format") != "quberon-evidence-bundle" or manifest.get("version") != 1:
        v.errors.append("FORMAT_VERSION_UNSUPPORTED")
    else:
        v.checks.append("format_version_1")
    if (not manifest.get("simulation_only")
            or manifest.get("physical_state_claim") != "NONE"
            or manifest.get("certification_claim") != "NONE"):
        v.errors.append("CLAIM_BOUNDARY_VIOLATION")
    else:
        v.checks.append("claim_boundary_simulation_only")

    # Stage 3: entry completeness (unlisted/missing) and SHA-256/size integrity.
    listed_entries = manifest.get("files")
    if not isinstance(listed_entries, list) or not all(
            isinstance(e, dict) for e in listed_entries):
        v.errors.append("MANIFEST_FILES_MALFORMED")
        listed_entries = []
    listed = [e.get("path") for e in listed_entries]
    if len(listed) != len(set(listed)):
        v.errors.append("MANIFEST_DUPLICATE_FILE")
    for required in BUNDLE_ENTRIES:
        if required not in listed:
            v.errors.append("MANIFEST_FILE_MISSING:%s" % required)
        if required not in files:
            v.errors.append("PAYLOAD_MISSING:%s" % required)
    for name in files:
        if name not in ("manifest.json", "attestation.json") and name not in listed:
            v.errors.append("UNLISTED_FILE:%s" % name)
    for entry in listed_entries:
        payload = files.get(entry.get("path"))
        if payload is not None:
            if len(payload) != entry.get("size"):
                v.errors.append("SIZE_MISMATCH:%s" % entry["path"])
            if _sha256_hex(payload) != entry.get("sha256"):
                v.errors.append("HASH_MISMATCH:%s" % entry["path"])
    if not any(e.startswith(("HASH_", "SIZE_")) for e in v.errors):
        v.checks.append("manifest_file_hashes_match")

    # Stage 4: environment completeness (SPEC: all non-empty strings;
    # git_commit 40 lowercase hex). Malformed types reject, never crash.
    environment = _load_json(files, "environment.json") if "environment.json" in files else None
    if not isinstance(environment, dict):
        if "environment.json" in files:
            v.errors.append("ENVIRONMENT_MALFORMED")
    else:
        for field in ENVIRONMENT_FIELDS:
            if not isinstance(environment.get(field), str) or not environment[field]:
                v.errors.append("ENV_FIELD_MISSING:%s" % field)
        commit = environment.get("git_commit")
        if not (isinstance(commit, str) and len(commit) == 40
                and all(c in "0123456789abcdef" for c in commit)):
            v.errors.append("ENV_GIT_COMMIT_MALFORMED")
        if not any(e.startswith("ENV_") for e in v.errors):
            v.checks.append("environment_manifest_complete")

    # Stage 5: secure-core envelope, decision, key (signatures, scope, kid).
    sc_names = ("secure-core/envelope.json", "secure-core/decision.json",
                "secure-core/verifying-key.json", "secure-core/audit.json")
    envelope: dict | None = None
    decision: dict | None = None
    key_doc: dict | None = None
    audit = None
    if all(name in files for name in sc_names):
        envelope = _load_json(files, sc_names[0])
        decision = _load_json(files, sc_names[1])
        key_doc = _load_json(files, sc_names[2])
        audit = _load_json(files, sc_names[3])
    bindings = manifest.get("bindings") if isinstance(manifest.get("bindings"), dict) else {}
    payload_hash = None
    if not all(isinstance(d, dict) for d in (envelope, decision, key_doc)):
        v.errors.append("SECURE_CORE_JSON_MALFORMED")
        envelope = decision = key_doc = None
    else:
        try:
            if not _is_int(envelope["version"]) or not all(
                    isinstance(envelope[f], str)
                    for f in ("kid", "issuer", "robot_id", "simulation_id", "subject")):
                raise ValueError("ENVELOPE_FIELD_MISSING")
            if not all(_is_int(envelope[f]) for f in
                       ("epoch", "sequence", "issued_at_unix", "expires_at_unix")):
                raise ValueError("ENVELOPE_FIELD_MISSING")
            payload_hash = canonical_payload_hash(envelope)
            if envelope.get("payload_hash") != payload_hash:
                v.errors.append("PAYLOAD_HASH_MISMATCH")
                payload_hash = envelope.get("payload_hash") if isinstance(
                    envelope.get("payload_hash"), str) else payload_hash
            else:
                v.checks.append("envelope_payload_hash_recomputed")
                try:
                    vk = bytes.fromhex(key_doc.get("verifying_key_hex", ""))
                    sig = bytes.fromhex(envelope.get("signature", ""))
                except Exception:
                    vk, sig = b"", b""
                if ed25519_verify(vk, SIGN_DOMAIN + bytes.fromhex(payload_hash), sig):
                    v.checks.append("envelope_signature_valid_for_bundled_key")
                else:
                    v.errors.append("SIGNATURE_INVALID")
                if bindings.get("envelope_payload_hash") != payload_hash:
                    v.errors.append("BINDING_PAYLOAD_HASH_MISMATCH")
        except ValueError as exc:
            v.errors.append(str(exc) if str(exc) in (
                "ACTION_NOT_STOP", "ENVELOPE_FIELD_MISSING")
                else "ENVELOPE_FIELD_MISSING")
            payload_hash = None
        except Exception:
            v.errors.append("ENVELOPE_FIELD_MISSING")
            payload_hash = None
        if (decision.get("outcome") != "ACCEPTED"
                or decision.get("code") != ACCEPTED_DECISION_CODE):
            v.errors.append("DECISION_NOT_ACCEPTED_SIMULATION_STOP")
        else:
            v.checks.append("decision_accepted_simulation_stop")
        if (decision.get("observed_state") != "UNKNOWN"
                or decision.get("physical_state_claim") != "NONE"):
            v.errors.append("DECISION_PHYSICAL_CLAIM_VIOLATION")
        if decision.get("sequence") != envelope.get("sequence"):
            v.errors.append("DECISION_SEQUENCE_MISMATCH")
        if (decision.get("robot_id") != envelope.get("robot_id")
                or decision.get("simulation_id") != envelope.get("simulation_id")):
            v.errors.append("DECISION_SCOPE_MISMATCH")
        if key_doc.get("kid") != envelope.get("kid") or manifest.get("kid") != envelope.get("kid"):
            v.errors.append("KID_MISMATCH")

    # Stage 6: audit hash chain (genesis, seq from 1 with no gaps) and the
    # audit/envelope binding. SPEC says "audit-tip/envelope binding"; the
    # reference observable behaviour binds the first record's payload_hash
    # (the tip record_hash is separately bound via bindings.audit_tip_hash).
    # Recorded as SD-6.
    if not isinstance(audit, list):
        if all(name in files for name in sc_names):
            v.errors.append("AUDIT_MALFORMED")
    elif not audit:
        v.errors.append("AUDIT_EMPTY")
    else:
        prev = GENESIS_PREV_HASH
        chain_ok = True
        for index, record in enumerate(audit):
            if not isinstance(record, dict):
                v.errors.append("AUDIT_CHAIN_INVALID")
                chain_ok = False
                break
            try:
                recomputed = audit_record_hash(
                    record["seq"], prev,
                    record.get("payload_hash", ""), record.get("decision_code", ""))
            except Exception:
                recomputed = None
            if (record.get("seq") != index + 1 or record.get("prev_hash") != prev
                    or recomputed != record.get("record_hash")):
                v.errors.append("AUDIT_CHAIN_INVALID")
                chain_ok = False
                break
            prev = record["record_hash"]
        if chain_ok:
            v.checks.append("audit_chain_hash_linked")
            if (bindings.get("audit_tip_hash") != prev
                    or bindings.get("audit_records") != len(audit)):
                v.errors.append("BINDING_AUDIT_TIP_MISMATCH")
            if envelope is not None and audit[0].get("payload_hash") != envelope.get("payload_hash"):
                v.errors.append("AUDIT_ENVELOPE_BINDING_MISMATCH")

    # Stage 7: replay determinism and STOP recorded in comparison.
    try:
        original_out = files["copper/original-task-outputs.bin"]
        replay_out = files["copper/replay-task-outputs.bin"]
        original_log = files["copper/original_0.copper"]
        replay_log = files["copper/replay_0.copper"]
        if original_out != replay_out:
            v.errors.append("REPLAY_TASK_OUTPUTS_MISMATCH")
        else:
            v.checks.append("copper_replay_task_outputs_byte_identical")
        if original_log != replay_log:
            v.errors.append("REPLAY_COPPER_LOGS_MISMATCH")
        else:
            v.checks.append("copper_logs_byte_identical")
        if (bindings.get("original_task_outputs_sha256") != _sha256_hex(original_out)
                or bindings.get("replay_task_outputs_sha256") != _sha256_hex(replay_out)):
            v.errors.append("BINDING_REPLAY_HASH_MISMATCH")
        comparison = files["copper/comparison.txt"].decode(errors="replace")
        if not all(token in comparison for token in COMPARISON_TOKENS):
            v.errors.append("STOP_NOT_RECORDED_IN_COMPARISON")
        else:
            v.checks.append("stop_recorded_in_copper_comparison")
    except KeyError:
        pass

    # Stage 8: bundle attestation over the exact manifest bytes.
    if "attestation.json" not in files:
        v.errors.append("ATTESTATION_MISSING")
    elif key_doc is not None:
        attestation = _load_json(files, "attestation.json")
        if not isinstance(attestation, dict):
            v.errors.append("ATTESTATION_MALFORMED")
        else:
            try:
                att_ok = (
                    attestation.get("manifest_sha256") == _sha256_hex(manifest_raw)
                    and ed25519_verify(
                        bytes.fromhex(key_doc.get("verifying_key_hex", "")),
                        ATTEST_DOMAIN + hashlib.sha256(manifest_raw).digest(),
                        bytes.fromhex(attestation.get("signature", ""))))
            except Exception:
                att_ok = False
            if att_ok:
                v.checks.append("bundle_attestation_valid_for_bundled_key")
            else:
                v.errors.append("ATTESTATION_INVALID")

    # Stage 9: claims lists must be exact (SPEC: inexact claims reject).
    claims = manifest.get("claims") if isinstance(manifest.get("claims"), dict) else {}
    if (claims.get("supported_if_valid") != SUPPORTED_CLAIMS
            or claims.get("unsupported") != UNSUPPORTED_CLAIMS):
        v.errors.append("CLAIMS_LIST_MISMATCH")
    else:
        v.checks.append("claims_lists_exact")
    return v.report()


def validate_path(path):
    with open(path, "rb") as handle:
        return validate_bytes(handle.read())


def main(argv):
    if len(argv) != 2:
        print(json.dumps({"verdict": "REJECT",
                          "errors": ["USAGE: independent_verify.py <bundle>"]}))
        return 2
    try:
        report = validate_path(argv[1])
    except OSError:
        print(json.dumps({"verdict": "REJECT", "format_version": 1,
                          "checks": [], "errors": ["BUNDLE_EMPTY_OR_NOT_ZIP"],
                          "supported_claims": [],
                          "unsupported_claims": UNSUPPORTED_CLAIMS}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["verdict"].startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
