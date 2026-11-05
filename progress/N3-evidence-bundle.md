# Progress - Wave4 N3 evidence bundle

Owner: Wave4 N3 alone. Scope honoured: only new
crates/quberon-evidence-bundle/**, new tools/quberon-verify/**, and this
file. No existing crate, root workspace, Cargo.toml/Cargo.lock, or MSRV
modified (crate declares its own standalone [workspace]).

## Verdict: PASS (attempt 1 of 3, with in-attempt bug fixes)

Two ZIP writer bugs (local-header method offset, central-directory
field count) and two Python bugs (length-prefix helper return, Ed25519
point decoding) were found by the deterministic checks, fixed, and all
checks re-run green. No gate was weakened.

## Format (crates/quberon-evidence-bundle/SPEC.md)
Single portable .qeb = deterministic ZIP v1 tying: actual Copper
original/replay unified logs + task-output bytes + comparison.txt;
secure-core v1 Ed25519 STOP envelope + ACCEPTED decision; secure-core
SQLite audit rows (hash-chained, secure-core domains/formulas mirrored
exactly); complete environment.json; manifest.json with SHA-256+size
for every payload and explicit bindings; attestation.json (Ed25519
over domain-separated SHA-256 of manifest bytes, bundled key).

## Real simulated STOP fixture (generated, not hand-written)
Built by crates/quberon-evidence-bundle/scripts/build-fixture.py using
the REAL secure-core CLI (generate-keypair -> sign -> authorize against
a temp SQLite DB; audit rows dumped from that DB) and the ACTUAL
committed Wave3 N3 Copper evidence. Decision:
ACCEPTED_SIMULATION_STOP_AUTHORIZATION, sequence=1, audit_record=1,
observed_state=UNKNOWN, physical_state_claim=NONE.
Bindings: envelope_payload_hash=
dd4f642ebb783854f6239dff1d6a2ede6f50bb06aba58f2464fc3e84f77b067e
audit_tip=a0b157b1121a584de0eae8049869ec4874532d8592f3a41c99c6d0957165f48d
Copper hashes match progress/N3-copper.md exactly:
original/replay task outputs sha256=249509dc...361d (39 bytes, identical),
original/replay Copper logs sha256=f5ac0065...1be5 (identical).

Fixtures (sha256):
  922c174fd7bdc8bbacb011f3b1df208dd086c31cbb86d5e7f02498f2db99e737  simulated-stop.qeb (37 KB)
  decd35dd9f4901336715984ebdbfd5ad3e7ade8122cbfc796699ab10315b6bfa  tampered-replay.qeb (one flipped byte in replay-task-outputs.bin)

## Deterministic evidence (raw)
- python3 tools/quberon-verify/quberon-verify simulated-stop.qeb:
  verdict PASS_LIMITED_CLAIMS, exit 0, checks: zip_container_read,
  format_version_1, claim_boundary_simulation_only,
  manifest_file_hashes_match, environment_manifest_complete,
  envelope_payload_hash_recomputed,
  envelope_signature_valid_for_bundled_key,
  decision_accepted_simulation_stop, audit_chain_hash_linked,
  copper_replay_task_outputs_byte_identical, copper_logs_byte_identical,
  stop_recorded_in_copper_comparison,
  bundle_attestation_valid_for_bundled_key, claims_lists_exact; errors []
- Same verifier on tampered-replay.qeb: verdict REJECT, exit 1, errors
  exactly [HASH_MISMATCH:copper/replay-task-outputs.bin,
  REPLAY_TASK_OUTPUTS_MISMATCH, BINDING_REPLAY_HASH_MISMATCH].
- Rust validator on simulated-stop.qeb: PASS_LIMITED_CLAIMS, exit 0
  (independent implementation parity with the Python verifier).
- cargo test (standalone crate): 5 passed (good fixture, tampered,
  signature tamper -> SIGNATURE_INVALID, audit tamper ->
  AUDIT_CHAIN_INVALID, garbage).
- python pytest tools/quberon-verify/tests/test_verify.py: 7 passed
  (plus env-incomplete -> ENV_FIELD_MISSING:git_commit, physical claim
  -> DECISION_PHYSICAL_CLAIM_VIOLATION, non-bundle).
- cargo clippy --all-targets -- -D warnings: clean; cargo fmt --check: clean.
- Root workspace untouched and green: cargo test --workspace: 14+3 passed.
- make test locally: .venv absent in this worktree (make: .venv/bin/python:
  No such file or directory), same limitation recorded by Wave3 N3;
  root Python suite evidence is PR CI. The new Python verifier tests are
  collected by that CI pytest run and need only stdlib.

## Claims (precise)
Supported on PASS only: bundle internal SHA-256 integrity, audit
hash-chain linkage, envelope signature valid for the bundled key,
secure-core ACCEPTED simulation-STOP decision, Copper replay task
outputs and logs byte-identical, STOP recorded.
Unsupported (printed on every report, never upgraded): physical stop /
safety-rated e-stop, certification/regulatory compliance, signer
authority beyond the bundled self-asserted ephemeral simulated key,
production/HSM/TPM custody, hardware/Pi execution, latency/real-time,
external audit, authenticity against an attacker who rebuilds and
re-signs a bundle with their own key. No certification or physical
claim is made anywhere.

## Third-party use
Only bundle + tools/quberon-verify/quberon-verify (Python stdlib only,
offline) are needed. Rust builder/validator is the second implementation.
