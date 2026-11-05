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
    /// Monotonic boot/session epoch of the issuing process. Envelopes from
    /// a prior epoch are rejected; the persisted replay sequence is *not*
    /// reset when the epoch advances.
    pub epoch: u64,
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
    /// Key-rotation / trust-entry scaffolding (no HSM claim): a key is only
    /// usable in `[valid_from_unix, valid_until_unix)` and never if revoked.
    /// `valid_until_unix == 0` means no expiry configured.
    pub valid_from_unix: i64,
    pub valid_until_unix: i64,
    pub revoked: bool,
}

impl TrustedIssuer {
    pub fn new(
        issuer: &str,
        robot_id: &str,
        simulation_id: &str,
        verifying_key: VerifyingKey,
    ) -> Self {
        TrustedIssuer {
            issuer: issuer.into(),
            robot_id: robot_id.into(),
            simulation_id: simulation_id.into(),
            verifying_key,
            valid_from_unix: 0,
            valid_until_unix: 0,
            revoked: false,
        }
    }
}

/// Externally anchored audit checkpoint. Anchoring the audit tip *outside*
/// the core DB lets an older-but-valid DB copy be detected as a rollback:
/// the DB tip can never legitimately move backwards from the anchor.
/// Production rollback resistance still requires hardware / remote
/// transparency anchoring — a local file is a simulation-grade anchor only.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Checkpoint {
    pub audit_seq: u64,
    pub record_hash: String,
}

pub trait AnchorStore {
    fn load(&self) -> Result<Option<Checkpoint>, Decision>;
    fn store(&self, checkpoint: &Checkpoint) -> Result<(), Decision>;
}

/// Local-file anchor for simulation: atomic replace (tmp + fsync + rename +
/// directory fsync) and strict `0600` permissions on Unix. NOT rollback-
/// resistant against an attacker who can rewrite both DB and anchor file.
pub struct FileAnchorStore {
    path: std::path::PathBuf,
}

impl FileAnchorStore {
    pub fn new(path: &Path) -> Self {
        FileAnchorStore {
            path: path.to_path_buf(),
        }
    }
    pub fn path(&self) -> &Path {
        &self.path
    }
}

#[cfg(unix)]
fn check_strict_permissions(path: &Path) -> Result<(), Decision> {
    use std::os::unix::fs::PermissionsExt;
    let mode = std::fs::metadata(path)
        .map_err(|_| rejected("ANCHOR_UNAVAILABLE"))?
        .permissions()
        .mode();
    if mode & 0o077 != 0 {
        return Err(rejected("ANCHOR_PERMISSIONS_REJECTED"));
    }
    Ok(())
}
#[cfg(not(unix))]
fn check_strict_permissions(_path: &Path) -> Result<(), Decision> {
    Ok(())
}

impl AnchorStore for FileAnchorStore {
    fn load(&self) -> Result<Option<Checkpoint>, Decision> {
        if !self.path.exists() {
            return Ok(None);
        }
        check_strict_permissions(&self.path)?;
        let raw = std::fs::read(&self.path).map_err(|_| rejected("ANCHOR_UNAVAILABLE"))?;
        if raw.len() > 4096 {
            return Err(rejected("ANCHOR_MALFORMED"));
        }
        let cp: Checkpoint =
            serde_json::from_slice(&raw).map_err(|_| rejected("ANCHOR_MALFORMED"))?;
        if cp.record_hash.len() != 64
            || !cp
                .record_hash
                .bytes()
                .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase())
        {
            return Err(rejected("ANCHOR_MALFORMED"));
        }
        Ok(Some(cp))
    }

    fn store(&self, checkpoint: &Checkpoint) -> Result<(), Decision> {
        use std::io::Write;
        let raw = serde_json::to_vec(checkpoint).map_err(|_| rejected("ANCHOR_UNAVAILABLE"))?;
        let tmp = self.path.with_extension("tmp");
        {
            let mut f = std::fs::File::create(&tmp).map_err(|_| rejected("ANCHOR_UNAVAILABLE"))?;
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                f.set_permissions(std::fs::Permissions::from_mode(0o600))
                    .map_err(|_| rejected("ANCHOR_UNAVAILABLE"))?;
            }
            f.write_all(&raw)
                .and_then(|_| f.sync_all())
                .map_err(|_| rejected("ANCHOR_UNAVAILABLE"))?;
        }
        std::fs::rename(&tmp, &self.path).map_err(|_| rejected("ANCHOR_UNAVAILABLE"))?;
        if let Some(parent) = self.path.parent() {
            if let Ok(dir) = std::fs::File::open(parent) {
                let _ = dir.sync_all();
            }
        }
        Ok(())
    }
}

/// Deterministic fault points, used by the simulation fault-injection tests
/// to prove write/commit/anchor failures never yield acceptance.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FaultPoint {
    AuditWrite,
    ReplayWrite,
    Commit,
    AnchorWrite,
}

#[derive(Clone)]
pub struct CoreConfig {
    /// Current process boot/session epoch (>= 1). Must never regress below
    /// the persisted high-water mark.
    pub current_epoch: u64,
    /// 0 = unbounded (not recommended); otherwise acceptance stops, fail
    /// closed, once the audit log holds this many records.
    pub max_audit_records: u64,
}

impl Default for CoreConfig {
    fn default() -> Self {
        CoreConfig {
            current_epoch: 1,
            max_audit_records: 0,
        }
    }
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
    put(&mut b, &e.epoch.to_be_bytes());
    put(&mut b, &e.sequence.to_be_bytes());
    put(&mut b, &e.issued_at_unix.to_be_bytes());
    put(&mut b, &e.expires_at_unix.to_be_bytes());
    b
}

pub fn compute_payload_hash(e: &Envelope) -> String {
    hex::encode(Sha256::digest(canonical_payload(e)))
}

/// Bounded envelope parse used by both `authorize` and the fuzz targets.
/// Never panics; rejects empty/oversized input before parsing.
pub fn parse_envelope(bytes: &[u8]) -> Result<Envelope, Decision> {
    if bytes.is_empty() || bytes.len() > MAX_ENVELOPE_BYTES {
        return Err(rejected("ENVELOPE_SIZE_REJECTED"));
    }
    serde_json::from_slice(bytes).map_err(|_| rejected("ENVELOPE_MALFORMED"))
}

/// Audit record hash, exposed for fuzz/property tests of audit records.
pub fn audit_record_hash(seq: i64, prev_hash: &str, payload_hash: &str, code: &str) -> String {
    let mut h = Sha256::new();
    h.update(AUDIT_DOMAIN);
    h.update(seq.to_be_bytes());
    h.update(prev_hash.as_bytes());
    h.update(payload_hash.as_bytes());
    h.update(code.as_bytes());
    hex::encode(h.finalize())
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
    epoch: u64,
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
        epoch,
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
        if audit_record_hash(seq, &prev, &ph, &code) != rh {
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
    config: CoreConfig,
    anchor: Option<Box<dyn AnchorStore>>,
    fault: Option<FaultPoint>,
}

impl Authorizer {
    pub fn open(
        db_path: &Path,
        trusted: BTreeMap<String, TrustedIssuer>,
    ) -> Result<Self, Decision> {
        Self::open_with_config(db_path, trusted, CoreConfig::default(), None)
    }

    pub fn open_with_config(
        db_path: &Path,
        trusted: BTreeMap<String, TrustedIssuer>,
        config: CoreConfig,
        anchor: Option<Box<dyn AnchorStore>>,
    ) -> Result<Self, Decision> {
        if config.current_epoch == 0 {
            return Err(rejected("EPOCH_REJECTED"));
        }
        let conn = Connection::open(db_path).map_err(|_| rejected("AUDIT_UNAVAILABLE"))?;
        conn.execute_batch(
            "PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;
             CREATE TABLE IF NOT EXISTS replay(
               scope TEXT PRIMARY KEY, last_sequence INTEGER NOT NULL);
             CREATE TABLE IF NOT EXISTS audit(
               seq INTEGER PRIMARY KEY, payload_hash TEXT NOT NULL,
               decision_code TEXT NOT NULL, prev_hash TEXT NOT NULL,
               record_hash TEXT NOT NULL);
             CREATE TABLE IF NOT EXISTS meta(
               key TEXT PRIMARY KEY, value INTEGER NOT NULL);",
        )
        .map_err(|_| rejected("AUDIT_UNAVAILABLE"))?;
        verify_audit_chain(&conn)?;
        // Monotonic epoch high-water mark: a later process may advance the
        // epoch, never regress it. The replay table is untouched, so the
        // persisted sequence survives epoch changes.
        let hw: Option<i64> = conn
            .query_row(
                "SELECT value FROM meta WHERE key='epoch_high_water'",
                [],
                |r| r.get(0),
            )
            .optional()
            .map_err(|_| rejected("AUDIT_UNAVAILABLE"))?;
        if let Some(hw) = hw {
            if (config.current_epoch as i64) < hw {
                return Err(rejected("EPOCH_REGRESSION"));
            }
        }
        if hw.map(|v| v as u64) != Some(config.current_epoch) {
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('epoch_high_water',?1)
                 ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                params![config.current_epoch as i64],
            )
            .map_err(|_| rejected("AUDIT_UNAVAILABLE"))?;
        }
        // Rollback detection against the external anchor (if configured).
        if let Some(store) = &anchor {
            let (tip_seq, tip_hash) = chain_tip(&conn)?;
            match store.load()? {
                None => {
                    if tip_seq != 0 {
                        return Err(rejected("ANCHOR_MISSING"));
                    }
                    store.store(&Checkpoint {
                        audit_seq: 0,
                        record_hash: tip_hash,
                    })?;
                }
                Some(cp) => {
                    if (tip_seq as u64) < cp.audit_seq
                        || ((tip_seq as u64) == cp.audit_seq && tip_hash != cp.record_hash)
                    {
                        return Err(rejected("ROLLBACK_DETECTED"));
                    }
                    if (tip_seq as u64) > cp.audit_seq {
                        // DB is ahead (crash between commit and anchor, or
                        // anchor lag): the anchored record itself must still
                        // be present verbatim, then re-anchor to the tip.
                        let at_anchor: Option<String> = conn
                            .query_row(
                                "SELECT record_hash FROM audit WHERE seq=?1",
                                params![cp.audit_seq as i64],
                                |r| r.get(0),
                            )
                            .optional()
                            .map_err(|_| rejected("AUDIT_UNAVAILABLE"))?;
                        if at_anchor.as_deref() != Some(cp.record_hash.as_str()) {
                            return Err(rejected("ROLLBACK_DETECTED"));
                        }
                        store.store(&Checkpoint {
                            audit_seq: tip_seq as u64,
                            record_hash: tip_hash,
                        })?;
                    }
                }
            }
        }
        Ok(Authorizer {
            conn,
            trusted,
            config,
            anchor,
            fault: None,
        })
    }

    /// Deterministic fault injection for simulation tests. Not a production
    /// control; it exists so failure paths can be exercised on demand.
    pub fn inject_fault_for_test(&mut self, fault: Option<FaultPoint>) {
        self.fault = fault;
    }

    pub fn current_epoch(&self) -> u64 {
        self.config.current_epoch
    }

    /// Verify an envelope (raw bytes, bounded) at `now_unix`. Acceptance is
    /// returned only after the replay+audit transaction commits; any audit,
    /// replay, signature, scope, or time failure is a rejection. This
    /// function does not panic on malformed input.
    pub fn authorize(&mut self, envelope_bytes: &[u8], now_unix: i64) -> Decision {
        let env: Envelope = match parse_envelope(envelope_bytes) {
            Ok(e) => e,
            Err(d) => return d,
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
        // Epoch binding: only the current process epoch is accepted.
        if env.epoch == 0 || env.epoch != self.config.current_epoch {
            return fail("EPOCH_REJECTED");
        }
        // Key rotation scaffolding: revoked / not-yet-valid / expired keys.
        if trusted.revoked {
            return fail("KEY_REVOKED");
        }
        if now_unix < trusted.valid_from_unix
            || (trusted.valid_until_unix != 0 && now_unix >= trusted.valid_until_unix)
        {
            return fail("KEY_VALIDITY_REJECTED");
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
        // Growth policy: fail closed *without growing the DB* once the audit
        // cap is reached. This bounds disk use; it cannot be used to wedge a
        // separate STOP path because this core is the only STOP authorizer
        // and the cap is an operator-set safety limit, not a shared queue.
        if self.config.max_audit_records > 0 && (tip_seq as u64) >= self.config.max_audit_records {
            return fail("AUDIT_CAPACITY_EXCEEDED");
        }
        let next_seq = tip_seq + 1;
        let record_hash = audit_record_hash(next_seq, &tip_hash, &env.payload_hash, code);
        if self.fault == Some(FaultPoint::AuditWrite)
            || tx
                .execute(
                    "INSERT INTO audit(seq,payload_hash,decision_code,prev_hash,record_hash) VALUES (?1,?2,?3,?4,?5)",
                    params![next_seq, env.payload_hash, code, tip_hash, record_hash],
                )
                .is_err()
        {
            return fail("AUDIT_WRITE_FAILED");
        }
        if !is_replay
            && (self.fault == Some(FaultPoint::ReplayWrite)
                || tx
                    .execute(
                        "INSERT INTO replay(scope,last_sequence) VALUES (?1,?2)
                     ON CONFLICT(scope) DO UPDATE SET last_sequence=excluded.last_sequence",
                        params![scope, env.sequence as i64],
                    )
                    .is_err())
        {
            return fail("REPLAY_WRITE_FAILED");
        }
        if self.fault == Some(FaultPoint::Commit) {
            drop(tx); // rolls back: nothing was committed
            return fail("AUDIT_COMMIT_FAILED");
        }
        if tx.commit().is_err() {
            return fail("AUDIT_COMMIT_FAILED");
        }
        // Anchor the new tip outside the DB before returning acceptance. If
        // anchoring fails we fail closed (the audit record is durable, so a
        // later open will re-anchor past it after verifying the chain).
        if let Some(store) = &self.anchor {
            let anchored = if self.fault == Some(FaultPoint::AnchorWrite) {
                Err(rejected("ANCHOR_UNAVAILABLE"))
            } else {
                store.store(&Checkpoint {
                    audit_seq: next_seq as u64,
                    record_hash: record_hash.clone(),
                })
            };
            if anchored.is_err() {
                let mut d = fail("ANCHOR_UPDATE_FAILED");
                d.audit_record = Some(next_seq as u64);
                return d;
            }
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
    fn trusted(sk: &SigningKey) -> BTreeMap<String, TrustedIssuer> {
        let mut t = BTreeMap::new();
        t.insert(
            "k1".into(),
            TrustedIssuer::new("issuer-1", "robot-1", "sim-1", sk.verifying_key()),
        );
        t
    }
    fn setup() -> (tempfile::TempDir, Authorizer, SigningKey) {
        let dir = tempfile::tempdir().unwrap();
        let sk = SigningKey::generate(&mut rand_core::OsRng);
        let auth = Authorizer::open(&dir.path().join("core.db"), trusted(&sk)).unwrap();
        (dir, auth, sk)
    }
    fn setup_cfg(
        dir: &tempfile::TempDir,
        sk: &SigningKey,
        cfg: CoreConfig,
        anchor: Option<Box<dyn AnchorStore>>,
    ) -> Authorizer {
        Authorizer::open_with_config(&dir.path().join("core.db"), trusted(sk), cfg, anchor).unwrap()
    }
    fn env(sk: &SigningKey, seq: u64, iat: i64, exp: i64) -> Vec<u8> {
        env_epoch(sk, 1, seq, iat, exp)
    }
    fn env_epoch(sk: &SigningKey, epoch: u64, seq: u64, iat: i64, exp: i64) -> Vec<u8> {
        serde_json::to_vec(&sign_envelope(
            sk, "k1", "issuer-1", "robot-1", "sim-1", "op-1", epoch, seq, iat, exp,
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
        assert!(Authorizer::open(&db, trusted(&sk)).is_err());
        let _ = dir;
    }

    #[test]
    fn fault_injection_never_accepts() {
        for (fault, code) in [
            (FaultPoint::AuditWrite, "AUDIT_WRITE_FAILED"),
            (FaultPoint::ReplayWrite, "REPLAY_WRITE_FAILED"),
            (FaultPoint::Commit, "AUDIT_COMMIT_FAILED"),
        ] {
            let (_d, mut a, sk) = setup();
            a.inject_fault_for_test(Some(fault));
            let d = a.authorize(&env(&sk, 1, 900, 1100), 1000);
            assert_eq!(d.outcome, "REJECTED", "{fault:?}");
            assert_eq!(d.code, code, "{fault:?}");
            // Clearing the fault: the same sequence must still be usable,
            // proving the failed attempt committed nothing.
            a.inject_fault_for_test(None);
            assert_eq!(
                a.authorize(&env(&sk, 1, 900, 1100), 1000).outcome,
                "ACCEPTED",
                "{fault:?}"
            );
        }
    }

    #[test]
    fn real_sqlite_write_failure_via_trigger_never_accepts() {
        let (_d, mut a, sk) = setup();
        a.conn
            .execute_batch(
                "CREATE TRIGGER fail_audit BEFORE INSERT ON audit
                 BEGIN SELECT RAISE(ABORT,'injected disk failure'); END;",
            )
            .unwrap();
        let d = a.authorize(&env(&sk, 1, 900, 1100), 1000);
        assert_eq!(d.outcome, "REJECTED");
        assert_eq!(d.code, "AUDIT_WRITE_FAILED");
        a.conn.execute_batch("DROP TRIGGER fail_audit").unwrap();
        assert_eq!(
            a.authorize(&env(&sk, 1, 900, 1100), 1000).outcome,
            "ACCEPTED"
        );
    }

    #[test]
    fn read_only_and_missing_db_paths_never_accept() {
        let dir = tempfile::tempdir().unwrap();
        let sk = SigningKey::generate(&mut rand_core::OsRng);
        // DB path inside a nonexistent directory: open must fail closed.
        assert!(Authorizer::open(&dir.path().join("nope/core.db"), trusted(&sk)).is_err());
        // DB path that is a directory: open must fail closed.
        assert!(Authorizer::open(dir.path(), trusted(&sk)).is_err());
    }

    #[test]
    fn anchor_detects_rollback_to_older_valid_db() {
        let dir = tempfile::tempdir().unwrap();
        let sk = SigningKey::generate(&mut rand_core::OsRng);
        let db = dir.path().join("core.db");
        let anchor_path = dir.path().join("anchor.json");
        let cfg = CoreConfig::default();
        let mut a = setup_cfg(
            &dir,
            &sk,
            cfg.clone(),
            Some(Box::new(FileAnchorStore::new(&anchor_path))),
        );
        assert_eq!(
            a.authorize(&env(&sk, 1, 900, 1100), 1000).outcome,
            "ACCEPTED"
        );
        drop(a);
        // Snapshot the valid DB after seq 1 (checkpoint WAL first via open/close is
        // implicit: rusqlite checkpoints on close of last connection).
        let backup = dir.path().join("backup.db");
        std::fs::copy(&db, &backup).unwrap();
        let mut a = setup_cfg(
            &dir,
            &sk,
            cfg.clone(),
            Some(Box::new(FileAnchorStore::new(&anchor_path))),
        );
        assert_eq!(
            a.authorize(&env(&sk, 2, 900, 1100), 1000).outcome,
            "ACCEPTED"
        );
        drop(a);
        // Roll back: replace DB with the older valid copy; anchor stays newer.
        std::fs::copy(&backup, &db).unwrap();
        for suffix in ["-wal", "-shm"] {
            let _ = std::fs::remove_file(format!("{}{suffix}", db.display()));
        }
        let err = Authorizer::open_with_config(
            &db,
            trusted(&sk),
            cfg,
            Some(Box::new(FileAnchorStore::new(&anchor_path))),
        )
        .err()
        .expect("rolled-back DB must be rejected");
        assert_eq!(err.code, "ROLLBACK_DETECTED");
        // Anchor file itself is strict-permission.
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mode = std::fs::metadata(&anchor_path)
                .unwrap()
                .permissions()
                .mode();
            assert_eq!(mode & 0o077, 0);
        }
    }

    #[test]
    fn anchor_fault_and_missing_anchor_never_accept() {
        let dir = tempfile::tempdir().unwrap();
        let sk = SigningKey::generate(&mut rand_core::OsRng);
        let anchor_path = dir.path().join("anchor.json");
        let mut a = setup_cfg(
            &dir,
            &sk,
            CoreConfig::default(),
            Some(Box::new(FileAnchorStore::new(&anchor_path))),
        );
        a.inject_fault_for_test(Some(FaultPoint::AnchorWrite));
        let d = a.authorize(&env(&sk, 1, 900, 1100), 1000);
        assert_eq!(d.code, "ANCHOR_UPDATE_FAILED");
        drop(a);
        // Deleting the anchor for a non-empty DB must fail closed.
        std::fs::remove_file(&anchor_path).unwrap();
        let err = Authorizer::open_with_config(
            &dir.path().join("core.db"),
            trusted(&sk),
            CoreConfig::default(),
            Some(Box::new(FileAnchorStore::new(&anchor_path))),
        )
        .err()
        .unwrap();
        assert_eq!(err.code, "ANCHOR_MISSING");
    }

    #[test]
    fn epoch_binding_rejects_old_epoch_and_preserves_sequence() {
        let dir = tempfile::tempdir().unwrap();
        let sk = SigningKey::generate(&mut rand_core::OsRng);
        let mut a = setup_cfg(
            &dir,
            &sk,
            CoreConfig {
                current_epoch: 1,
                max_audit_records: 0,
            },
            None,
        );
        assert_eq!(
            a.authorize(&env_epoch(&sk, 1, 1, 900, 1100), 1000).outcome,
            "ACCEPTED"
        );
        drop(a);
        let mut a = setup_cfg(
            &dir,
            &sk,
            CoreConfig {
                current_epoch: 2,
                max_audit_records: 0,
            },
            None,
        );
        // Old-epoch envelope rejected even with a fresh sequence.
        assert_eq!(
            a.authorize(&env_epoch(&sk, 1, 2, 900, 1100), 1000).code,
            "EPOCH_REJECTED"
        );
        // Persisted sequence survived: seq 1 in the new epoch is still replay.
        assert_eq!(
            a.authorize(&env_epoch(&sk, 2, 1, 900, 1100), 1000).code,
            "REPLAY_REJECTED"
        );
        assert_eq!(
            a.authorize(&env_epoch(&sk, 2, 2, 900, 1100), 1000).outcome,
            "ACCEPTED"
        );
        drop(a);
        // Epoch regression at open fails closed.
        let err = Authorizer::open_with_config(
            &dir.path().join("core.db"),
            trusted(&sk),
            CoreConfig {
                current_epoch: 1,
                max_audit_records: 0,
            },
            None,
        )
        .err()
        .unwrap();
        assert_eq!(err.code, "EPOCH_REGRESSION");
    }

    #[test]
    fn revoked_and_out_of_window_keys_rejected_rotation_accepted() {
        let dir = tempfile::tempdir().unwrap();
        let sk_old = SigningKey::generate(&mut rand_core::OsRng);
        let sk_new = SigningKey::generate(&mut rand_core::OsRng);
        let mut t = BTreeMap::new();
        let mut old = TrustedIssuer::new("issuer-1", "robot-1", "sim-1", sk_old.verifying_key());
        old.revoked = true;
        t.insert("k-old".into(), old);
        let mut new = TrustedIssuer::new("issuer-1", "robot-1", "sim-1", sk_new.verifying_key());
        new.valid_from_unix = 900;
        new.valid_until_unix = 1200;
        t.insert("k-new".into(), new);
        let mut a = Authorizer::open(&dir.path().join("core.db"), t).unwrap();
        let old_env = serde_json::to_vec(&sign_envelope(
            &sk_old, "k-old", "issuer-1", "robot-1", "sim-1", "op-1", 1, 1, 900, 1100,
        ))
        .unwrap();
        assert_eq!(a.authorize(&old_env, 1000).code, "KEY_REVOKED");
        let new_env = |seq, iat, exp| {
            serde_json::to_vec(&sign_envelope(
                &sk_new, "k-new", "issuer-1", "robot-1", "sim-1", "op-1", 1, seq, iat, exp,
            ))
            .unwrap()
        };
        assert_eq!(
            a.authorize(&new_env(1, 900, 1100), 1000).outcome,
            "ACCEPTED"
        );
        assert_eq!(
            a.authorize(&new_env(2, 900, 1100), 1300).code,
            "KEY_VALIDITY_REJECTED"
        );
    }

    #[test]
    fn audit_capacity_fails_closed_without_growth() {
        let dir = tempfile::tempdir().unwrap();
        let sk = SigningKey::generate(&mut rand_core::OsRng);
        let mut a = setup_cfg(
            &dir,
            &sk,
            CoreConfig {
                current_epoch: 1,
                max_audit_records: 1,
            },
            None,
        );
        assert_eq!(
            a.authorize(&env(&sk, 1, 900, 1100), 1000).outcome,
            "ACCEPTED"
        );
        let d = a.authorize(&env(&sk, 2, 900, 1100), 1000);
        assert_eq!(d.code, "AUDIT_CAPACITY_EXCEEDED");
        let n: i64 = a
            .conn
            .query_row("SELECT COUNT(*) FROM audit", [], |r| r.get(0))
            .unwrap();
        assert_eq!(n, 1, "capacity rejection must not grow the audit log");
    }
    proptest::proptest! {
        #[test]
        fn arbitrary_bytes_never_panic_and_never_accept(bytes in proptest::collection::vec(proptest::prelude::any::<u8>(), 0..9000)) {
            let (_d, mut a, _sk) = setup();
            let d = a.authorize(&bytes, 1000);
            proptest::prop_assert_eq!(d.outcome.as_str(), "REJECTED");
        }
        #[test]
        fn audit_hash_is_deterministic_and_sensitive(seq in -1000i64..1000, code in "[A-Z_]{1,32}") {
            let h1 = audit_record_hash(seq, GENESIS_HASH, &"a".repeat(64), &code);
            let h2 = audit_record_hash(seq, GENESIS_HASH, &"a".repeat(64), &code);
            proptest::prop_assert_eq!(&h1, &h2);
            proptest::prop_assert_eq!(h1.len(), 64);
            let h3 = audit_record_hash(seq + 1, GENESIS_HASH, &"a".repeat(64), &code);
            proptest::prop_assert_ne!(h1, h3);
        }
        #[test]
        fn mutated_valid_envelope_never_accepts_without_resigning(
            seq in 1u64..1000, flip in 0usize..20,
        ) {
            let (_d, mut a, sk) = setup();
            let mut v: serde_json::Value = serde_json::from_slice(&env(&sk, seq, 900, 1100)).unwrap();
            match flip % 4 {
                0 => { v["sequence"] = (seq + 1000).into(); }
                1 => { v["subject"] = "mallory".into(); }
                2 => { v["expires_at_unix"] = 1050.into(); }
                _ => { v["signature"] = "00".repeat(64).into(); }
            }
            let d = a.authorize(&serde_json::to_vec(&v).unwrap(), 1000);
            proptest::prop_assert_eq!(d.outcome.as_str(), "REJECTED");
        }
    }
}
