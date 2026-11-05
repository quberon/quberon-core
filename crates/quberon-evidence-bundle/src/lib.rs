//! quberon-evidence-bundle v1 — SIMULATION ONLY. NO PHYSICAL CONTROL.
//! NOT A SAFETY-RATED E-STOP. NO CERTIFICATION CLAIM.
//!
//! A single portable artifact (deterministic ZIP, method=deflate) tying:
//!   * actual Copper record/replay logs + task-output bytes,
//!   * a secure-core v1 Ed25519-signed STOP envelope + ACCEPTED decision,
//!   * the secure-core hash-chained audit records that decision produced,
//!   * a complete environment manifest.
//!
//! Canonical payload / audit formulas mirror docs/SECURE-CORE.md and
//! crates/quberon-secure-core v1 exactly (domains below); this crate does
//! not import that crate (root-workspace isolation).
#![forbid(unsafe_code)]

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::io::{Read, Write};

pub const FORMAT: &str = "quberon-evidence-bundle";
pub const FORMAT_VERSION: u32 = 1;
pub const HASH_DOMAIN: &[u8] = b"QUBERON-SECURE-CORE/PAYLOAD/v1\0";
pub const SIGN_DOMAIN: &[u8] = b"QUBERON-SECURE-CORE/SIGN/v1\0";
pub const AUDIT_DOMAIN: &[u8] = b"QUBERON-SECURE-CORE/AUDIT/v1\0";
pub const ATTEST_DOMAIN: &[u8] = b"QUBERON-EVIDENCE-BUNDLE/ATTEST/v1\0";
pub const GENESIS: &str = "0000000000000000000000000000000000000000000000000000000000000000";
pub const SUPPORTED: &[&str] = &[
    "bundle_internal_integrity_sha256",
    "audit_chain_hash_linked",
    "envelope_signature_valid_for_bundled_key",
    "secure_core_decision_accepted_simulation_stop",
    "copper_replay_task_outputs_byte_identical",
    "copper_logs_byte_identical",
    "stop_recorded_in_copper_comparison",
];
pub const UNSUPPORTED: &[&str] = &[
    "physical_stop_or_safety_rated_estop",
    "certification_or_regulatory_compliance",
    "signer_authority_beyond_bundled_self_asserted_key",
    "production_key_custody_hsm_or_tpm",
    "hardware_or_pi_execution",
    "latency_or_real_time_behaviour",
    "external_security_audit",
    "authenticity_against_attacker_who_rebuilds_and_resigns_bundle_with_own_key",
];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct FileEntry {
    pub path: String,
    pub sha256: String,
    pub size: u64,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Bindings {
    pub envelope_payload_hash: String,
    pub audit_tip_hash: String,
    pub audit_records: u64,
    pub decision_code: String,
    pub sequence: u64,
    pub original_task_outputs_sha256: String,
    pub replay_task_outputs_sha256: String,
    pub original_copper_sha256: String,
    pub replay_copper_sha256: String,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Claims {
    pub supported_if_valid: Vec<String>,
    pub unsupported: Vec<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub format: String,
    pub version: u32,
    pub bundle_id: String,
    pub simulation_only: bool,
    pub physical_state_claim: String,
    pub certification_claim: String,
    pub kid: String,
    pub issuer: String,
    pub robot_id: String,
    pub simulation_id: String,
    pub files: Vec<FileEntry>,
    pub bindings: Bindings,
    pub claims: Claims,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Attestation {
    pub kid: String,
    pub algorithm: String,
    pub domain: String,
    pub manifest_sha256: String,
    pub signature: String,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct AuditRecord {
    pub seq: u64,
    pub payload_hash: String,
    pub decision_code: String,
    pub prev_hash: String,
    pub record_hash: String,
}

pub fn sha256_hex(b: &[u8]) -> String {
    hex::encode(Sha256::digest(b))
}

fn put(buf: &mut Vec<u8>, bytes: &[u8]) {
    buf.extend_from_slice(&(bytes.len() as u64).to_be_bytes());
    buf.extend_from_slice(bytes);
}

/// Mirror of secure-core canonical_payload (v1).
pub fn payload_hash(env: &serde_json::Value) -> Result<String, String> {
    let s = |k: &str| {
        env.get(k)
            .and_then(|v| v.as_str())
            .ok_or("ENVELOPE_FIELD_MISSING")
            .map(|x| x.to_string())
    };
    let u = |k: &str| {
        env.get(k)
            .and_then(|v| v.as_u64())
            .ok_or("ENVELOPE_FIELD_MISSING")
    };
    let i = |k: &str| {
        env.get(k)
            .and_then(|v| v.as_i64())
            .ok_or("ENVELOPE_FIELD_MISSING")
    };
    let mut b = Vec::new();
    put(&mut b, HASH_DOMAIN);
    put(&mut b, &(u("version")? as u32).to_be_bytes());
    for k in ["kid", "issuer", "robot_id", "simulation_id", "subject"] {
        put(&mut b, s(k)?.as_bytes());
    }
    if s("action")? != "STOP" {
        return Err("ACTION_NOT_STOP".into());
    }
    put(&mut b, b"STOP");
    put(&mut b, &u("epoch")?.to_be_bytes());
    put(&mut b, &u("sequence")?.to_be_bytes());
    put(&mut b, &i("issued_at_unix")?.to_be_bytes());
    put(&mut b, &i("expires_at_unix")?.to_be_bytes());
    Ok(sha256_hex(&b))
}
pub fn audit_hash(seq: u64, prev: &str, payload: &str, code: &str) -> String {
    let mut h = Sha256::new();
    h.update(AUDIT_DOMAIN);
    h.update((seq as i64).to_be_bytes());
    h.update(prev.as_bytes());
    h.update(payload.as_bytes());
    h.update(code.as_bytes());
    hex::encode(h.finalize())
}
pub fn verify_ed25519(pub_hex: &str, msg: &[u8], sig_hex: &str) -> bool {
    let (Ok(pk), Ok(sb)) = (hex::decode(pub_hex), hex::decode(sig_hex)) else {
        return false;
    };
    let (Ok(pkb), Ok(sigb)) = (
        <[u8; 32]>::try_from(pk.as_slice()),
        <[u8; 64]>::try_from(sb.as_slice()),
    ) else {
        return false;
    };
    let Ok(vk) = VerifyingKey::from_bytes(&pkb) else {
        return false;
    };
    vk.verify(msg, &Signature::from_bytes(&sigb)).is_ok()
}
pub fn sign_attestation(sk: &SigningKey, kid: &str, manifest_bytes: &[u8]) -> Attestation {
    let digest = Sha256::digest(manifest_bytes);
    let mut msg = ATTEST_DOMAIN.to_vec();
    msg.extend_from_slice(&digest);
    Attestation {
        kid: kid.into(),
        algorithm: "Ed25519".into(),
        domain: "QUBERON-EVIDENCE-BUNDLE/ATTEST/v1".into(),
        manifest_sha256: hex::encode(digest),
        signature: hex::encode(sk.sign(&msg).to_bytes()),
    }
}

// ---- deterministic ZIP (deflate, fixed 1980 timestamp, sorted names) ----
fn crc32(data: &[u8]) -> u32 {
    let mut table = [0u32; 256];
    for (i, e) in table.iter_mut().enumerate() {
        let mut c = i as u32;
        for _ in 0..8 {
            c = if c & 1 != 0 {
                0xEDB88320 ^ (c >> 1)
            } else {
                c >> 1
            };
        }
        *e = c;
    }
    let mut c = 0xFFFFFFFFu32;
    for &b in data {
        c = table[((c ^ b as u32) & 0xFF) as usize] ^ (c >> 8);
    }
    c ^ 0xFFFFFFFF
}
pub fn write_bundle(files: &BTreeMap<String, Vec<u8>>) -> Result<Vec<u8>, String> {
    let mut out = Vec::new();
    let mut central = Vec::new();
    for (name, data) in files {
        if name.is_empty() || name.starts_with('/') || name.contains("..") || name.contains('\\') {
            return Err("UNSAFE_PATH".into());
        }
        let mut enc = flate2::write::DeflateEncoder::new(Vec::new(), flate2::Compression::new(9));
        enc.write_all(data).map_err(|_| "DEFLATE")?;
        let comp = enc.finish().map_err(|_| "DEFLATE")?;
        let offset = out.len() as u32;
        let crc = crc32(data);
        let mut h = Vec::new();
        h.extend_from_slice(&0x04034b50u32.to_le_bytes());
        h.extend_from_slice(&20u16.to_le_bytes());
        h.extend_from_slice(&0x0800u16.to_le_bytes());
        h.extend_from_slice(&8u16.to_le_bytes());
        h.extend_from_slice(&0u16.to_le_bytes());
        h.extend_from_slice(&0x21u16.to_le_bytes()); // 1980-01-01
        h.extend_from_slice(&crc.to_le_bytes());
        h.extend_from_slice(&(comp.len() as u32).to_le_bytes());
        h.extend_from_slice(&(data.len() as u32).to_le_bytes());
        h.extend_from_slice(&(name.len() as u16).to_le_bytes());
        h.extend_from_slice(&0u16.to_le_bytes());
        h.extend_from_slice(name.as_bytes());
        out.extend_from_slice(&h);
        out.extend_from_slice(&comp);
        let mut c = Vec::new();
        c.extend_from_slice(&0x02014b50u32.to_le_bytes());
        c.extend_from_slice(&20u16.to_le_bytes());
        c.extend_from_slice(&20u16.to_le_bytes());
        c.extend_from_slice(&0x0800u16.to_le_bytes());
        c.extend_from_slice(&8u16.to_le_bytes());
        c.extend_from_slice(&0u16.to_le_bytes());
        c.extend_from_slice(&0x21u16.to_le_bytes());
        c.extend_from_slice(&crc.to_le_bytes());
        c.extend_from_slice(&(comp.len() as u32).to_le_bytes());
        c.extend_from_slice(&(data.len() as u32).to_le_bytes());
        c.extend_from_slice(&(name.len() as u16).to_le_bytes());
        for _ in 0..4 {
            c.extend_from_slice(&0u16.to_le_bytes());
        }
        c.extend_from_slice(&0u32.to_le_bytes());
        c.extend_from_slice(&offset.to_le_bytes());
        c.extend_from_slice(name.as_bytes());
        central.extend_from_slice(&c);
    }
    let cd_off = out.len() as u32;
    out.extend_from_slice(&central);
    out.extend_from_slice(&0x06054b50u32.to_le_bytes());
    out.extend_from_slice(&0u16.to_le_bytes());
    out.extend_from_slice(&0u16.to_le_bytes());
    out.extend_from_slice(&(files.len() as u16).to_le_bytes());
    out.extend_from_slice(&(files.len() as u16).to_le_bytes());
    out.extend_from_slice(&(central.len() as u32).to_le_bytes());
    out.extend_from_slice(&cd_off.to_le_bytes());
    out.extend_from_slice(&0u16.to_le_bytes());
    Ok(out)
}
pub fn read_bundle(bytes: &[u8]) -> Result<BTreeMap<String, Vec<u8>>, String> {
    // Parse local headers sequentially (our writer + python zipfile both emit them first).
    let mut map = BTreeMap::new();
    let mut p = 0usize;
    let rd32 = |b: &[u8], o: usize| u32::from_le_bytes(b[o..o + 4].try_into().unwrap());
    let rd16 = |b: &[u8], o: usize| u16::from_le_bytes(b[o..o + 2].try_into().unwrap());
    while p + 30 <= bytes.len() && rd32(bytes, p) == 0x04034b50 {
        let method = rd16(bytes, p + 8);
        let crc = rd32(bytes, p + 14);
        let csize = rd32(bytes, p + 18) as usize;
        let usize_ = rd32(bytes, p + 22) as usize;
        let nlen = rd16(bytes, p + 26) as usize;
        let elen = rd16(bytes, p + 28) as usize;
        let name =
            String::from_utf8(bytes[p + 30..p + 30 + nlen].to_vec()).map_err(|_| "BAD_NAME")?;
        if name.is_empty() || name.starts_with('/') || name.contains("..") || name.contains('\\') {
            return Err("UNSAFE_PATH".into());
        }
        if map.contains_key(&name) {
            return Err("DUPLICATE_ENTRY".into());
        }
        let start = p + 30 + nlen + elen;
        let comp = &bytes[start..start + csize];
        let data = match method {
            0 => comp.to_vec(),
            8 => {
                let mut d = flate2::read::DeflateDecoder::new(comp);
                let mut v = Vec::new();
                d.read_to_end(&mut v).map_err(|_| "INFLATE")?;
                v
            }
            _ => return Err("UNSUPPORTED_COMPRESSION".into()),
        };
        if data.len() != usize_ || crc32(&data) != crc {
            return Err("CRC_MISMATCH".into());
        }
        map.insert(name, data);
        p = start + csize;
    }
    if map.is_empty() {
        return Err("BUNDLE_EMPTY_OR_NOT_ZIP".into());
    }
    Ok(map)
}

// ---- validation ----
#[derive(Debug, Serialize)]
pub struct Report {
    pub verdict: String,
    pub format_version: u32,
    pub checks: Vec<String>,
    pub errors: Vec<String>,
    pub supported_claims: Vec<String>,
    pub unsupported_claims: Vec<String>,
}

const REQUIRED_FILES: &[&str] = &[
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
];
const ENV_REQUIRED: &[&str] = &[
    "arch",
    "cargo_version",
    "copper_config_sha256",
    "copper_cu29_version",
    "created_utc",
    "git_commit",
    "os",
    "python_version",
    "rustc_version",
    "secure_core_cli_sha256",
    "secure_core_source_sha256",
];

pub fn validate(bytes: &[u8]) -> Report {
    let mut checks = vec![];
    let mut errors: Vec<String> = vec![];
    let fail = |c: &str, e: &mut Vec<String>| e.push(c.to_string());
    let files = match read_bundle(bytes) {
        Ok(f) => f,
        Err(e) => {
            return Report {
                verdict: "REJECT".into(),
                format_version: 0,
                checks,
                errors: vec![e],
                supported_claims: vec![],
                unsupported_claims: UNSUPPORTED.iter().map(|s| s.to_string()).collect(),
            }
        }
    };
    checks.push("zip_container_read".into());
    let Some(manifest_bytes) = files.get("manifest.json") else {
        fail("MANIFEST_MISSING", &mut errors);
        return rep(checks, errors);
    };
    let manifest: Manifest = match serde_json::from_slice(manifest_bytes) {
        Ok(m) => m,
        Err(_) => {
            fail("MANIFEST_MALFORMED", &mut errors);
            return rep(checks, errors);
        }
    };
    if manifest.format != FORMAT || manifest.version != FORMAT_VERSION {
        fail("FORMAT_VERSION_UNSUPPORTED", &mut errors);
    } else {
        checks.push("format_version_1".into());
    }
    if !manifest.simulation_only
        || manifest.physical_state_claim != "NONE"
        || manifest.certification_claim != "NONE"
    {
        fail("CLAIM_BOUNDARY_VIOLATION", &mut errors);
    } else {
        checks.push("claim_boundary_simulation_only".into());
    }
    // file inventory / hashes
    let listed: Vec<String> = manifest.files.iter().map(|f| f.path.clone()).collect();
    for r in REQUIRED_FILES {
        if !listed.contains(&r.to_string()) {
            fail(&format!("MANIFEST_FILE_MISSING:{r}"), &mut errors);
        }
        if !files.contains_key(*r) {
            fail(&format!("PAYLOAD_MISSING:{r}"), &mut errors);
        }
    }
    for name in files.keys() {
        if name != "manifest.json" && name != "attestation.json" && !listed.contains(name) {
            fail(&format!("UNLISTED_FILE:{name}"), &mut errors);
        }
    }
    let mut by_path = BTreeMap::new();
    for f in &manifest.files {
        if by_path.insert(f.path.clone(), f).is_some() {
            fail("MANIFEST_DUPLICATE_FILE", &mut errors);
        }
        match files.get(&f.path) {
            None => {}
            Some(d) => {
                if d.len() as u64 != f.size {
                    fail(&format!("SIZE_MISMATCH:{}", f.path), &mut errors);
                }
                if sha256_hex(d) != f.sha256 {
                    fail(&format!("HASH_MISMATCH:{}", f.path), &mut errors);
                }
            }
        }
    }
    if errors.is_empty() {
        checks.push("manifest_file_hashes_match".into());
    }
    // environment completeness
    if let Some(envb) = files.get("environment.json") {
        if let Ok(env) = serde_json::from_slice::<serde_json::Value>(envb) {
            for k in ENV_REQUIRED {
                if env
                    .get(*k)
                    .and_then(|v| v.as_str())
                    .filter(|s| !s.is_empty())
                    .is_none()
                {
                    fail(&format!("ENV_FIELD_MISSING:{k}"), &mut errors);
                }
            }
            if let Some(g) = env.get("git_commit").and_then(|v| v.as_str()) {
                if !(g.len() == 40 && g.bytes().all(|c| c.is_ascii_hexdigit())) {
                    fail("ENV_GIT_COMMIT_MALFORMED", &mut errors);
                }
            }
            if errors.iter().all(|e| !e.starts_with("ENV_")) {
                checks.push("environment_manifest_complete".into());
            }
        } else {
            fail("ENVIRONMENT_MALFORMED", &mut errors);
        }
    }
    // envelope / decision / key
    let getj = |p: &str| {
        files
            .get(p)
            .and_then(|b| serde_json::from_slice::<serde_json::Value>(b).ok())
    };
    let (env, dec, keyj, auditj) = (
        getj("secure-core/envelope.json"),
        getj("secure-core/decision.json"),
        getj("secure-core/verifying-key.json"),
        getj("secure-core/audit.json"),
    );
    if let (Some(env), Some(dec), Some(keyj)) = (&env, &dec, &keyj) {
        match payload_hash(env) {
            Ok(ph) => {
                if env.get("payload_hash").and_then(|v| v.as_str()) != Some(ph.as_str()) {
                    fail("PAYLOAD_HASH_MISMATCH", &mut errors);
                } else {
                    checks.push("envelope_payload_hash_recomputed".into());
                    let mut msg = SIGN_DOMAIN.to_vec();
                    if let Ok(raw) = hex::decode(&ph) {
                        msg.extend_from_slice(&raw);
                    }
                    let vk = keyj
                        .get("verifying_key_hex")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    if verify_ed25519(
                        vk,
                        &msg,
                        env.get("signature").and_then(|v| v.as_str()).unwrap_or(""),
                    ) {
                        checks.push("envelope_signature_valid_for_bundled_key".into());
                    } else {
                        fail("SIGNATURE_INVALID", &mut errors);
                    }
                    if manifest.bindings.envelope_payload_hash != ph {
                        fail("BINDING_PAYLOAD_HASH_MISMATCH", &mut errors);
                    }
                }
            }
            Err(e) => fail(&e, &mut errors),
        }
        if dec.get("outcome").and_then(|v| v.as_str()) != Some("ACCEPTED")
            || dec.get("code").and_then(|v| v.as_str())
                != Some("ACCEPTED_SIMULATION_STOP_AUTHORIZATION")
        {
            fail("DECISION_NOT_ACCEPTED_SIMULATION_STOP", &mut errors);
        } else {
            checks.push("decision_accepted_simulation_stop".into());
        }
        if dec.get("observed_state").and_then(|v| v.as_str()) != Some("UNKNOWN")
            || dec.get("physical_state_claim").and_then(|v| v.as_str()) != Some("NONE")
        {
            fail("DECISION_PHYSICAL_CLAIM_VIOLATION", &mut errors);
        }
        if dec.get("sequence") != env.get("sequence") {
            fail("DECISION_SEQUENCE_MISMATCH", &mut errors);
        }
        for (dk, ek) in [("robot_id", "robot_id"), ("simulation_id", "simulation_id")] {
            if dec.get(dk) != env.get(ek) {
                fail("DECISION_SCOPE_MISMATCH", &mut errors);
            }
        }
        if keyj.get("kid") != env.get("kid")
            || manifest.kid != env.get("kid").and_then(|v| v.as_str()).unwrap_or("")
        {
            fail("KID_MISMATCH", &mut errors);
        }
    } else {
        fail("SECURE_CORE_JSON_MALFORMED", &mut errors);
    }
    // audit chain
    if let Some(auditj) = &auditj {
        let recs: Result<Vec<AuditRecord>, _> = serde_json::from_value(auditj.clone());
        match recs {
            Ok(recs) => {
                let mut prev = GENESIS.to_string();
                let mut ok = true;
                for (idx, r) in recs.iter().enumerate() {
                    if r.seq != idx as u64 + 1
                        || r.prev_hash != prev
                        || audit_hash(r.seq, &prev, &r.payload_hash, &r.decision_code)
                            != r.record_hash
                    {
                        fail("AUDIT_CHAIN_INVALID", &mut errors);
                        ok = false;
                        break;
                    }
                    prev = r.record_hash.clone();
                }
                if ok && !recs.is_empty() {
                    checks.push("audit_chain_hash_linked".into());
                    if manifest.bindings.audit_tip_hash != prev
                        || manifest.bindings.audit_records != recs.len() as u64
                    {
                        fail("BINDING_AUDIT_TIP_MISMATCH", &mut errors);
                    }
                    if let Some(env) = &env {
                        if recs[0].payload_hash
                            != env
                                .get("payload_hash")
                                .and_then(|v| v.as_str())
                                .unwrap_or("")
                        {
                            fail("AUDIT_ENVELOPE_BINDING_MISMATCH", &mut errors);
                        }
                    }
                } else if recs.is_empty() {
                    fail("AUDIT_EMPTY", &mut errors);
                }
            }
            Err(_) => fail("AUDIT_MALFORMED", &mut errors),
        }
    }
    // replay determinism
    if let (Some(a), Some(b), Some(c), Some(d)) = (
        files.get("copper/original-task-outputs.bin"),
        files.get("copper/replay-task-outputs.bin"),
        files.get("copper/original_0.copper"),
        files.get("copper/replay_0.copper"),
    ) {
        if a != b {
            fail("REPLAY_TASK_OUTPUTS_MISMATCH", &mut errors);
        } else {
            checks.push("copper_replay_task_outputs_byte_identical".into());
        }
        if c != d {
            fail("REPLAY_COPPER_LOGS_MISMATCH", &mut errors);
        } else {
            checks.push("copper_logs_byte_identical".into());
        }
        if manifest.bindings.original_task_outputs_sha256 != sha256_hex(a)
            || manifest.bindings.replay_task_outputs_sha256 != sha256_hex(b)
        {
            fail("BINDING_REPLAY_HASH_MISMATCH", &mut errors);
        }
    }
    if let Some(comp) = files.get("copper/comparison.txt") {
        let t = String::from_utf8_lossy(comp);
        if !(t.contains("command=STOP")
            && t.contains("authorized=true")
            && t.contains("byte_identical=true"))
        {
            fail("STOP_NOT_RECORDED_IN_COMPARISON", &mut errors);
        } else {
            checks.push("stop_recorded_in_copper_comparison".into());
        }
    }
    // attestation over manifest
    if let (Some(attb), Some(keyj)) = (files.get("attestation.json"), &keyj) {
        if let Ok(att) = serde_json::from_slice::<Attestation>(attb) {
            let mut msg = ATTEST_DOMAIN.to_vec();
            msg.extend_from_slice(&Sha256::digest(manifest_bytes));
            if att.manifest_sha256 != sha256_hex(manifest_bytes)
                || !verify_ed25519(
                    keyj.get("verifying_key_hex")
                        .and_then(|v| v.as_str())
                        .unwrap_or(""),
                    &msg,
                    &att.signature,
                )
            {
                fail("ATTESTATION_INVALID", &mut errors);
            } else {
                checks.push("bundle_attestation_valid_for_bundled_key".into());
            }
        } else {
            fail("ATTESTATION_MALFORMED", &mut errors);
        }
    } else {
        fail("ATTESTATION_MISSING", &mut errors);
    }
    // claims exactness
    if manifest.claims.supported_if_valid != SUPPORTED || manifest.claims.unsupported != UNSUPPORTED
    {
        fail("CLAIMS_LIST_MISMATCH", &mut errors);
    } else {
        checks.push("claims_lists_exact".into());
    }
    rep(checks, errors)
}
fn rep(checks: Vec<String>, errors: Vec<String>) -> Report {
    let ok = errors.is_empty();
    Report {
        verdict: if ok {
            "PASS_LIMITED_CLAIMS".into()
        } else {
            "REJECT".into()
        },
        format_version: FORMAT_VERSION,
        supported_claims: if ok {
            SUPPORTED.iter().map(|s| s.to_string()).collect()
        } else {
            vec![]
        },
        unsupported_claims: UNSUPPORTED.iter().map(|s| s.to_string()).collect(),
        checks,
        errors,
    }
}
