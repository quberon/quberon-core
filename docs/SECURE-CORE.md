# Rust Secure Core — Increment 1

> **SIMULATION ONLY — STOP AUTHORIZATION ONLY — NO PHYSICAL CONTROL — NOT A SAFETY-RATED E-STOP**

This document describes a minimal, auditable Rust security boundary added in
Increment 1. It does **not** claim that the system is secure, certified,
audited, or state-of-the-art. Words such as "secure core" are a component
name, not an assurance claim.

## What was implemented

- Rust workspace: library crate `crates/quberon-secure-core`
  (`#![forbid(unsafe_code)]`) and subprocess CLI
  `apps/quberon-secure-core-cli`.
- Versioned (v1) deterministic signed envelope using **Ed25519**
  (`ed25519-dalek`, a maintained RustCrypto-ecosystem library; no
  cryptography was invented here):
  - Domain separation: distinct domain strings for payload hashing,
    signing, and audit hashing.
  - Closed action enum: only `STOP` is representable. There is no reset,
    unlatch, task, or motion variant; unknown actions and unknown fields
    are rejected (`serde(deny_unknown_fields)`).
  - Exact scope pinning per key id (`kid`): issuer, `robot_id`, and
    `simulation_id` must all match the trusted entry exactly.
  - `payload_hash` = SHA-256 over a length-prefixed canonical payload;
    signature verified over the domain-separated hash.
  - Time checks: `expires > issued`, validity window ≤ 300 s,
    `issued` at most 30 s in the future (skew), `expires > now`.
- Durable SQLite store (`rusqlite`, bundled SQLite, WAL,
  `synchronous=FULL`):
  - Per-scope monotonic replay sequence; a sequence ≤ the last accepted
    sequence for that scope is rejected.
  - Hash-chained audit records (`SHA-256(prev_hash || seq || payload_hash
    || decision_code)` under an audit domain). The full chain is
    re-verified before any new acceptance; a chain failure rejects.
  - Acceptance is returned **only after** the combined replay+audit
    transaction commits. Write/commit failures reject.
- Stable machine-readable decisions (JSON) with a closed code set
  (`ACCEPTED_SIMULATION_STOP_AUTHORIZATION`, `REPLAY_REJECTED`,
  `EXPIRED`, `SCOPE_MISMATCH`, …). A decision never asserts a physical
  state: `observed_state` is always `"UNKNOWN"` and
  `physical_state_claim` is always `"NONE"`. An acceptance means only
  "a simulation STOP may be requested".
- Boundary choice: **subprocess**, not FFI. The Python client
  (`integrations/secure_core.py`) talks to the CLI over bounded stdin /
  stdout JSON. The CLI wraps the core call in `catch_unwind`; no panic
  crosses the boundary as a crash contract — failures become
  `REJECTED`/`INTERNAL_ERROR` decisions, and any Python-side error raises
  `SecureCoreError`.
- Integration: the single `execute_stop` convergence path in
  `app/main.py` (used by the button, voice, gesture, and intervention
  endpoints) requires a Rust `ACCEPTED` decision **before**
  `SimulatedRobotAdapter.stop()` is invoked. On any core error:
  HTTP 503, latch retained (`stop_latched=True`), observed state
  `UNKNOWN`, an audit event is recorded, and the adapter is **not**
  invoked (covered by `tests/test_secure_core.py`).

## Key custody

No secret is stored in Git. The Ed25519 signing seed is either supplied
via the `QUBERON_SECURE_CORE_SIGNING_KEY_HEX` environment variable
(external secrets management) or generated ephemerally per app instance
by the Rust CLI and held only in process memory (simulation default).
Signing itself happens inside the Rust CLI, not in Python code.

## Threat model (Increment 1 scope)

Assets: integrity of the simulation STOP authorization decision, replay
resistance, and tamper evidence of the audit log. Adversaries considered:

| Threat | Mitigation implemented | Residual risk |
|---|---|---|
| Forged STOP envelope | Ed25519 verification (maintained library), payload hash, domain separation | Key compromise defeats this; no HSM in this increment |
| Replay of a valid envelope | Durable per-scope monotonic sequence in SQLite | An attacker who can roll back the whole DB file can roll back the sequence; chain verification detects record edits, not full-file rollback |
| Scope confusion (other robot/simulation/issuer) | Exact trusted-entry match on all three fields | Trusted-config distribution is out of scope here |
| Smuggled actions (reset/motion fields) | Closed enum + `deny_unknown_fields`; core cannot represent them | The Python app still has separate simulation reset/task endpoints outside this core — they are simulation-only and unchanged |
| Audit tampering | Hash chain re-verified before acceptance and at open | No external anchoring (e.g. transparency log); planned |
| Malformed / oversized input, panics | Bounded input (8 KiB envelope, 32 KiB CLI stdin), `catch_unwind`, property test over arbitrary bytes | Denial of service by request flooding is not addressed |
| Clock manipulation | Validity/skew windows bound the damage to ≤300 s envelopes | Host clock trust remains an assumption |
| Python-side bypass | `execute_stop` is the only adapter-stop path and now gates on Rust acceptance; test asserts adapter not invoked on core error | Other processes with DB/adapter access are out of scope |

Explicitly **out of scope**: physical robots, certified e-stop behavior,
real-time guarantees, multi-instance deployment (the app's documented
single-instance limitation still applies), denial of service, side
channels, and compromise of the host OS, the signing key, or the
trusted-config file.

## Evidence / benchmark matrix

| Control | Status | Evidence |
|---|---|---|
| Ed25519 signed, domain-separated, scope-pinned STOP-only envelope | Implemented + tested | Rust unit tests (`crates/quberon-secure-core`), CLI integration tests (`apps/quberon-secure-core-cli/tests/cli.rs`) |
| Expiry / max-validity / future-skew checks | Implemented + tested | Unit tests: expired, future, >300 s window |
| Durable replay sequence (SQLite) | Implemented + tested | Replay rejected in unit + CLI tests |
| Hash-chained audit; chain failure rejects | Implemented + tested | Tamper test edits a record; reopen/authorize rejects |
| Acceptance only after transaction commit | Implemented (code path) | Commit/write failure branches return rejections; fault-injection test of disk failure not yet written |
| No panic across boundary; bounded input | Implemented + tested | Property test (arbitrary bytes never accepted/panic), oversized-input CLI test |
| `execute_stop` requires Rust acceptance before adapter | Implemented + tested | `tests/test_secure_core.py` counts adapter invocations |
| `cargo audit` | Run in this increment | 98 crate dependencies scanned against RustSec advisory DB; no vulnerabilities reported (see session report) |
| `cargo deny check` | Run in this increment | advisories/bans/licenses/sources all ok (duplicate `syn` warning only) |
| SBOM generation | Implemented | `scripts/sbom.sh` (CycloneDX JSON from `cargo metadata`), 98 components |
| Signed releases / provenance attestation | Planned | Not in this increment; see SLSA reference below |
| External security review / penetration test | External review required | No external review has occurred; nothing here is "audited" |
| Fuzzing beyond property tests | Planned | `proptest` only in this increment |
| Hardware-backed key custody (HSM/TPM), external audit anchoring | Planned | Not implemented |

## Standards and primary-source references

Cited for design context only; listing a standard is not a claim of
compliance with it.

- NIST SP 800-82 Rev. 3, *Guide to OT Security* —
  https://csrc.nist.gov/pubs/sp/800/82/r3/final
- NIST SP 800-207, *Zero Trust Architecture* —
  https://csrc.nist.gov/pubs/sp/800/207/final
- NIST SP 800-218, *Secure Software Development Framework (SSDF) v1.1* —
  https://csrc.nist.gov/pubs/sp/800/218/final
- ROS 2 DDS-Security / SROS2 documentation —
  https://docs.ros.org/en/rolling/Concepts/Intermediate/About-Security.html
  and https://github.com/ros2/sros2
- The Update Framework (TUF) — https://theupdateframework.io/
  specification: https://theupdateframework.github.io/specification/latest/
- Uptane (automotive update security) — https://uptane.org/
- RustSec advisory database — https://rustsec.org/ /
  https://github.com/RustSec/advisory-db
- SLSA (Supply-chain Levels for Software Artifacts) — https://slsa.dev/
- EU Cyber Resilience Act, Regulation (EU) 2024/2847 —
  https://eur-lex.europa.eu/eli/reg/2024/2847/oj
- EU Machinery Regulation, Regulation (EU) 2023/1230 —
  https://eur-lex.europa.eu/eli/reg/2023/1230/oj

Relevance, briefly: SP 800-82r3 and the Machinery Regulation frame why a
software STOP request is not a safety function; SP 800-207 motivates
per-request, scope-bound authorization rather than network trust;
SP 800-218/SLSA/RustSec motivate the SSDF-style supply-chain controls
(`Cargo.lock`, audit/deny, SBOM); TUF/Uptane are the reference design if
signed, rollback-resistant distribution of trusted configs or updates is
added later; ROS 2 DDS-Security/SROS2 is the relevant model if this
system ever interoperates with ROS 2 (it does not today).

## Limitations and blockers

- Single-process simulation demo; ephemeral keys by default. This is a
  development boundary, not a deployed security product.
- No external review, certification, or audit has been performed.
- The core DB and the Python app DB are separate SQLite files; crash
  consistency *across* the two is not transactional (the core commits
  before the app acts, so a crash in between yields an authorized STOP
  with no app event — fail-safe direction, but not atomic).
- Not deployed to the Pi; no physical hardware was accessed.
