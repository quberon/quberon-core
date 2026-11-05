# Rust Secure Core — Increment 2

> **SIMULATION ONLY — STOP AUTHORIZATION ONLY — NO PHYSICAL CONTROL — NOT A SAFETY-RATED E-STOP**

This document describes a minimal, auditable Rust security boundary through
Increment 2. It does **not** claim that the system is secure, certified,
audited, or state-of-the-art. Words such as "secure core" are a component
name, not an assurance claim.

Increment 2 adds, only where listed as tested in the evidence matrix below:
monotonic boot/session epoch binding (persisted replay sequence is not reset
on epoch advance; epoch regression is rejected), key-validity/revocation
scaffolding for rotation, an externally-anchored audit checkpoint with
rollback detection, deterministic fault injection plus a real SQLite write-
failure test, audit-capacity fail-closed behaviour, bounded fuzz targets,
stricter Python client key-custody modes (production provisions no client without an
external key; ephemeral keys only in explicit development mode), and a
STOP-isolated priority rate limiter.

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
  `REJECTED`/`INTERNAL_ERROR` decisions, and Python-side boundary failures
  raise `SecureCoreError` subclasses: `SecureCoreUnavailable` (no decision
  obtained) or `SecureCoreRejected` (reachable core did not accept).
- Integration: the single `execute_stop` convergence path in
  `app/main.py` (used by the button, voice, gesture, and intervention
  endpoints) requests a Rust `ACCEPTED` decision **before**
  `SimulatedRobotAdapter.stop()` is invoked as a signed stop. If the
  core is unavailable, the authenticated simulation STOP still executes
  UNSIGNED (adapter invoked, latch retained, audit-marked
  `UNSIGNED/core_unavailable`). On a reachable core rejection:
  HTTP 503, latch retained (`stop_latched=True`), observed state
  `UNKNOWN`, an audit event is recorded, and the adapter is **not**
  invoked (covered by `tests/test_secure_core.py`).

## Which direction does this fail?

For safety engineers: this system fails in different directions
depending on whether the operation moves toward or away from motion,
and the distinction between *unavailable* and *rejected* is load-bearing.

- STOP (motion-inhibiting): fails **open with respect to optional
  attestation, closed with respect to authentication**. If the Rust
  core binary is missing or cannot run, no signed decision exists, but
  an authenticated, CSRF-checked simulation STOP still invokes
  `SimulatedRobotAdapter.stop()`, returns HTTP 200, and retains the
  latch. The application audit event and the response mark this
  explicitly: audit `UNSIGNED/core_unavailable`, response
  `secure_core.status = "unavailable"` with `decision`, `sequence`,
  and `audit_record` all null. This is **not** a signed authorization
  and must never be reported as one. Rationale: an attestation outage
  must not block an operator from requesting a stop.
- Reachable core rejection: fails **closed in both directions**. If
  the core runs and returns a non-ACCEPTED decision (replay, expiry,
  scope mismatch, ...), or returns malformed/oversized output, STOP
  does **not** invoke the adapter: HTTP 503, latch retained, observed
  state `UNKNOWN`, response `secure_core.status = "rejected"`.
  "The core said no" is not the same as "the core was not there".
- Reset / unlatch / any motion-permitting operation: fails **closed
  whenever core availability requirements are not met**. Clearing the
  latch (`simulation-reset`) and starting a simulated task require a
  present secure-core client/binary; when the core is unavailable
  they return HTTP 503, the latch is retained, and the adapter is not
  invoked for reset/task. There is no unsigned reset and no unsigned
  motion. The Rust core's closed enum can only authorize STOP, so
  availability — not a signed motion decision — is the gate here, and
  the latch itself also independently blocks tasks.
- Accepted path: only a Rust `ACCEPTED` decision yields
  `secure_core.status = "accepted"` with its `decision`, `sequence`,
  and `audit_record` in the response and an `allowed` audit event.

This is a simulation-only, STOP-authorization-only component. It is
not a safety-rated e-stop, and the unsigned degraded STOP above is a
deliberate simulation availability choice, not a physical-safety claim.

## Key custody

No secret is stored in Git. Increment 2 removes the permissive default:

- `QUBERON_SECURE_CORE_MODE=production`: provisions no client unless an external
  signing key is supplied via `QUBERON_SECURE_CORE_SIGNING_KEY_FILE`
  (strict `0600` permissions enforced) or
  `QUBERON_SECURE_CORE_SIGNING_KEY_HEX` (injected by an external secrets
  manager), together with a verifying key and an explicit core DB path.
  An audit anchor path should also be configured.
- `QUBERON_SECURE_CORE_MODE=development`: explicit opt-in only; ephemeral
  per-instance keys generated by the Rust CLI and held only in process
  memory are allowed.
- No mode set / unknown mode: no client is provisioned; the app treats
  that as core unavailable (see "Which direction does this fail?").

Signing itself happens inside the Rust CLI, not in Python code. Trusted
entries carry `valid_from_unix` / `valid_until_unix` / `revoked` scaffolding
so a rotated-out or revoked key is rejected; this is configuration-level
rotation support, not HSM/TPM custody.

## Threat model (Increment 2 scope)

Assets: integrity of the simulation STOP authorization decision, replay
resistance, and tamper evidence of the audit log. Adversaries considered:

| Threat | Mitigation implemented | Residual risk |
|---|---|---|
| Forged STOP envelope | Ed25519 verification (maintained library), payload hash, domain separation | Key compromise defeats this; no HSM in this increment |
| Replay of a valid envelope | Durable per-scope monotonic sequence in SQLite; epoch binding (Increment 2): old-epoch envelopes rejected, epoch regression rejected, and the persisted sequence is **not** reset when the epoch advances | An attacker who can roll back the whole DB file can roll back the sequence unless an external anchor is configured (see anchor row); chain verification detects record edits, not full-file rollback |
| Audit DB rollback | External audit checkpoint (`FileAnchorStore`: atomic tmp+fsync+rename, `0600` on Unix): DB tip behind the anchor, or a mismatched anchored record, is rejected as `ROLLBACK_DETECTED`; a missing anchor for a non-empty DB fails closed | **Same-filesystem DB+anchor rollback remains undetectable**: an attacker who can replace *both* the DB and the anchor file (e.g. restoring a whole-directory snapshot on one filesystem) defeats the local file anchor. Production rollback resistance requires an anchor outside the attacker's control — hardware (TPM/HSM/secure element) or a remote transparency log / remote witness — which is **not implemented** |
| Key compromise / stale keys | Validity window + `revoked` flag on trusted entries; rotated (new) key accepted, revoked/out-of-window key rejected | Key compromise of a currently-valid key defeats this; no HSM/TPM in this increment; trusted-config distribution is out of scope |
| Scope confusion (other robot/simulation/issuer) | Exact trusted-entry match on all three fields | Trusted-config distribution is out of scope here |
| Smuggled actions (reset/motion fields) | Closed enum + `deny_unknown_fields`; core cannot represent them | The Python app still has separate simulation reset/task endpoints outside this core — they are simulation-only and unchanged |
| Audit tampering | Hash chain re-verified before acceptance and at open; Increment 2 anchor checkpoint (above) | No remote/hardware anchoring; same-filesystem DB+anchor rollback undetectable (see above) |
| Disk / write failure | Deterministic fault injection (`FaultPoint::{AuditWrite,ReplayWrite,Commit,AnchorWrite}`) never yields acceptance; a real SQLite trigger (`RAISE(ABORT)`) write failure never accepts; missing/unwritable DB paths never accept; audit-capacity cap fails closed without growing the log | **Synthetic limits**: fault injection and the SQLite trigger simulate write/commit failure at the SQL layer. They are **not** a real disk-full (`ENOSPC`), read-only-media, filesystem-corruption, or power-loss test. No claim is made for behaviour on physically full/failing media |
| Malformed / oversized input, panics | Bounded input (8 KiB envelope, 32 KiB CLI stdin), `catch_unwind`, property test over arbitrary bytes; Python client validates subject (1–128 printable ASCII) and uses a STOP-isolated priority token-bucket limiter (flooding non-critical work cannot consume STOP tokens; STOP itself is still bounded) | Flooding the STOP bucket itself, or flooding below the Python client (network/OS), is not addressed; limiter is per-process |
| Clock manipulation | Validity/skew windows bound the damage to ≤300 s envelopes | Host clock trust remains an assumption |
| Python-side bypass | `execute_stop` is the only adapter-stop path; it requests Rust acceptance, executes UNSIGNED (audit-marked) if the core is unavailable, and does not invoke the adapter on a reachable core rejection; reset/task require core availability | An unsigned STOP has no signed attestation by design; other processes with DB/adapter access are out of scope |

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
| Acceptance only after transaction commit | Implemented + tested (Increment 2) | Fault-injection tests (`FaultPoint` AuditWrite/ReplayWrite/Commit/AnchorWrite) and a real SQLite `RAISE(ABORT)` trigger test never yield acceptance; missing/unwritable DB paths never accept. Synthetic SQL-layer faults only — not a real disk-full/read-only-media test (see threat model) |
| Epoch binding; sequence survives epoch advance | Implemented + tested (Increment 2) | Unit tests: old-epoch rejected, epoch regression rejected at open, seq 1 replay-rejected in new epoch, new-epoch acceptance works; CLI test covers epoch mismatch |
| Key validity window / revocation / rotation | Implemented + tested (Increment 2) | Unit test: revoked and out-of-window keys rejected, rotated new key accepted. Scaffolding only — no HSM |
| External audit anchor / rollback detection | Implemented + tested (Increment 2) | Unit tests: rollback to an older valid DB copy detected, missing anchor for non-empty DB fails closed, anchor-write fault never accepts; CLI rollback test. Local file anchor only — same-filesystem DB+anchor rollback undetectable |
| No panic across boundary; bounded input | Implemented + tested | Property test (arbitrary bytes never accepted/panic), oversized-input CLI test |
| `execute_stop` attestation asymmetry (accepted / unavailable-unsigned / rejected) | Implemented + tested | `tests/test_secure_core.py` counts adapter invocations for all three statuses, incl. `test_stop_executes_without_secure_core_but_reset_does_not` and `test_stop_rejected_by_secure_core_does_not_invoke_adapter`: unavailable -> adapter invoked, HTTP 200, UNSIGNED/core_unavailable, latch retained; reachable rejected -> no adapter, latch retained, UNKNOWN, HTTP 503 |
| Mutated valid envelope never accepted without re-signing | Implemented + tested (Increment 2) | Rust property/unit test mutating a valid envelope; Python subject validation (1–128 printable ASCII) |
| Audit capacity fails closed | Implemented + tested (Increment 2) | Unit test: at cap, rejection and audit log does not grow |
| Production key-custody modes (no permissive default) | Implemented + tested (Increment 2) | Python tests (`tests/test_secure_core.py`): no-mode and production-without-key provision no client (app treats as unavailable), key file with permissive mode rejected, development ephemeral allowed only on explicit opt-in |
| STOP-isolated priority rate limiting | Implemented + tested (Increment 2) | Python unit test with injectable clock: exhausting OTHER bucket does not consume STOP tokens |
| `cargo audit` | Run in Increment 2 (2026-11-05, local) | cargo-audit 0.22.2: 98 crate dependencies scanned, no vulnerabilities reported at run time. A point-in-time scan, not an audit |
| `cargo deny check` | Run in Increment 2 (2026-11-05, local) | cargo-deny 0.20.2: advisories/bans/licenses/sources ok. Licenses tightened to those actually in the graph; the deliberate `syn` 2/3 duplicate is explicitly skipped with rationale in `deny.toml` (both majors are load-bearing upstream), any new duplicate fails |
| SBOM generation | Implemented + verified in Increment 2 | `scripts/sbom.sh` (CycloneDX 1.5 JSON from `cargo metadata`): verified locally 2026-11-05, 98 components, valid JSON; CI uploads it as an artifact. Unsigned — not SLSA provenance |
| Signed releases / provenance attestation | Planned | Not implemented; no SLSA claim |
| External security review / penetration test | External review required | No external review has occurred; nothing here is "audited" |
| Fuzzing beyond property tests | Targets written; **NOT RUN locally in Increment 2** | `fuzz/` cargo-fuzz targets (`envelope_parse`, `audit_record`) + `scripts/fuzz-smoke.sh`. Local run 2026-11-05: `cargo-fuzz` unavailable on this toolchain, script exited **77 = not run** (never reported as success). CI runs the same script and surfaces exit 77 as a warning; `proptest` remains the executable evidence on stable |
| Hardware-backed key custody (HSM/TPM), remote/hardware audit anchoring | Planned | Not implemented; local file anchor is simulation-grade only |

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

Current primary-source notes (checked 2026-11-05; design context only,
no compliance claim):

- TUF (https://theupdateframework.io/, spec at
  https://theupdateframework.github.io/specification/latest/) — the
  reference model for compromise-resilient, rollback-resistant update
  metadata (root/targets/snapshot/timestamp roles). The Increment 2 local
  anchor borrows only the *idea* of an external checkpoint; it is not TUF.
- Uptane (https://uptane.org/) — TUF adaptation for automotive ECUs
  (director/image repositories, per-ECU manifests). Relevant only as a
  design reference if trusted-config distribution is ever built; no OTA
  mechanism exists here.
- SLSA (https://slsa.dev/) — supply-chain integrity levels and provenance
  concepts. The unsigned CycloneDX SBOM here is an inventory artifact,
  **not** SLSA provenance and no SLSA level is claimed.
- NIST SP 800-218 SSDF v1.1
  (https://csrc.nist.gov/pubs/sp/800/218/final) — practices such as
  dependency management and vulnerability response motivate
  `cargo audit` / `cargo deny` / SBOM in CI; SSDF conformance is not claimed.
- RustSec (https://rustsec.org/, https://github.com/RustSec/advisory-db) —
  the advisory database behind `cargo audit`; a clean scan is a
  point-in-time result against that database, not a security audit.

## Limitations and blockers

- Single-process simulation demo; ephemeral keys only in explicit
  development mode, external keys required in production mode. This is a
  development boundary, not a deployed security product.
- Disk/write-failure evidence is synthetic (fault injection + SQLite
  trigger + missing/unwritable paths). Real disk-full, read-only-media,
  filesystem-corruption and power-loss behaviour is untested.
- The local audit anchor is a file: **same-filesystem DB+anchor rollback
  remains undetectable** without external/hardware anchoring (remote
  transparency log, hardware counter, TPM/HSM) — none is implemented.
- Fuzz targets are written but were not run locally (exit 77, cargo-fuzz
  unavailable); proptest is the executable evidence.
- No external review, certification, or audit has been performed.
- The core DB and the Python app DB are separate SQLite files; crash
  consistency *across* the two is not transactional (the core commits
  before the app acts, so a crash in between yields an authorized STOP
  with no app event — fail-safe direction, but not atomic).
- Not deployed to the Pi; no physical hardware was accessed.
