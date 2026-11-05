#!/usr/bin/env python3
"""Regenerate vectors.json deterministically from the committed N3 fixture.
Stdlib only. Run: python3 generate_vectors.py"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bundle_check as bc
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/"tools/quberon-verify/tests/fixtures/simulated-stop.qeb"
def main():
    data = FIXTURE.read_bytes(); files = bc._read_all(data)
    manifest = json.loads(files["manifest.json"]); env = json.loads(files["secure-core/envelope.json"]); audit = json.loads(files["secure-core/audit.json"])
    pre = bc.canonical_preimage(env)
    # synthetic 3-record chain (invented payloads, real formula)
    chain, prev = [], bc.GENESIS
    for seq, payload in enumerate(["aa"*32, "bb"*32, "cc"*32], 1):
        rh = bc.audit_hash(seq, prev, payload, "ACCEPTED_SIMULATION_STOP_AUTHORIZATION")
        chain.append({"seq":seq,"payload_hash":payload,"decision_code":"ACCEPTED_SIMULATION_STOP_AUTHORIZATION","prev_hash":prev,"record_hash":rh}); prev = rh
    tampers = [
        ("flip_replay_task_output_byte", ["HASH_MISMATCH:copper/replay-task-outputs.bin","REPLAY_TASK_OUTPUTS_MISMATCH","BINDING_REPLAY_HASH_MISMATCH"]),
        ("flip_original_copper_byte", ["HASH_MISMATCH:copper/original_0.copper","REPLAY_COPPER_LOGS_MISMATCH"]),
        ("mutate_envelope_sequence_without_resign", ["PAYLOAD_HASH_MISMATCH"]),
        ("flip_envelope_signature_char", ["SIGNATURE_INVALID"]),
        ("break_audit_record_hash", ["AUDIT_CHAIN_INVALID"]),
        ("remove_environment_field", ["ENV_FIELD_MISSING:git_commit"]),
        ("delete_payload_entry", ["PAYLOAD_MISSING:copper/replay-task-outputs.bin"]),
        ("add_unlisted_entry", ["UNLISTED_FILE:extra.txt"]),
        ("claim_boundary_physical", ["CLAIM_BOUNDARY_VIOLATION"]),
        ("unsupported_version", ["FORMAT_VERSION_UNSUPPORTED"]),
        ("garbage_not_zip", ["BUNDLE_EMPTY_OR_NOT_ZIP"]),
    ]
    vectors = [
        {"id":"EB-CANON-01","category":"canonical_bytes","description":"Envelope canonical preimage (domain,length-prefixed fields,BE ints) and payload_hash from fixture envelope. Exact bytes, not JSON re-serialisation.","canonical_preimage_hex":pre.hex(),"payload_hash":bc.payload_hash(env),"attestation_message_sha256":bc.sha(bc.ATTEST_DOMAIN+hashlib.sha256(files["manifest.json"]).digest()),"expected":{"verdict":"PASS_LIMITED_CLAIMS"}},
        {"id":"EB-CHAIN-01","category":"hash_chain","description":"Synthetic 3-record audit chain via SPEC audit formula plus fixture audit tip binding.","synthetic_chain":chain,"synthetic_tip":prev,"fixture_audit_tip":audit[-1]["record_hash"],"expected":{"verdict":"PASS_LIMITED_CLAIMS"}},
        {"id":"EB-SIG-01","category":"signature","description":"Fixture Ed25519 envelope signature verifies for bundled key; wrong-domain and bit-flipped signature must not.","valid_signature_verifies":True,"expected":{"verdict":"PASS_LIMITED_CLAIMS"}},
        {"id":"EB-REPLAY-01","category":"replay_binding","description":"Original/replay task-output and Copper-log hashes equal manifest bindings and bytes are identical.","original_task_outputs_sha256":bc.sha(files["copper/original-task-outputs.bin"]),"replay_task_outputs_sha256":bc.sha(files["copper/replay-task-outputs.bin"]),"original_copper_sha256":bc.sha(files["copper/original_0.copper"]),"replay_copper_sha256":bc.sha(files["copper/replay_0.copper"]),"expected":{"verdict":"PASS_LIMITED_CLAIMS"}},
        {"id":"EB-MANIFEST-01","category":"manifest_completeness","description":"Manifest lists exactly the required payload files; environment contains every required non-empty field.","required_files":bc.REQUIRED,"env_required_fields":bc.ENV_REQUIRED,"manifest_file_count":len(manifest["files"]),"expected":{"verdict":"PASS_LIMITED_CLAIMS"}},
    ] + [{"id":f"EB-TAMPER-{i:02d}","category":"tamper_classes","description":f"Tamper class {tid}: mutated fixture must be rejected with the listed error code(s).","tamper_id":tid,"expected":{"verdict":"REJECT","errors_contains":errs}} for i,(tid,errs) in enumerate(tampers,1)] + [
        {"id":"EB-RESIGN-01","category":"rebuild_and_resign_limitation","description":"LIMITATION, not a pass claim: an attacker who rebuilds, fixes all bindings and re-signs with their own bundled key produces an internally consistent bundle. Without an externally pinned key/kid it verifies as PASS_LIMITED_CLAIMS; with the original key pinned it is REJECT (PINNED_KEY_MISMATCH). Bundled-key verification alone proves no signer authority.","expected":{"internal_verdict_without_trust_anchor":"PASS_LIMITED_CLAIMS","pinned_verdict":"REJECT","errors_contains":["PINNED_KEY_MISMATCH"],"limitation":True}},
    ]
    out = {"format":"quberon-evidence-bundle-conformance-vectors","version":1,"fixture":"tools/quberon-verify/tests/fixtures/simulated-stop.qeb","fixture_sha256":hashlib.sha256(data).hexdigest(),"claim_boundary":"SIMULATION_ONLY_NO_PHYSICAL_NO_CERTIFICATION","unsupported_claims":bc.UNSUPPORTED,"vectors":vectors}
    (Path(__file__).parent/"vectors.json").write_text(json.dumps(out, indent=2)+"\n")
    print(f"wrote vectors.json: {len(vectors)} vectors fixture_sha256={out['fixture_sha256']}")
if __name__ == "__main__": main()
