# quberon-evidence-bundle v1 — format spec

SIMULATION ONLY. NO PHYSICAL CONTROL. NOT A SAFETY-RATED E-STOP.
NO CERTIFICATION CLAIM.

## Artifact
A `.qeb` file is a single portable ZIP (entries sorted, DOS timestamp
1980-01-01, deflate). It is the *only* artifact a third party needs,
together with `tools/quberon-verify/quberon-verify`.

Entries:
  manifest.json                     format/version/bundle_id, scope
                                    (kid, issuer, robot_id, simulation_id),
                                    files[] {path,sha256,size} for every
                                    payload entry, bindings{}, claims{}
  attestation.json                  Ed25519 sig over
                                    "QUBERON-EVIDENCE-BUNDLE/ATTEST/v1\0" ||
                                    SHA-256(exact manifest.json bytes),
                                    by the bundled key
  environment.json                  complete environment manifest (below)
  copper/original_0.copper          actual Copper unified log (record)
  copper/replay_0.copper            actual Copper unified log (replay)
  copper/original-task-outputs.bin  actual recorded task outputs
  copper/replay-task-outputs.bin    actual replayed task outputs
  copper/comparison.txt             actual record/replay comparison
  secure-core/envelope.json         secure-core v1 signed STOP envelope
  secure-core/decision.json         secure-core decision (ACCEPTED_*)
  secure-core/audit.json            secure-core SQLite audit rows, in seq
                                    order: {seq,payload_hash,decision_code,
                                    prev_hash,record_hash}
  secure-core/verifying-key.json    {kid, verifying_key_hex, key_origin}

## Algorithms (mirroring secure-core v1 exactly)
- payload_hash: SHA-256 over length-prefixed (u64 BE length + bytes)
  canonical fields with domain "QUBERON-SECURE-CORE/PAYLOAD/v1\0";
  integer fields as BE (version u32, epoch/sequence u64, times i64);
  action is the literal STOP.
- signature: Ed25519 over "QUBERON-SECURE-CORE/SIGN/v1\0" || raw
  payload_hash bytes.
- audit record_hash: hex SHA-256("QUBERON-SECURE-CORE/AUDIT/v1\0" ||
  seq i64 BE || prev_hash ASCII || payload_hash ASCII || code ASCII),
  genesis prev_hash = 64 zeroes, seq starts at 1 with no gaps.

## Environment completeness (all non-empty strings required)
arch, cargo_version, copper_config_sha256, copper_cu29_version,
created_utc, git_commit (40 lowercase hex), os, python_version,
rustc_version, secure_core_cli_sha256, secure_core_source_sha256.
Extra descriptive fields are allowed in environment.json only.

## Verification (offline; chain, signatures, replay, manifest)
A verifier MUST reject (verdict REJECT, precise error codes) on:
unknown format/version, unsafe/duplicate/unlisted/missing entries,
any size/SHA-256 mismatch, incomplete environment, payload_hash
mismatch, invalid envelope or attestation signature, non-ACCEPTED or
physically-claiming decision, scope/sequence/kid mismatch, broken
audit chain or audit-tip/envelope binding mismatch, original != replay
task outputs or Copper logs, no STOP in comparison.txt, inexact
claims lists. See SUPPORTED/UNSUPPORTED in the crate source; the
verifier prints both lists verbatim on every run.

## Claims
PASS means only `PASS_LIMITED_CLAIMS` with the supported list in the
report. The unsupported list (physical STOP, certification, signer
authority beyond the bundled self-asserted key, HSM/TPM custody,
hardware execution, latency, external audit, authenticity against an
attacker who rebuilds and re-signs with their own key) is never
upgraded by a passing bundle.

## Regenerating the fixture
  cargo build -p quberon-secure-core-cli   # root workspace, unchanged
  cargo build --manifest-path crates/quberon-evidence-bundle/Cargo.toml
  python3 crates/quberon-evidence-bundle/scripts/build-fixture.py \
    --repo . --secure-cli target/debug/quberon-secure-core-cli \
    --bundle-bin crates/quberon-evidence-bundle/target/debug/quberon-evidence-bundle \
    --out tools/quberon-verify/tests/fixtures/simulated-stop.qeb \
    --tampered tools/quberon-verify/tests/fixtures/tampered-replay.qeb
The fixture key is generated per build by the secure-core CLI for this
simulation; it is not a production key and its seed is not in the bundle.
