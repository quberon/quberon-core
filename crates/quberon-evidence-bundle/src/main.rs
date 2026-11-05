//! Builder: quberon-bundle build --out B --bundle-id ID --kid KID
//!   --signing-seed-hex HEX --copper-dir DIR --secure-dir DIR --environment FILE
//! validate: quberon-bundle validate BUNDLE  (prints JSON report, exit 0/1)
//! secure-dir must contain envelope.json decision.json audit.json verifying-key.json
//! produced by the real secure-core CLI (see scripts/build-fixture.py).
#![forbid(unsafe_code)]
use quberon_evidence_bundle::*;
use std::collections::BTreeMap;
use std::process::ExitCode;

fn arg(args: &[String], k: &str) -> Option<String> {
    args.windows(2).find(|w| w[0] == k).map(|w| w[1].clone())
}
fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(|s| s.as_str()) {
        Some("validate") => {
            let Ok(b) = std::fs::read(&args[1]) else {
                println!("{{\"verdict\":\"REJECT\",\"errors\":[\"BUNDLE_UNREADABLE\"]}}");
                return ExitCode::from(1);
            };
            let r = validate(&b);
            println!("{}", serde_json::to_string_pretty(&r).unwrap());
            if r.verdict.starts_with("PASS") {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(1)
            }
        }
        Some("build") => {
            let (Some(out), Some(id), Some(seed)) = (
                arg(&args, "--out"),
                arg(&args, "--bundle-id"),
                arg(&args, "--signing-seed-hex"),
            ) else {
                eprintln!("missing --out/--bundle-id/--signing-seed-hex");
                return ExitCode::from(2);
            };
            let copper = arg(&args, "--copper-dir").unwrap();
            let secure = arg(&args, "--secure-dir").unwrap();
            let envp = arg(&args, "--environment").unwrap();
            let seedb: [u8; 32] = hex::decode(&seed).unwrap().try_into().unwrap();
            let sk = ed25519_dalek::SigningKey::from_bytes(&seedb);
            let mut payloads: BTreeMap<String, Vec<u8>> = BTreeMap::new();
            for (src, dst) in [
                (
                    format!("{copper}/original_0.copper"),
                    "copper/original_0.copper".to_string(),
                ),
                (
                    format!("{copper}/replay_0.copper"),
                    "copper/replay_0.copper".to_string(),
                ),
                (
                    format!("{copper}/original-task-outputs.bin"),
                    "copper/original-task-outputs.bin".to_string(),
                ),
                (
                    format!("{copper}/replay-task-outputs.bin"),
                    "copper/replay-task-outputs.bin".to_string(),
                ),
                (
                    format!("{copper}/comparison.txt"),
                    "copper/comparison.txt".to_string(),
                ),
                (
                    format!("{secure}/envelope.json"),
                    "secure-core/envelope.json".to_string(),
                ),
                (
                    format!("{secure}/decision.json"),
                    "secure-core/decision.json".to_string(),
                ),
                (
                    format!("{secure}/audit.json"),
                    "secure-core/audit.json".to_string(),
                ),
                (
                    format!("{secure}/verifying-key.json"),
                    "secure-core/verifying-key.json".to_string(),
                ),
                (envp.clone(), "environment.json".to_string()),
            ] {
                payloads.insert(
                    dst.to_string(),
                    std::fs::read(&src).unwrap_or_else(|_| panic!("read {src}")),
                );
            }
            let env: serde_json::Value =
                serde_json::from_slice(&payloads["secure-core/envelope.json"]).unwrap();
            let dec: serde_json::Value =
                serde_json::from_slice(&payloads["secure-core/decision.json"]).unwrap();
            let audit: Vec<AuditRecord> =
                serde_json::from_slice(&payloads["secure-core/audit.json"]).unwrap();
            let files: Vec<FileEntry> = payloads
                .iter()
                .map(|(p, d)| FileEntry {
                    path: p.clone(),
                    sha256: sha256_hex(d),
                    size: d.len() as u64,
                })
                .collect();
            let manifest = Manifest {
                format: FORMAT.into(),
                version: FORMAT_VERSION,
                bundle_id: id,
                simulation_only: true,
                physical_state_claim: "NONE".into(),
                certification_claim: "NONE".into(),
                kid: env["kid"].as_str().unwrap().into(),
                issuer: env["issuer"].as_str().unwrap().into(),
                robot_id: env["robot_id"].as_str().unwrap().into(),
                simulation_id: env["simulation_id"].as_str().unwrap().into(),
                files,
                bindings: Bindings {
                    envelope_payload_hash: env["payload_hash"].as_str().unwrap().into(),
                    audit_tip_hash: audit.last().unwrap().record_hash.clone(),
                    audit_records: audit.len() as u64,
                    decision_code: dec["code"].as_str().unwrap().into(),
                    sequence: env["sequence"].as_u64().unwrap(),
                    original_task_outputs_sha256: sha256_hex(
                        &payloads["copper/original-task-outputs.bin"],
                    ),
                    replay_task_outputs_sha256: sha256_hex(
                        &payloads["copper/replay-task-outputs.bin"],
                    ),
                    original_copper_sha256: sha256_hex(&payloads["copper/original_0.copper"]),
                    replay_copper_sha256: sha256_hex(&payloads["copper/replay_0.copper"]),
                },
                claims: Claims {
                    supported_if_valid: SUPPORTED.iter().map(|s| s.to_string()).collect(),
                    unsupported: UNSUPPORTED.iter().map(|s| s.to_string()).collect(),
                },
            };
            let mb = serde_json::to_vec_pretty(&manifest).unwrap();
            let att = sign_attestation(&sk, &manifest.kid, &mb);
            payloads.insert("manifest.json".into(), mb);
            payloads.insert(
                "attestation.json".into(),
                serde_json::to_vec_pretty(&att).unwrap(),
            );
            let bytes = write_bundle(&payloads).unwrap();
            let report = validate(&bytes);
            if !report.verdict.starts_with("PASS") {
                eprintln!("self-validation failed: {:?}", report.errors);
                return ExitCode::from(1);
            }
            std::fs::write(&out, bytes).unwrap();
            println!("WROTE {out}");
            ExitCode::SUCCESS
        }
        _ => {
            eprintln!("usage: build|validate");
            ExitCode::from(2)
        }
    }
}
