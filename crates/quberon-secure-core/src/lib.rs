//! quberon-secure-core — SIMULATION ONLY, STOP AUTHORIZATION ONLY.
//! NO PHYSICAL CONTROL. NOT A SAFETY-RATED E-STOP.
//!
//! This crate verifies a versioned, deterministic, Ed25519-signed STOP
//! authorization envelope for one exact (issuer, robot, simulation) scope,
//! enforces durable replay protection and a hash-chained audit log in
//! SQLite, and returns a stable machine-readable decision. It contains no
//! motion, reset, unlatch, or task representation by design.
//!
//! The decision vocabulary deliberately never asserts a physical state:
//! an accepted decision means only "a simulation STOP may be requested".

#![forbid(unsafe_code)]
// Decision doubles as the stable machine-readable error value; boxing it
// would obscure that contract, and this is not a hot path.
#![allow(clippy::result_large_err)]

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rusqlite::{params, Connection, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::path::Path;

pub const ENVELOPE_VERSION: u32 = 1;
pub const MAX_ENVELOPE_BYTES: usize = 8_192;
pub const MAX_VALIDITY_SECONDS: i64 = 300;
pub const MAX_FUTURE_SKEW_SECONDS: i64 = 30;
const SIGN_DOMAIN: &[u8] = b"QUBERON-SECURE-CORE/SIGN/v1\0";
const HASH_DOMAIN: &[u8] = b"QUBERON-SECURE-CORE/PAYLOAD/v1\0";
const AUDIT_DOMAIN: &[u8] = b"QUBERON-SECURE-CORE/AUDIT/v1\0";
const GENESIS_HASH: &str = "0000000000000000000000000000000000000000000000000000000000000000";

/// Closed action enum: STOP is the only representable action. Any other
/// action string fails deserialization and is rejected; there is no variant
/// for reset, unlatch, task, or motion.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Action {
    #[serde(rename = "STOP")]
    Stop,
}

/// Versioned signed envelope. Unknown fields are denied so that smuggled
/// fields (e.g. a reset flag) cannot be carried through the boundary.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Envelope {
    pub version: u32,
    pub kid: String,
    pub issuer: String,
    pub robot_id: String,
    pub simulation_id: String,
    /// Authenticated human/service subject the envelope was issued for.
    /// Bounded and non-empty; scope pinning applies to issuer/robot/sim.
    pub subject: String,
    pub action: Action,
    pub sequence: u64,
    pub issued_at_unix: i64,
    pub expires_at_unix: i64,
    /// Lowercase hex SHA-256 over the domain-separated canonical payload.
    pub payload_hash: String,
    /// Lowercase hex Ed25519 signature over domain-separated payload hash.
    pub signature: String,
}

#[derive(Debug, Clone)]
pub struct TrustedIssuer {
    pub issuer: String,
    pub robot_id: String,
    pub simulation_id: String,
    pub verifying_key: VerifyingKey,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Decision {
    pub version: u32,
    /// "ACCEPTED" or "REJECTED". Acceptance means only that a *simulation*
    /// STOP may be requested; it never asserts any physical state.
    pub outcome: String,
    pub code: String,
    pub action: String,
    pub robot_id: String,
    pub simulation_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sequence: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub audit_record: Option<u64>,
    /// Always "UNKNOWN": this core observes no physical or simulated state.
    pub observed_state: String,
    /// Always "NONE": this core makes no physical-state claim.
    pub physical_state_claim: String,
}

impl Decision {
    fn rejected(code: &str, env: Option<&Envelope>) -> Self {
        Decision {
            version: ENVELOPE_VERSION,
            outcome: "REJECTED".into(),
            code: code.into(),
            action: "STOP".into(),
            robot_id: env.map(|e| e.robot_id.clone()).unwrap_or_default(),
            simulation_id: env.map(|e| e.simulation_id.clone()).unwrap_or_default(),
            sequence: env.map(|e| e.sequence),
            audit_record: None,
            observed_state: "UNKNOWN".into(),
            physical_state_claim: "NONE".into(),
        }
    }
}

fn rejected(code: &str) -> Decision {
    Decision::rejected(code, None)
}

/// Deterministic canonical payload encoding: length-prefixed fields in a
/// fixed order. No map ordering, float, or whitespace ambiguity.
pub fn canonical_payload(e: &Envelope) -> Vec<u8> {
    fn put(buf: &mut Vec<u8>, bytes: &[u8]) {
        buf.extend_from_slice(&(bytes.len() as u64).to_be_bytes());
        buf.extend_from_slice(bytes);
    }
    let mut b = Vec::with_capacity(256);
    put(&mut b, HASH_DOMAIN);
    put(&mut b, &e.version.to_be_bytes());
    put(&mut b, e.kid.as_bytes());
    put(&mut b, e.issuer.as_bytes());
    put(&mut b, e.robot_id.as_bytes());
    put(&mut b, e.simulation_id.as_bytes());
    put(&mut b, e.subject.as_bytes());
    put(&mut b, b"STOP");
    put(&mut b, &e.sequence.to_be_bytes());
    put(&mut b, &e.issued_at_unix.to_be_bytes());
    put(&mut b, &e.expires_at_unix.to_be_bytes());
    b
}

pub fn compute_payload_hash(e: &Envelope) -> String {
    hex::encode(Sha256::digest(canonical_payload(e)))
}

fn signing_message(payload_hash_hex: &str) -> Vec<u8> {
    let mut m = Vec::with_capacity(SIGN_DOMAIN.len() + 32);
    m.extend_from_slice(SIGN_DOMAIN);
    if let Ok(raw) = hex::decode(payload_hash_hex) {
        m.extend_from_slice(&raw);
    }
    m
}

/// Build and sign an envelope. Used by the CLI signer; the private key is
/// supplied by the caller and is never stored by this crate.
#[allow(clippy::too_many_arguments)] // explicit signed-field list is the API contract
pub fn sign_envelope(
    signing_key: &SigningKey,
    kid: &str,
    issuer: &str,
    robot_id: &str,
    simulation_id: &str,
    subject: &str,
    sequence: u64,
    issued_at_unix: i64,
    expires_at_unix: i64,
) -> Envelope {
    let mut e = Envelope {
        version: ENVELOPE_VERSION,
        kid: kid.into(),
        issuer: issuer.into(),
        robot_id: robot_id.into(),
        simulation_id: simulation_id.into(),
        subject: subject.into(),
        action: Action::Stop,
        sequence,
        issued_at_unix,
        expires_at_unix,
        payload_hash: String::new(),
        signature: String::new(),
    };
    e.payload_hash = compute_payload_hash(&e);
    let sig = signing_key.sign(&signing_message(&e.payload_hash));
    e.signature = hex::encode(sig.to_bytes());
    e
}

fn bounded_field(s: &str, max: usize) -> bool {
    !s.is_empty() && s.len() <= max && s.bytes().all(|c| (0x21..0x7f).contains(&c))
}

fn verify_audit_chain(conn: &Connection) -> Result<(), Decision> {
    let mut stmt = conn
        .prepare("SELECT seq,payload_hash,decision_code,prev_hash,record_hash FROM audit ORDER BY seq ASC")
        .map_err(|_| rejected("AUDIT_UNAVAILABLE"))?;
    let rows = stmt
        .query_map([], |r| {
            Ok((
                r.get::<_, i64>(0)?,
                r.get::<_, String>(1)?,
                r.get::<_, String>(2)?,
                r.get::<_, String>(3)?,
                r.get::<_, String>(4)?,
            ))
        })
        .map_err(|_| rejected("AUDIT_UNAVAILABLE"))?;
    let mut prev = GENESIS_HASH.to_string();
    for (idx, row) in rows.enumerate() {
        let expect_seq = idx as i64 + 1;
        let (seq, ph, code, ph_prev, rh) =
            row.map_err(|_| Decision::rejected("AUDIT_CHAIN_INVALID", None))?;
        if seq != expect_seq || ph_prev != prev {
            return Err(rejected("AUDIT_CHAIN_INVALID"));
        }
        let mut h = Sha256::new();
        h.update(AUDIT_DOMAIN);
        h.update(seq.to_be_bytes());
        h.update(prev.as_bytes());
        h.update(ph.as_bytes());
        h.update(code.as_bytes());
        if hex::encode(h.finalize()) != rh {
            return Err(rejected("AUDIT_CHAIN_INVALID"));
        }
        prev = rh;
    }
    // Include the tip in subsequent inserts via `prev`.
    let _ = prev;
    Ok(())
}

fn chain_tip(conn: &Connection) -> Result<(i64, String), Decision> {
    let tip: Option<(i64, String)> = conn
        .query_row(
            "SELECT seq,record_hash FROM audit ORDER BY seq DESC LIMIT 1",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()
        .map_err(|_| rejected("AUDIT_UNAVAILABLE"))?;
    Ok(match tip {
        Some((s, h)) => (s, h),
        None => (0, GENESIS_HASH.to_string()),
    })
}

pub struct Authorizer {
    conn: Connection,
    trusted: BTreeMap<String, TrustedIssuer>,
}

impl Authorizer {
    pub fn open(
        db_path: &Path,
        trusted: BTreeMap<String, TrustedIssuer>,
    ) -> Result<Self, Decision> {
        let conn = Connection::open(db_path).map_err(|_| rejected("AUDIT_UNAVAILABLE"))?;
        conn.execute_batch(
            "PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;
             CREATE TABLE IF NOT EXISTS replay(
               scope TEXT PRIMARY KEY, last_sequence INTEGER NOT NULL);
             CREATE TABLE IF NOT EXISTS audit(
               seq INTEGER PRIMARY KEY, payload_hash TEXT NOT NULL,
               decision_code TEXT NOT NULL, prev_hash TEXT NOT NULL,
               record_hash TEXT NOT NULL);",
        )
        .map_err(|_| rejected("AUDIT_UNAVAILABLE"))?;
        verify_audit_chain(&conn)?;
        Ok(Authorizer { conn, trusted })
    }

    /// Verify an envelope (raw bytes, bounded) at `now_unix`. Acceptance is
    /// returned only after the replay+audit transaction commits; any audit,
    /// replay, signature, scope, or time failure is a rejection. This
    /// function does not panic on malformed input.
    pub fn authorize(&mut self, envelope_bytes: &[u8], now_unix: i64) -> Decision {
        if envelope_bytes.is_empty() || envelope_bytes.len() > MAX_ENVELOPE_BYTES {
            return rejected("ENVELOPE_SIZE_REJECTED");
        }
        let env: Envelope = match serde_json::from_slice(envelope_bytes) {
            Ok(e) => e,
            Err(_) => return rejected("ENVELOPE_MALFORMED"),
        };
        let fail = |code: &str| Decision::rejected(code, Some(&env));

        if env.version != ENVELOPE_VERSION {
            return fail("VERSION_REJECTED");
        }
        if !bounded_field(&env.kid, 64)
            || !bounded_field(&env.issuer, 128)
            || !bounded_field(&env.robot_id, 128)
            || !bounded_field(&env.simulation_id, 128)
            || !bounded_field(&env.subject, 128)
        {
            return fail("FIELD_REJECTED");
        }
        let trusted = match self.trusted.get(&env.kid) {
            Some(t) => t,
            None => return fail("UNTRUSTED_ISSUER"),
        };
        // Exact scope: issuer, robot and simulation must all match the
        // trusted entry pinned to this key id. No wildcards.
        if trusted.issuer != env.issuer
            || trusted.robot_id != env.robot_id
            || trusted.simulation_id != env.simulation_id
        {
            return fail("SCOPE_MISMATCH");
        }
        let validity = env.expires_at_unix.saturating_sub(env.issued_at_unix);
        if validity <= 0 || validity > MAX_VALIDITY_SECONDS {
            return fail("VALIDITY_WINDOW_REJECTED");
        }
        if env.issued_at_unix > now_unix.saturating_add(MAX_FUTURE_SKEW_SECONDS) {
            return fail("ISSUED_IN_FUTURE");
        }
        if env.expires_at_unix <= now_unix {
            return fail("EXPIRED");
        }
        if env.payload_hash.len() != 64
            || !env
                .payload_hash
                .bytes()
                .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase())
            || compute_payload_hash(&env) != env.payload_hash
        {
            return fail("PAYLOAD_HASH_MISMATCH");
        }
        let sig_bytes = match hex::decode(&env.signature) {
            Ok(b) if b.len() == 64 => b,
            _ => return fail("SIGNATURE_MALFORMED"),
        };
        let sig_arr: [u8; 64] = match sig_bytes.try_into() {
            Ok(a) => a,
            Err(_) => return fail("SIGNATURE_MALFORMED"),
        };
        let signature = Signature::from_bytes(&sig_arr);
        if trusted
            .verifying_key
            .verify(&signing_message(&env.payload_hash), &signature)
            .is_err()
        {
            return fail("SIGNATURE_INVALID");
        }

        // Durable phase: replay + hash-chained audit in ONE transaction.
        // Acceptance is returned only after COMMIT succeeds.
        let tx = match self
            .conn
            .transaction_with_behavior(TransactionBehavior::Immediate)
        {
            Ok(t) => t,
            Err(_) => return fail("AUDIT_UNAVAILABLE"),
        };
        if let Err(d) = verify_audit_chain(&tx) {
            return d;
        }
        let scope = format!("{}\0{}\0{}", env.issuer, env.robot_id, env.simulation_id);
        let last: Option<i64> = match tx
            .query_row(
                "SELECT last_sequence FROM replay WHERE scope=?1",
                params![scope],
                |r| r.get(0),
            )
            .optional()
        {
            Ok(v) => v,
            Err(_) => return fail("AUDIT_UNAVAILABLE"),
        };
        let is_replay = last.map(|l| (env.sequence as i64) <= l).unwrap_or(false);
        let code = if is_replay {
            "REPLAY_REJECTED"
        } else {
            "ACCEPTED_SIMULATION_STOP_AUTHORIZATION"
        };
        let (tip_seq, tip_hash) = match chain_tip(&tx) {
            Ok(v) => v,
            Err(d) => return d,
        };
        let next_seq = tip_seq + 1;
        let mut h = Sha256::new();
        h.update(AUDIT_DOMAIN);
        h.update(next_seq.to_be_bytes());
        h.update(tip_hash.as_bytes());
        h.update(env.payload_hash.as_bytes());
        h.update(code.as_bytes());
        let record_hash = hex::encode(h.finalize());
        if tx
            .execute(
                "INSERT INTO audit(seq,payload_hash,decision_code,prev_hash,record_hash) VALUES (?1,?2,?3,?4,?5)",
                params![next_seq, env.payload_hash, code, tip_hash, record_hash],
            )
            .is_err()
        {
            return fail("AUDIT_WRITE_FAILED");
        }
        if !is_replay
            && tx
                .execute(
                    "INSERT INTO replay(scope,last_sequence) VALUES (?1,?2)
                     ON CONFLICT(scope) DO UPDATE SET last_sequence=excluded.last_sequence",
                    params![scope, env.sequence as i64],
                )
                .is_err()
        {
            return fail("REPLAY_WRITE_FAILED");
        }
        if tx.commit().is_err() {
            return fail("AUDIT_COMMIT_FAILED");
        }
        if is_replay {
            let mut d = fail("REPLAY_REJECTED");
            d.audit_record = Some(next_seq as u64);
            return d;
        }
        Decision {
            version: ENVELOPE_VERSION,
            outcome: "ACCEPTED".into(),
            code: code.into(),
            action: "STOP".into(),
            robot_id: env.robot_id.clone(),
            simulation_id: env.simulation_id.clone(),
            sequence: Some(env.sequence),
            audit_record: Some(next_seq as u64),
            observed_state: "UNKNOWN".into(),
            physical_state_claim: "NONE".into(),
        }
    }
}

/// Generate a fresh Ed25519 keypair (seed bytes, verifying-key bytes).
/// The caller owns secret custody; this crate stores no secrets.
pub fn generate_keypair() -> ([u8; 32], [u8; 32]) {
    let sk = SigningKey::generate(&mut rand_core::OsRng);
    (sk.to_bytes(), sk.verifying_key().to_bytes())
}

pub fn verifying_key_from_bytes(bytes: &[u8; 32]) -> Result<VerifyingKey, Decision> {
    VerifyingKey::from_bytes(bytes).map_err(|_| rejected("KEY_MALFORMED"))
}

pub fn signing_key_from_seed(seed: &[u8; 32]) -> SigningKey {
    SigningKey::from_bytes(seed)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn setup() -> (tempfile::TempDir, Authorizer, SigningKey) {
        let dir = tempfile::tempdir().unwrap();
        let sk = SigningKey::generate(&mut rand_core::OsRng);
        let mut trusted = BTreeMap::new();
        trusted.insert(
            "k1".into(),
            TrustedIssuer {
                issuer: "issuer-1".into(),
                robot_id: "robot-1".into(),
                simulation_id: "sim-1".into(),
                verifying_key: sk.verifying_key(),
            },
        );
        let auth = Authorizer::open(&dir.path().join("core.db"), trusted).unwrap();
        (dir, auth, sk)
    }
    fn env(sk: &SigningKey, seq: u64, iat: i64, exp: i64) -> Vec<u8> {
        serde_json::to_vec(&sign_envelope(
            sk, "k1", "issuer-1", "robot-1", "sim-1", "op-1", seq, iat, exp,
        ))
        .unwrap()
    }
    #[test]
    fn accepts_valid_then_replay_rejected() {
        let (_d, mut a, sk) = setup();
        let d1 = a.authorize(&env(&sk, 1, 900, 1100), 1000);
        assert_eq!(d1.code, "ACCEPTED_SIMULATION_STOP_AUTHORIZATION");
        assert_eq!(d1.observed_state, "UNKNOWN");
        let d2 = a.authorize(&env(&sk, 1, 900, 1100), 1000);
        assert_eq!(d2.code, "REPLAY_REJECTED");
        assert_eq!(
            a.authorize(&env(&sk, 2, 900, 1100), 1000).outcome,
            "ACCEPTED"
        );
    }
    #[test]
    fn rejects_expired_future_long_validity_and_tamper() {
        let (_d, mut a, sk) = setup();
        assert_eq!(a.authorize(&env(&sk, 1, 100, 200), 1000).code, "EXPIRED");
        assert_eq!(
            a.authorize(&env(&sk, 1, 2000, 2100), 1000).code,
            "ISSUED_IN_FUTURE"
        );
        assert_eq!(
            a.authorize(&env(&sk, 1, 900, 2000), 1000).code,
            "VALIDITY_WINDOW_REJECTED"
        );
        let mut v: serde_json::Value = serde_json::from_slice(&env(&sk, 5, 900, 1100)).unwrap();
        v["robot_id"] = "robot-2".into();
        assert_eq!(
            a.authorize(&serde_json::to_vec(&v).unwrap(), 1000).code,
            "SCOPE_MISMATCH"
        );
        let mut v: serde_json::Value = serde_json::from_slice(&env(&sk, 5, 900, 1100)).unwrap();
        v["subject"] = "mallory".into(); // signed payload changed
        assert_eq!(
            a.authorize(&serde_json::to_vec(&v).unwrap(), 1000).code,
            "PAYLOAD_HASH_MISMATCH"
        );
        let mut v: serde_json::Value = serde_json::from_slice(&env(&sk, 5, 900, 1100)).unwrap();
        v["action"] = "RESET".into();
        let d = a.authorize(&serde_json::to_vec(&v).unwrap(), 1000);
        assert_eq!(d.outcome, "REJECTED"); // closed enum: RESET not representable
        let mut v: serde_json::Value = serde_json::from_slice(&env(&sk, 5, 900, 1100)).unwrap();
        v["reset"] = true.into();
        assert_eq!(
            a.authorize(&serde_json::to_vec(&v).unwrap(), 1000).code,
            "ENVELOPE_MALFORMED"
        );
    }
    #[test]
    fn audit_tamper_rejects_next_authorization() {
        let (dir, mut a, sk) = setup();
        assert_eq!(
            a.authorize(&env(&sk, 1, 900, 1100), 1000).outcome,
            "ACCEPTED"
        );
        let db = dir.path().join("core.db");
        let c = Connection::open(&db).unwrap();
        c.execute("UPDATE audit SET decision_code='FORGED' WHERE seq=1", [])
            .unwrap();
        drop(c);
        drop(a);
        // Reopen also fails chain verification at open; a fresh authorizer on the
        // tampered DB must not accept.
        let mut trusted = BTreeMap::new();
        trusted.insert(
            "k1".into(),
            TrustedIssuer {
                issuer: "issuer-1".into(),
                robot_id: "robot-1".into(),
                simulation_id: "sim-1".into(),
                verifying_key: sk.verifying_key(),
            },
        );
        assert!(Authorizer::open(&db, trusted).is_err());
        let _ = dir;
    }
    proptest::proptest! {
        #[test]
        fn arbitrary_bytes_never_panic_and_never_accept(bytes in proptest::collection::vec(proptest::prelude::any::<u8>(), 0..9000)) {
            let (_d, mut a, _sk) = setup();
            let d = a.authorize(&bytes, 1000);
            proptest::prop_assert_eq!(d.outcome.as_str(), "REJECTED");
        }
    }
}
