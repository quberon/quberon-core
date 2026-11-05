use quberon_evidence_bundle::{read_bundle, validate, write_bundle};
use std::path::PathBuf;

fn fixture(name: &str) -> Vec<u8> {
    let p: PathBuf = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../tools/quberon-verify/tests/fixtures")
        .join(name);
    std::fs::read(&p).unwrap_or_else(|_| {
        panic!("fixture missing at {p:?} — regenerate via scripts/build-fixture.py")
    })
}
#[test]
fn real_simulated_stop_bundle_passes_limited_claims() {
    let r = validate(&fixture("simulated-stop.qeb"));
    assert_eq!(r.verdict, "PASS_LIMITED_CLAIMS", "{:?}", r.errors);
    assert!(r
        .supported_claims
        .iter()
        .any(|c| c == "copper_replay_task_outputs_byte_identical"));
    assert!(r
        .unsupported_claims
        .iter()
        .any(|c| c.starts_with("physical_stop")));
}
#[test]
fn committed_tampered_replay_is_rejected_precisely() {
    let r = validate(&fixture("tampered-replay.qeb"));
    assert_eq!(r.verdict, "REJECT");
    assert!(
        r.errors.iter().any(|e| e == "REPLAY_TASK_OUTPUTS_MISMATCH"),
        "{:?}",
        r.errors
    );
    assert!(r
        .errors
        .iter()
        .any(|e| e == "HASH_MISMATCH:copper/replay-task-outputs.bin"));
}
#[test]
fn signature_tamper_is_rejected() {
    let mut files = read_bundle(&fixture("simulated-stop.qeb")).unwrap();
    let mut env: serde_json::Value =
        serde_json::from_slice(&files["secure-core/envelope.json"]).unwrap();
    let sig = env["signature"].as_str().unwrap().to_string();
    env["signature"] = serde_json::Value::String(format!(
        "{}{}",
        if sig.starts_with('0') { "1" } else { "0" },
        &sig[1..]
    ));
    files.insert(
        "secure-core/envelope.json".into(),
        serde_json::to_vec(&env).unwrap(),
    );
    let r = validate(&write_bundle(&files).unwrap());
    assert_eq!(r.verdict, "REJECT");
    assert!(
        r.errors.iter().any(|e| e == "SIGNATURE_INVALID"),
        "{:?}",
        r.errors
    );
}
#[test]
fn audit_chain_tamper_is_rejected() {
    let mut files = read_bundle(&fixture("simulated-stop.qeb")).unwrap();
    let mut audit: serde_json::Value =
        serde_json::from_slice(&files["secure-core/audit.json"]).unwrap();
    audit[0]["record_hash"] = serde_json::Value::String("f".repeat(64));
    files.insert(
        "secure-core/audit.json".into(),
        serde_json::to_vec(&audit).unwrap(),
    );
    let r = validate(&write_bundle(&files).unwrap());
    assert!(
        r.errors.iter().any(|e| e == "AUDIT_CHAIN_INVALID"),
        "{:?}",
        r.errors
    );
}
#[test]
fn garbage_is_rejected() {
    assert_eq!(validate(b"not a bundle").verdict, "REJECT");
}
