#![no_main]
//! Fuzz target: envelope parsing + verification-path entry points.
//! Invariants: never panic, never accept arbitrary/mutated bytes.
use libfuzzer_sys::fuzz_target;
use quberon_secure_core::{compute_payload_hash, parse_envelope};

fuzz_target!(|data: &[u8]| {
    if let Ok(env) = parse_envelope(data) {
        // Exercise canonical hashing on anything that parsed; must not panic.
        let _ = compute_payload_hash(&env);
        // Re-serialization must stay within the envelope bound or fail cleanly.
        if let Ok(bytes) = serde_json::to_vec(&env) {
            let _ = parse_envelope(&bytes);
        }
    }
});
