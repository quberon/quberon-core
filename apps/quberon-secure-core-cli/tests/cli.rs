use std::io::Write;
use std::process::{Command, Stdio};

fn run_cli(args: &[&str], stdin_data: &str) -> serde_json::Value {
    let mut child = Command::new(env!("CARGO_BIN_EXE_quberon-secure-core-cli"))
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(stdin_data.as_bytes())
        .unwrap();
    let out = child.wait_with_output().unwrap();
    serde_json::from_slice(&out.stdout).unwrap_or_else(|e| {
        panic!(
            "bad CLI output {e}: {}",
            String::from_utf8_lossy(&out.stdout)
        )
    })
}

#[test]
fn subprocess_sign_authorize_replay_and_tamper() {
    let keys = run_cli(&["generate-keypair"], "");
    let seed = keys["signing_key_hex"].as_str().unwrap();
    let vk = keys["verifying_key_hex"].as_str().unwrap();
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("core.db").to_string_lossy().to_string();
    let sign_req = serde_json::json!({"signing_key_hex": seed, "kid": "k1", "issuer": "issuer-1",
        "robot_id": "robot-1", "simulation_id": "sim-1", "subject": "op-1", "epoch": 1,
        "sequence": 1, "issued_at_unix": 900, "expires_at_unix": 1100});
    let env = run_cli(&["sign"], &sign_req.to_string());
    let auth_req = |e: serde_json::Value| {
        serde_json::json!({"db_path": db, "now_unix": 1000, "boot_epoch": 1,
        "trusted": [{"kid": "k1", "issuer": "issuer-1", "robot_id": "robot-1", "simulation_id": "sim-1", "verifying_key_hex": vk}],
        "envelope": e}).to_string()
    };
    let d = run_cli(&["authorize"], &auth_req(env.clone()));
    assert_eq!(d["code"], "ACCEPTED_SIMULATION_STOP_AUTHORIZATION");
    assert_eq!(d["observed_state"], "UNKNOWN");
    let d = run_cli(&["authorize"], &auth_req(env.clone()));
    assert_eq!(d["code"], "REPLAY_REJECTED");
    let mut forged = env.clone();
    forged["sequence"] = 2.into();
    let d = run_cli(&["authorize"], &auth_req(forged));
    assert_eq!(d["outcome"], "REJECTED");
}

#[test]
fn malformed_and_oversized_input_rejected_without_crash() {
    let d = run_cli(&["authorize"], "not json");
    assert_eq!(d["outcome"], "REJECTED");
    let d = run_cli(&["authorize"], &"x".repeat(40_000));
    assert_eq!(d["code"], "INPUT_TOO_LARGE");
    let d = run_cli(&["bogus"], "");
    assert_eq!(d["outcome"], "REJECTED");
}

#[test]
fn epoch_mismatch_and_anchor_rollback_via_cli() {
    let keys = run_cli(&["generate-keypair"], "");
    let seed = keys["signing_key_hex"].as_str().unwrap();
    let vk = keys["verifying_key_hex"].as_str().unwrap();
    let dir = tempfile::tempdir().unwrap();
    let db_path = dir.path().join("core.db");
    let db = db_path.to_string_lossy().to_string();
    let anchor = dir.path().join("anchor.json").to_string_lossy().to_string();
    let sign = |epoch: u64, seq: u64| {
        run_cli(
            &["sign"],
            &serde_json::json!({"signing_key_hex": seed, "kid": "k1", "issuer": "issuer-1",
            "robot_id": "robot-1", "simulation_id": "sim-1", "subject": "op-1", "epoch": epoch,
            "sequence": seq, "issued_at_unix": 900, "expires_at_unix": 1100})
            .to_string(),
        )
    };
    let auth = |e: serde_json::Value, epoch: u64| {
        run_cli(
            &["authorize"],
            &serde_json::json!({"db_path": db, "now_unix": 1000, "boot_epoch": epoch,
            "anchor_path": anchor,
            "trusted": [{"kid": "k1", "issuer": "issuer-1", "robot_id": "robot-1", "simulation_id": "sim-1", "verifying_key_hex": vk}],
            "envelope": e}).to_string(),
        )
    };
    assert_eq!(
        auth(sign(1, 1), 1)["code"],
        "ACCEPTED_SIMULATION_STOP_AUTHORIZATION"
    );
    // Envelope from the prior epoch, authorized in a new epoch: rejected.
    assert_eq!(auth(sign(1, 2), 2)["code"], "EPOCH_REJECTED");
    assert_eq!(
        auth(sign(2, 2), 2)["code"],
        "ACCEPTED_SIMULATION_STOP_AUTHORIZATION"
    );
    // Roll the DB back to nothing-but-anchor state by removing it: a fresh
    // empty DB against a non-genesis anchor is a rollback, not a fresh start.
    std::fs::remove_file(&db_path).unwrap();
    for s in ["-wal", "-shm"] {
        let _ = std::fs::remove_file(format!("{db}{s}"));
    }
    assert_eq!(auth(sign(2, 3), 2)["code"], "ROLLBACK_DETECTED");
}
