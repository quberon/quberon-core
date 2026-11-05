# Progress - Wave5 F2 evidence-bundle conformance vectors

Owner: Wave5 F2 alone. Scope honoured: only new evidence-bundle-conformance/**
and this file. No existing crate, verifier, fixture, or workspace file modified.
Base: 35ee2aef6f7a2fcf17e51de40678aee97ba0b350 (origin/main at start; gh pr list: none open relevant).

## Verdict: PASS (attempt 1 of 3)

## What was built
- evidence-bundle-conformance/vectors.json: 17 machine-readable vectors with
  per-vector "expected" {verdict, errors_contains, limitation}. Fixture pinned
  by sha256 922c174fd7bdc8bbacb011f3b1df208dd086c31cbb86d5e7f02498f2db99e737
  (the committed Wave4 N3 simulated-stop.qeb, unchanged).
  Categories: canonical_bytes (EB-CANON-01, exact length-prefixed preimage hex +
  payload_hash dd4f642e...67e + attestation-message hash), hash_chain
  (EB-CHAIN-01, synthetic 3-record chain + fixture tip a0b157b1...5f48d),
  signature (EB-SIG-01, valid / wrong-domain / bit-flip), replay_binding
  (EB-REPLAY-01, byte identity + manifest bindings incl. copper-log bindings),
  manifest_completeness (EB-MANIFEST-01), tamper_classes (EB-TAMPER-01..11),
  rebuild_and_resign_limitation (EB-RESIGN-01).
- evidence-bundle-conformance/bundle_check.py: small independent stdlib-only
  Python checker written from crates/quberon-evidence-bundle/SPEC.md (does not
  import the Rust crate or tools/quberon-verify). Validates a .qeb, consumes
  vectors.json against a bundle fixture, supports an external trust anchor
  (--pinned-key-hex / --pinned-kid -> PINNED_KEY_MISMATCH), and contains the
  deterministic tamper + rebuild-and-resign generators used by the tests.
- evidence-bundle-conformance/generate_vectors.py: deterministic regeneration
  of vectors.json from the fixture (re-run verified, no diff drift in hashes).
- evidence-bundle-conformance/test_bundle_conformance.py: pytest, collected by
  root make test / CI. Cross-implementation parity: clean fixture verdict AND
  exact check list equal to tools/quberon-verify; committed tampered fixture
  REJECT in both; every tamper class REJECT in both (verdict parity, error-code
  subset asserted in this checker).
- evidence-bundle-conformance/README.md: usage + limitation disclosure.

## Rebuild-and-resign limitation (explicit, not a claim)
A rebuilt bundle (payload fixed up, all manifest hashes/bindings recomputed,
own key bundled, envelope + attestation re-signed) is PASS_LIMITED_CLAIMS in
this checker AND in the pre-existing verifier (asserted in tests) — bundled-key
verification proves internal consistency only, never signer authority. With the
original key pinned externally it is REJECT / PINNED_KEY_MISMATCH. This matches
SPEC.md's unsupported list; nothing here upgrades it.

## Deterministic evidence (raw)
- python3 evidence-bundle-conformance/generate_vectors.py:
  "wrote vectors.json: 17 vectors fixture_sha256=922c174f...e737"
- python3 evidence-bundle-conformance/bundle_check.py --vectors
  evidence-bundle-conformance/vectors.json
  tools/quberon-verify/tests/fixtures/simulated-stop.qeb:
  exit 0, base_verdict PASS_LIMITED_CLAIMS, all_ok true, 17/17 results ok.
  Tamper errors e.g. EB-TAMPER-01 exactly [HASH_MISMATCH:copper/replay-task-outputs.bin,
  REPLAY_TASK_OUTPUTS_MISMATCH, BINDING_REPLAY_HASH_MISMATCH]; EB-RESIGN-01
  pinned errors [PINNED_KEY_MISMATCH].
- .venv/bin/python -m pytest evidence-bundle-conformance/test_bundle_conformance.py -q:
  17 passed.
- Full gate: python3.11 -m venv .venv && pip install -r requirements.txt && make test:
  148 passed, 13 skipped (17 of those tests are the new suite above; no
  existing test modified).

## Claims
Supported on PASS only: the SPEC.md supported list (internal SHA-256 integrity,
audit linkage, envelope signature for the bundled key, ACCEPTED simulation STOP,
Copper replay byte-identity, STOP recorded). Unsupported, never upgraded:
physical stop / safety-rated e-stop, certification/regulatory compliance,
signer authority beyond the bundled self-asserted key, HSM/TPM custody,
hardware/Pi execution, latency, external audit, authenticity against a
rebuild-and-resign attacker. No certification or physical claim anywhere.
