#![no_main]
//! Fuzz target: audit-record hashing / checkpoint parsing.
//! Invariants: deterministic 64-hex output, never panic on arbitrary input.
use libfuzzer_sys::fuzz_target;
use quberon_secure_core::{audit_record_hash, Checkpoint};

fuzz_target!(|data: &[u8]| {
    let s = String::from_utf8_lossy(data);
    let h = audit_record_hash(data.len() as i64, &s, &s, &s);
    assert_eq!(h.len(), 64);
    assert!(h.bytes().all(|c| c.is_ascii_hexdigit()));
    let _ = serde_json::from_slice::<Checkpoint>(data);
});
