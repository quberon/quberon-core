#!/usr/bin/env python3
"""Independent stdlib-only checker for quberon-evidence-bundle v1 vectors.

SIMULATION ONLY. No physical, safety, or certification claim is made or
implied by a PASS. A PASS means only internal consistency for the key
bundled inside the artifact (see rebuild-and-resign limitation vector).

This implementation is written from SPEC.md (crates/quberon-evidence-bundle)
only; it does not import the Rust crate or tools/quberon-verify.
Usage:
  python3 bundle_check.py --vectors vectors.json --bundle <fixture.qeb>
  python3 bundle_check.py <bundle.qeb> [--pinned-key-hex HEX] [--pinned-kid KID]
Exit 0 iff every consumed vector matches its expected verdict, else 1.
"""
import argparse, hashlib, json, struct, sys, zipfile
from pathlib import Path

HASH_DOMAIN = b"QUBERON-SECURE-CORE/PAYLOAD/v1\x00"
SIGN_DOMAIN = b"QUBERON-SECURE-CORE/SIGN/v1\x00"
AUDIT_DOMAIN = b"QUBERON-SECURE-CORE/AUDIT/v1\x00"
ATTEST_DOMAIN = b"QUBERON-EVIDENCE-BUNDLE/ATTEST/v1\x00"
GENESIS = "0" * 64
SUPPORTED = ["bundle_internal_integrity_sha256","audit_chain_hash_linked","envelope_signature_valid_for_bundled_key","secure_core_decision_accepted_simulation_stop","copper_replay_task_outputs_byte_identical","copper_logs_byte_identical","stop_recorded_in_copper_comparison"]
UNSUPPORTED = ["physical_stop_or_safety_rated_estop","certification_or_regulatory_compliance","signer_authority_beyond_bundled_self_asserted_key","production_key_custody_hsm_or_tpm","hardware_or_pi_execution","latency_or_real_time_behaviour","external_security_audit","authenticity_against_attacker_who_rebuilds_and_resigns_bundle_with_own_key"]
REQUIRED = ["copper/comparison.txt","copper/original-task-outputs.bin","copper/original_0.copper","copper/replay-task-outputs.bin","copper/replay_0.copper","environment.json","secure-core/audit.json","secure-core/decision.json","secure-core/envelope.json","secure-core/verifying-key.json"]
ENV_REQUIRED = ["arch","cargo_version","copper_config_sha256","copper_cu29_version","created_utc","git_commit","os","python_version","rustc_version","secure_core_cli_sha256","secure_core_source_sha256"]

# --- Ed25519 (RFC 8032 pure python, verify + sign for the limitation demo) ---
_q = 2**255 - 19; _l = 2**252 + 27742317777372353535851937790883648493
def _inv(x): return pow(x, _q-2, _q)
_d = -121665 * _inv(121666) % _q; _I = pow(2, (_q-1)//4, _q)
def _xrecover(y):
    xx = (y*y-1) * _inv(_d*y*y+1) % _q; x = pow(xx, (_q+3)//8, _q)
    if (x*x-xx) % _q != 0: x = (x*_I) % _q
    if x % 2 != 0: x = _q-x
    return x
_By = 4*_inv(5) % _q; _B = [_xrecover(_By), _By]
def _edwards(P, Q):
    (x1,y1),(x2,y2) = P,Q
    return [((x1*y2+x2*y1)*_inv(1+_d*x1*x2*y1*y2%_q))%_q, ((y1*y2+x1*x2)*_inv(1-_d*x1*x2*y1*y2%_q))%_q]
def _scalarmult(P, e):
    Q = [0,1]
    while e > 0:
        if e & 1: Q = _edwards(Q,P)
        P = _edwards(P,P); e >>= 1
    return Q
def _encodepoint(P):
    x,y = P; bits = y | ((x & 1) << 255); return bits.to_bytes(32, "little")
def _decodepoint(s):
    if len(s) != 32: raise ValueError("bad point")
    bits = int.from_bytes(s, "little"); y = bits & ((1<<255)-1); x = _xrecover(y)
    if (x & 1) != ((bits>>255)&1): x = _q-x
    return [x,y]
def ed25519_verify(pk, msg, sig):
    try:
        if len(pk)!=32 or len(sig)!=64: return False
        R = _decodepoint(sig[:32]); A = _decodepoint(pk); S = int.from_bytes(sig[32:], "little")
        if S >= _l: return False
        h = int.from_bytes(hashlib.sha512(sig[:32]+pk+msg).digest(), "little") % _l
        return _scalarmult(_B,S) == _edwards(R, _scalarmult(A,h))
    except Exception: return False
def ed25519_keypair_from_seed(seed32):
    if len(seed32)!=32: raise ValueError("seed must be 32 bytes")
    h = hashlib.sha512(seed32).digest()
    a = int.from_bytes(h[:32], "little"); a &= (1<<254)-8; a |= (1<<254)
    return _encodepoint(_scalarmult(_B,a)), a, h
def ed25519_sign(seed32, msg):
    pk, a, h = ed25519_keypair_from_seed(seed32)
    r = int.from_bytes(hashlib.sha512(h[32:]+msg).digest(), "little") % _l
    R = _encodepoint(_scalarmult(_B,r))
    S = (r + int.from_bytes(hashlib.sha512(R+pk+msg).digest(), "little") * a) % _l
    return R + S.to_bytes(32, "little")

# --- Canonical forms (SPEC.md) ---
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical_preimage(env):
    def put(buf,b): return buf + struct.pack(">Q", len(b)) + b
    buf = put(b"", HASH_DOMAIN); buf = put(buf, struct.pack(">I", env["version"]))
    for k in ("kid","issuer","robot_id","simulation_id","subject"): buf = put(buf, env[k].encode())
    if env.get("action") != "STOP": raise ValueError("ACTION_NOT_STOP")
    buf = put(buf, b"STOP"); buf = put(buf, struct.pack(">Q", env["epoch"])); buf = put(buf, struct.pack(">Q", env["sequence"]))
    buf = put(buf, struct.pack(">q", env["issued_at_unix"])); buf = put(buf, struct.pack(">q", env["expires_at_unix"]))
    return buf
def payload_hash(env): return sha(canonical_preimage(env))
def audit_hash(seq, prev, payload, code): return sha(AUDIT_DOMAIN + struct.pack(">q", seq) + prev.encode() + payload.encode() + code.encode())

def _report(checks, errors):
    ok = not errors
    return {"verdict":"PASS_LIMITED_CLAIMS" if ok else "REJECT","format_version":1,"checks":checks,"errors":errors,
            "supported_claims": SUPPORTED if ok else [],"unsupported_claims": UNSUPPORTED,
            "claim_boundary":"SIMULATION_ONLY_NO_PHYSICAL_NO_CERTIFICATION"}

def validate_bytes(data, pinned_key_hex=None, pinned_kid=None):
    """Validate raw .qeb bytes. pinned_* are an external trust anchor: when
    supplied, a self-consistent bundle signed by any other bundled key fails."""
    checks, errors = [], []
    try:
        import io
        z = zipfile.ZipFile(io.BytesIO(data)); names = z.namelist()
        if len(names) != len(set(names)): errors.append("DUPLICATE_ENTRY")
        files = {}
        for n in names:
            if n.startswith("/") or ".." in n.split("/") or "\\" in n: errors.append(f"UNSAFE_PATH:{n}"); continue
            files[n] = z.read(n)
        checks.append("zip_container_read")
    except Exception: return _report(checks, ["BUNDLE_EMPTY_OR_NOT_ZIP"])
    if "manifest.json" not in files: errors.append("MANIFEST_MISSING"); return _report(checks, errors)
    mb = files["manifest.json"]
    try: m = json.loads(mb)
    except Exception: errors.append("MANIFEST_MALFORMED"); return _report(checks, errors)
    if m.get("format") != "quberon-evidence-bundle" or m.get("version") != 1: errors.append("FORMAT_VERSION_UNSUPPORTED")
    else: checks.append("format_version_1")
    if not m.get("simulation_only") or m.get("physical_state_claim") != "NONE" or m.get("certification_claim") != "NONE": errors.append("CLAIM_BOUNDARY_VIOLATION")
    else: checks.append("claim_boundary_simulation_only")
    listed = [f.get("path") for f in m.get("files",[])]
    if len(listed) != len(set(listed)): errors.append("MANIFEST_DUPLICATE_FILE")
    for r in REQUIRED:
        if r not in listed: errors.append(f"MANIFEST_FILE_MISSING:{r}")
        if r not in files: errors.append(f"PAYLOAD_MISSING:{r}")
    for n in files:
        if n not in ("manifest.json","attestation.json") and n not in listed: errors.append(f"UNLISTED_FILE:{n}")
    for f in m.get("files",[]):
        d = files.get(f.get("path"))
        if d is not None:
            if len(d) != f.get("size"): errors.append(f"SIZE_MISMATCH:{f['path']}")
            if sha(d) != f.get("sha256"): errors.append(f"HASH_MISMATCH:{f['path']}")
    if not any(e.startswith(("HASH_","SIZE_")) for e in errors): checks.append("manifest_file_hashes_match")
    def getj(p):
        try: return json.loads(files[p])
        except Exception: return None
    envj = getj("environment.json") if "environment.json" in files else None
    if envj is None:
        if "environment.json" in files: errors.append("ENVIRONMENT_MALFORMED")
    else:
        for k in ENV_REQUIRED:
            if not isinstance(envj.get(k), str) or not envj[k]: errors.append(f"ENV_FIELD_MISSING:{k}")
        g = envj.get("git_commit","")
        # Rust requires lowercase-or-digit hex via is_ascii_hexdigit+len; Python verifier requires lower.
        # Cross-impl note in vectors.json: fixture uses lowercase, both accept it.
        if not (isinstance(g,str) and len(g)==40 and all(c in "0123456789abcdef" for c in g)): errors.append("ENV_GIT_COMMIT_MALFORMED")
        if not any(e.startswith("ENV_") for e in errors): checks.append("environment_manifest_complete")
    have_sc = all(k in files for k in ("secure-core/envelope.json","secure-core/decision.json","secure-core/verifying-key.json","secure-core/audit.json"))
    env, dec, keyj, audit = (getj("secure-core/envelope.json"), getj("secure-core/decision.json"), getj("secure-core/verifying-key.json"), getj("secure-core/audit.json")) if have_sc else (None,None,None,None)
    if env is None or dec is None or keyj is None: errors.append("SECURE_CORE_JSON_MALFORMED")
    else:
        if pinned_key_hex is not None and keyj.get("verifying_key_hex") != pinned_key_hex: errors.append("PINNED_KEY_MISMATCH")
        if pinned_kid is not None and keyj.get("kid") != pinned_kid: errors.append("PINNED_KID_MISMATCH")
        try:
            ph = payload_hash(env)
            if env.get("payload_hash") != ph: errors.append("PAYLOAD_HASH_MISMATCH")
            else:
                checks.append("envelope_payload_hash_recomputed")
                try: vk = bytes.fromhex(keyj.get("verifying_key_hex","")); sig = bytes.fromhex(env.get("signature",""))
                except Exception: vk, sig = b"", b""
                if ed25519_verify(vk, SIGN_DOMAIN+bytes.fromhex(ph), sig): checks.append("envelope_signature_valid_for_bundled_key")
                else: errors.append("SIGNATURE_INVALID")
                if m.get("bindings",{}).get("envelope_payload_hash") != ph: errors.append("BINDING_PAYLOAD_HASH_MISMATCH")
        except ValueError as e: errors.append(str(e) if str(e)=="ACTION_NOT_STOP" else "ENVELOPE_FIELD_MISSING")
        except Exception: errors.append("ENVELOPE_FIELD_MISSING")
        if dec.get("outcome") != "ACCEPTED" or dec.get("code") != "ACCEPTED_SIMULATION_STOP_AUTHORIZATION": errors.append("DECISION_NOT_ACCEPTED_SIMULATION_STOP")
        else: checks.append("decision_accepted_simulation_stop")
        if dec.get("observed_state") != "UNKNOWN" or dec.get("physical_state_claim") != "NONE": errors.append("DECISION_PHYSICAL_CLAIM_VIOLATION")
        if dec.get("sequence") != env.get("sequence"): errors.append("DECISION_SEQUENCE_MISMATCH")
        if dec.get("robot_id") != env.get("robot_id") or dec.get("simulation_id") != env.get("simulation_id"): errors.append("DECISION_SCOPE_MISMATCH")
        if keyj.get("kid") != env.get("kid") or m.get("kid") != env.get("kid"): errors.append("KID_MISMATCH")
    if audit is None:
        if have_sc: errors.append("AUDIT_MALFORMED")
    elif not audit: errors.append("AUDIT_EMPTY")
    else:
        prev, ok = GENESIS, True
        for idx, r in enumerate(audit):
            try: rh = audit_hash(r["seq"], prev, r.get("payload_hash",""), r.get("decision_code",""))
            except Exception: rh = None
            if r.get("seq") != idx+1 or r.get("prev_hash") != prev or rh != r.get("record_hash"): errors.append("AUDIT_CHAIN_INVALID"); ok=False; break
            prev = r["record_hash"]
        if ok:
            checks.append("audit_chain_hash_linked")
            if m.get("bindings",{}).get("audit_tip_hash") != prev or m.get("bindings",{}).get("audit_records") != len(audit): errors.append("BINDING_AUDIT_TIP_MISMATCH")
            if env and audit[0].get("payload_hash") != env.get("payload_hash"): errors.append("AUDIT_ENVELOPE_BINDING_MISMATCH")
    try:
        a,b,c,d = (files["copper/original-task-outputs.bin"], files["copper/replay-task-outputs.bin"], files["copper/original_0.copper"], files["copper/replay_0.copper"])
        if a != b: errors.append("REPLAY_TASK_OUTPUTS_MISMATCH")
        else: checks.append("copper_replay_task_outputs_byte_identical")
        if c != d: errors.append("REPLAY_COPPER_LOGS_MISMATCH")
        else: checks.append("copper_logs_byte_identical")
        if m.get("bindings",{}).get("original_task_outputs_sha256") != sha(a) or m.get("bindings",{}).get("replay_task_outputs_sha256") != sha(b): errors.append("BINDING_REPLAY_HASH_MISMATCH")
        t = files["copper/comparison.txt"].decode(errors="replace")
        if not ("command=STOP" in t and "authorized=true" in t and "byte_identical=true" in t): errors.append("STOP_NOT_RECORDED_IN_COMPARISON")
        else: checks.append("stop_recorded_in_copper_comparison")
    except KeyError: pass
    if "attestation.json" not in files: errors.append("ATTESTATION_MISSING")
    elif keyj is not None:
        att = getj("attestation.json")
        if att is None: errors.append("ATTESTATION_MALFORMED")
        else:
            try: ok = att.get("manifest_sha256")==sha(mb) and ed25519_verify(bytes.fromhex(keyj.get("verifying_key_hex","")), ATTEST_DOMAIN+hashlib.sha256(mb).digest(), bytes.fromhex(att.get("signature","")))
            except Exception: ok=False
            if ok: checks.append("bundle_attestation_valid_for_bundled_key")
            else: errors.append("ATTESTATION_INVALID")
    if m.get("claims",{}).get("supported_if_valid") != SUPPORTED or m.get("claims",{}).get("unsupported") != UNSUPPORTED: errors.append("CLAIMS_LIST_MISMATCH")
    else: checks.append("claims_lists_exact")
    return _report(checks, errors)

def validate(path, **kw): return validate_bytes(Path(path).read_bytes(), **kw)

# --- Tamper / rebuild helpers (deterministic, used by tests and CLI demo) ---
def _read_all(data):
    import io; z = zipfile.ZipFile(io.BytesIO(data)); return {n: z.read(n) for n in z.namelist()}
def _write_all(files):
    import io; buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in sorted(files):
            info = zipfile.ZipInfo(n, date_time=(1980,1,1,0,0,0)); info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o600<<16
            z.writestr(info, files[n])
    return buf.getvalue()
def _jdump(obj): return (json.dumps(obj, indent=2)+"\n").encode()
def apply_tamper(data, tamper_id):
    files = _read_all(data)
    if tamper_id == "flip_replay_task_output_byte":
        b = bytearray(files["copper/replay-task-outputs.bin"]); b[0] ^= 1; files["copper/replay-task-outputs.bin"] = bytes(b)
    elif tamper_id == "flip_original_copper_byte":
        b = bytearray(files["copper/original_0.copper"]); b[100] ^= 1; files["copper/original_0.copper"] = bytes(b)
    elif tamper_id == "mutate_envelope_sequence_without_resign":
        e = json.loads(files["secure-core/envelope.json"]); e["sequence"] = e["sequence"]+1; files["secure-core/envelope.json"] = _jdump(e)
    elif tamper_id == "flip_envelope_signature_char":
        e = json.loads(files["secure-core/envelope.json"]); s = e["signature"]; e["signature"] = ("0" if s[0]!="0" else "1")+s[1:]; files["secure-core/envelope.json"] = _jdump(e)
    elif tamper_id == "break_audit_record_hash":
        a = json.loads(files["secure-core/audit.json"]); a[0]["record_hash"] = "0"*64; files["secure-core/audit.json"] = _jdump(a)
    elif tamper_id == "remove_environment_field":
        e = json.loads(files["environment.json"]); e.pop("git_commit", None); files["environment.json"] = _jdump(e)
    elif tamper_id == "delete_payload_entry":
        files.pop("copper/replay-task-outputs.bin", None)
    elif tamper_id == "add_unlisted_entry":
        files["extra.txt"] = b"unlisted"
    elif tamper_id == "claim_boundary_physical":
        m = json.loads(files["manifest.json"]); m["physical_state_claim"] = "PHYSICAL_STOP_CONFIRMED"; files["manifest.json"] = _jdump(m)
    elif tamper_id == "unsupported_version":
        m = json.loads(files["manifest.json"]); m["version"] = 99; files["manifest.json"] = _jdump(m)
    elif tamper_id == "garbage_not_zip":
        return b"not a zip at all"
    else: raise ValueError(f"unknown tamper {tamper_id}")
    return _write_all(files)

def rebuild_and_resign(data, seed=b"\x01"*32):
    """Attacker rebuild: flip replay, fix every hash/binding, replace bundled
    key, re-sign envelope+attestation. Internally consistent by construction.
    This MUST still be described as unauthenticated without a pinned key."""
    files = _read_all(data)
    pk, _, _ = ed25519_keypair_from_seed(hashlib.sha256(b"attacker-demo-seed:"+seed).digest() if seed!=b"\x01"*32 else hashlib.sha256(b"attacker-demo-seed").digest())
    seed32 = hashlib.sha256(b"attacker-demo-seed").digest(); pk,_,_ = ed25519_keypair_from_seed(seed32)
    b = bytearray(files["copper/replay-task-outputs.bin"]); b[0] ^= 1; files["copper/replay-task-outputs.bin"] = bytes(b)
    keyj = json.loads(files["secure-core/verifying-key.json"]); keyj["verifying_key_hex"] = pk.hex(); files["secure-core/verifying-key.json"] = _jdump(keyj)
    env = json.loads(files["secure-core/envelope.json"]); ph = payload_hash(env)
    env["signature"] = ed25519_sign(seed32, SIGN_DOMAIN+bytes.fromhex(ph)).hex(); files["secure-core/envelope.json"] = _jdump(env)
    m = json.loads(files["manifest.json"])
    for entry in m["files"]:
        if entry["path"] in files: entry["sha256"], entry["size"] = sha(files[entry["path"]]), len(files[entry["path"]])
    m["bindings"]["replay_task_outputs_sha256"] = sha(files["copper/replay-task-outputs.bin"])
    # original/replay now differ, so a fully consistent attacker would also need
    # identical replay: copy original over replay to satisfy byte-identity check.
    files["copper/replay-task-outputs.bin"] = files["copper/original-task-outputs.bin"]
    m["bindings"]["replay_task_outputs_sha256"] = sha(files["copper/replay-task-outputs.bin"])
    for entry in m["files"]:
        if entry["path"] in files: entry["sha256"], entry["size"] = sha(files[entry["path"]]), len(files[entry["path"]])
    mb = _jdump(m); files["manifest.json"] = mb
    att = json.loads(files["attestation.json"]); att["manifest_sha256"] = sha(mb); att["signature"] = ed25519_sign(seed32, ATTEST_DOMAIN+hashlib.sha256(mb).digest()).hex(); files["attestation.json"] = _jdump(att)
    return _write_all(files)

def check_vectors(vectors, bundle_path):
    data = Path(bundle_path).read_bytes(); results = []
    files = _read_all(data); manifest = json.loads(files["manifest.json"]); env = json.loads(files["secure-core/envelope.json"])
    audit = json.loads(files["secure-core/audit.json"]); keyj = json.loads(files["secure-core/verifying-key.json"])
    base = validate_bytes(data)
    for v in vectors["vectors"]:
        cat, exp = v["category"], v["expected"]; got_errors, ok = [], True
        if cat == "canonical_bytes":
            pre = canonical_preimage(env)
            ok = pre.hex()==v["canonical_preimage_hex"] and payload_hash(env)==v["payload_hash"] and sha(ATTEST_DOMAIN+hashlib.sha256(files["manifest.json"]).digest())==v["attestation_message_sha256"]
        elif cat == "hash_chain":
            prev = GENESIS
            for r in v["synthetic_chain"]:
                if audit_hash(r["seq"], prev, r["payload_hash"], r["decision_code"]) != r["record_hash"]: ok=False; break
                prev = r["record_hash"]
            ok = ok and prev==v["synthetic_tip"] and audit_hash(audit[0]["seq"], audit[0]["prev_hash"], audit[0]["payload_hash"], audit[0]["decision_code"])==audit[0]["record_hash"]==v["fixture_audit_tip"]
        elif cat == "signature":
            msg = SIGN_DOMAIN+bytes.fromhex(payload_hash(env))
            ok = ed25519_verify(bytes.fromhex(keyj["verifying_key_hex"]), msg, bytes.fromhex(env["signature"])) == v["valid_signature_verifies"]
            ok = ok and not ed25519_verify(bytes.fromhex(keyj["verifying_key_hex"]), b"WRONG-DOMAIN\x00"+bytes.fromhex(payload_hash(env)), bytes.fromhex(env["signature"]))
            bad = bytearray(bytes.fromhex(env["signature"])); bad[0]^=1
            ok = ok and not ed25519_verify(bytes.fromhex(keyj["verifying_key_hex"]), msg, bytes(bad))
        elif cat == "replay_binding":
            ok = sha(files["copper/original-task-outputs.bin"])==v["original_task_outputs_sha256"]==manifest["bindings"]["original_task_outputs_sha256"]
            ok = ok and sha(files["copper/replay-task-outputs.bin"])==v["replay_task_outputs_sha256"]==manifest["bindings"]["replay_task_outputs_sha256"]
            ok = ok and sha(files["copper/original_0.copper"])==v["original_copper_sha256"]==manifest["bindings"]["original_copper_sha256"] and sha(files["copper/replay_0.copper"])==v["replay_copper_sha256"]==manifest["bindings"]["replay_copper_sha256"]
            ok = ok and files["copper/original-task-outputs.bin"]==files["copper/replay-task-outputs.bin"] and files["copper/original_0.copper"]==files["copper/replay_0.copper"]
        elif cat == "manifest_completeness":
            ok = sorted(REQUIRED)==sorted(v["required_files"]) and ENV_REQUIRED==v["env_required_fields"]
            ok = ok and all(k in json.loads(files["environment.json"]) for k in ENV_REQUIRED)
            ok = ok and sorted(f["path"] for f in manifest["files"])==sorted(REQUIRED) and base["verdict"]==exp["verdict"]
        elif cat == "tamper_classes":
            rep = validate_bytes(apply_tamper(data, v["tamper_id"])); got_errors = rep["errors"]
            ok = rep["verdict"]==exp["verdict"] and all(any(e==x or e.startswith(x) for e in got_errors) for x in exp["errors_contains"])
        elif cat == "rebuild_and_resign_limitation":
            rebuilt = rebuild_and_resign(data); internal = validate_bytes(rebuilt); pinned = validate_bytes(rebuilt, pinned_key_hex=keyj["verifying_key_hex"], pinned_kid=keyj["kid"])
            got_errors = pinned["errors"]
            ok = internal["verdict"]==exp["internal_verdict_without_trust_anchor"] and pinned["verdict"]==exp["pinned_verdict"] and "PINNED_KEY_MISMATCH" in pinned["errors"] and exp["limitation"] is True
        else: ok=False; got_errors=[f"UNKNOWN_CATEGORY:{cat}"]
        results.append({"id":v["id"],"category":cat,"ok":bool(ok),"expected_verdict":exp.get("verdict", exp.get("pinned_verdict","")),"errors_seen":got_errors})
    return {"bundle":str(bundle_path),"base_verdict":base["verdict"],"all_ok":all(r["ok"] for r in results),"results":results,"unsupported_claims":UNSUPPORTED}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("bundle", nargs="?"); ap.add_argument("--vectors"); ap.add_argument("--pinned-key-hex"); ap.add_argument("--pinned-kid")
    a = ap.parse_args()
    if a.vectors:
        if not a.bundle: ap.error("--vectors requires a bundle argument")
        out = check_vectors(json.loads(Path(a.vectors).read_text()), a.bundle); print(json.dumps(out, indent=2)); sys.exit(0 if out["all_ok"] else 1)
    if not a.bundle: ap.error("bundle required")
    r = validate(a.bundle, pinned_key_hex=a.pinned_key_hex, pinned_kid=a.pinned_kid); print(json.dumps(r, indent=2)); sys.exit(0 if r["verdict"].startswith("PASS") else 1)
