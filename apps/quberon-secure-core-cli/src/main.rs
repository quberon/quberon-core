//! quberon-secure-core-cli — narrow subprocess boundary to the secure core.
//! SIMULATION ONLY, STOP AUTHORIZATION ONLY. NO PHYSICAL CONTROL.
//! NOT A SAFETY-RATED E-STOP.
//!
//! Subcommands (JSON on stdin, one JSON object on stdout, bounded input,
//! no panic crosses this boundary):
//!   generate-keypair                       -> {"signing_key_hex","verifying_key_hex"}
//!   sign        {seed_hex,kid,issuer,robot_id,simulation_id,subject,
//!                sequence,issued_at_unix,expires_at_unix} -> envelope JSON
//!   authorize   {db_path, trusted:[{kid,issuer,robot_id,simulation_id,
//!                verifying_key_hex}], envelope:{...}, now_unix} -> decision JSON

use quberon_secure_core::*;
use std::collections::BTreeMap;
use std::io::Read;
use std::path::Path;

const MAX_STDIN: usize = 32_768;

fn decision_json(code: &str) -> String {
    serde_json::json!({
        "version": ENVELOPE_VERSION, "outcome": "REJECTED", "code": code,
        "action": "STOP", "robot_id": "", "simulation_id": "",
        "observed_state": "UNKNOWN", "physical_state_claim": "NONE"
    })
    .to_string()
}

fn read_stdin() -> Result<String, String> {
    let mut buf = String::new();
    std::io::stdin()
        .take((MAX_STDIN + 1) as u64)
        .read_to_string(&mut buf)
        .map_err(|_| "INPUT_ERROR".to_string())?;
    if buf.len() > MAX_STDIN {
        return Err("INPUT_TOO_LARGE".into());
    }
    Ok(buf)
}

fn hex32(s: &str) -> Result<[u8; 32], String> {
    let b = hex_decode(s).ok_or("HEX_MALFORMED")?;
    b.try_into().map_err(|_| "HEX_MALFORMED".into())
}

fn hex_decode(s: &str) -> Option<Vec<u8>> {
    if s.len() % 2 != 0 || !s.bytes().all(|c| c.is_ascii_hexdigit()) {
        return None;
    }
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).ok())
        .collect()
}

fn run() -> String {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let cmd = args.first().map(|s| s.as_str()).unwrap_or("");
    match cmd {
        "generate-keypair" => {
            let (seed, vk) = generate_keypair();
            serde_json::json!({
                "signing_key_hex": hex_encode(&seed),
                "verifying_key_hex": hex_encode(&vk),
            })
            .to_string()
        }
        "sign" => {
            let input = match read_stdin() {
                Ok(v) => v,
                Err(c) => return decision_json(&c),
            };
            let v: serde_json::Value = match serde_json::from_str(&input) {
                Ok(v) => v,
                Err(_) => return decision_json("REQUEST_MALFORMED"),
            };
            let get_s = |k: &str| v.get(k).and_then(|x| x.as_str()).map(|s| s.to_string());
            let get_i = |k: &str| v.get(k).and_then(|x| x.as_i64());
            let get_u = |k: &str| v.get(k).and_then(|x| x.as_u64());
            let (
                Some(seed),
                Some(kid),
                Some(issuer),
                Some(robot),
                Some(sim),
                Some(subject),
                Some(seq),
                Some(iat),
                Some(exp),
            ) = (
                get_s("signing_key_hex"),
                get_s("kid"),
                get_s("issuer"),
                get_s("robot_id"),
                get_s("simulation_id"),
                get_s("subject"),
                get_u("sequence"),
                get_i("issued_at_unix"),
                get_i("expires_at_unix"),
            )
            else {
                return decision_json("REQUEST_MALFORMED");
            };
            let seed = match hex32(&seed) {
                Ok(s) => s,
                Err(c) => return decision_json(&c),
            };
            let sk = signing_key_from_seed(&seed);
            let env = sign_envelope(&sk, &kid, &issuer, &robot, &sim, &subject, seq, iat, exp);
            serde_json::to_string(&env).unwrap_or_else(|_| decision_json("INTERNAL_ERROR"))
        }
        "authorize" => {
            let input = match read_stdin() {
                Ok(v) => v,
                Err(c) => return decision_json(&c),
            };
            let v: serde_json::Value = match serde_json::from_str(&input) {
                Ok(v) => v,
                Err(_) => return decision_json("REQUEST_MALFORMED"),
            };
            let (Some(db_path), Some(envelope), Some(now)) = (
                v.get("db_path")
                    .and_then(|x| x.as_str())
                    .map(|s| s.to_string()),
                v.get("envelope").cloned(),
                v.get("now_unix").and_then(|x| x.as_i64()),
            ) else {
                return decision_json("REQUEST_MALFORMED");
            };
            let mut trusted = BTreeMap::new();
            if let Some(list) = v.get("trusted").and_then(|x| x.as_array()) {
                for t in list {
                    let (Some(kid), Some(issuer), Some(robot), Some(sim), Some(vk)) = (
                        t.get("kid").and_then(|x| x.as_str()),
                        t.get("issuer").and_then(|x| x.as_str()),
                        t.get("robot_id").and_then(|x| x.as_str()),
                        t.get("simulation_id").and_then(|x| x.as_str()),
                        t.get("verifying_key_hex").and_then(|x| x.as_str()),
                    ) else {
                        return decision_json("TRUSTED_CONFIG_MALFORMED");
                    };
                    let vk_bytes = match hex32(vk) {
                        Ok(b) => b,
                        Err(c) => return decision_json(&c),
                    };
                    let key = match verifying_key_from_bytes(&vk_bytes) {
                        Ok(k) => k,
                        Err(_) => return decision_json("KEY_MALFORMED"),
                    };
                    trusted.insert(
                        kid.to_string(),
                        TrustedIssuer {
                            issuer: issuer.into(),
                            robot_id: robot.into(),
                            simulation_id: sim.into(),
                            verifying_key: key,
                        },
                    );
                }
            }
            if trusted.is_empty() {
                return decision_json("TRUSTED_CONFIG_MALFORMED");
            }
            let env_bytes = match serde_json::to_vec(&envelope) {
                Ok(b) => b,
                Err(_) => return decision_json("ENVELOPE_MALFORMED"),
            };
            let result = std::panic::catch_unwind(move || {
                let mut auth = match Authorizer::open(Path::new(&db_path), trusted) {
                    Ok(a) => a,
                    Err(d) => return d,
                };
                auth.authorize(&env_bytes, now)
            });
            match result {
                Ok(d) => {
                    serde_json::to_string(&d).unwrap_or_else(|_| decision_json("INTERNAL_ERROR"))
                }
                Err(_) => decision_json("INTERNAL_ERROR"),
            }
        }
        _ => decision_json("USAGE_REJECTED"),
    }
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn main() {
    // A panic must never cross the subprocess boundary as a crash contract:
    // run() already catch_unwinds the core call; wrap the rest too.
    let out = std::panic::catch_unwind(run).unwrap_or_else(|_| decision_json("INTERNAL_ERROR"));
    println!("{out}");
}
