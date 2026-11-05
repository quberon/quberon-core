Evidence-bundle conformance vectors (Wave5 F2)
===============================================

SIMULATION ONLY. NO PHYSICAL CONTROL. NOT A SAFETY-RATED E-STOP.
NO CERTIFICATION CLAIM. A PASS here is PASS_LIMITED_CLAIMS only.

Scope: new files only in this directory plus progress/F2-bundle-vectors.md.
No existing crate, verifier, or fixture is modified.

What this is
------------
Cross-implementation test vectors for quberon-evidence-bundle v1
(crates/quberon-evidence-bundle/SPEC.md, Wave4 N3), intended for a third
implementer who does not want to trust either existing implementation:

  vectors.json          machine-readable vectors + expected verdicts (17 vectors).
                        Regenerate deterministically (stdlib only):
                          python3 generate_vectors.py
  bundle_check.py       small independent stdlib-only Python checker, written
                        from SPEC.md. Validates a .qeb and/or consumes
                        vectors.json against a bundle fixture. Also contains
                        deterministic tamper and rebuild-and-resign helpers
                        used to produce the tamper/limitation vectors.
  test_bundle_conformance.py
                        pytest suite collected by the root `make test` / CI
                        pytest run. Cross-checks verdict (and, for the clean
                        fixture, the exact check list) against the pre-existing
                        tools/quberon-verify Python verifier.

Categories (one or more vectors each; ids in vectors.json)
----------------------------------------------------------
  canonical_bytes               EB-CANON-01   exact length-prefixed preimage hex,
                                              payload_hash, attestation-message hash
  hash_chain                    EB-CHAIN-01   synthetic 3-record chain + fixture tip
  signature                     EB-SIG-01     valid Ed25519; wrong-domain / bit-flip fail
  replay_binding                EB-REPLAY-01  original==replay bytes and manifest bindings
                                              (including copper-log bindings, which the
                                              vector layer checks even though the v1
                                              bundle validators only bind task outputs)
  manifest_completeness         EB-MANIFEST-01 required payload files + env fields
  tamper_classes                EB-TAMPER-01..11  replay flip, copper flip, unsigned
                                              envelope mutation, signature flip, audit
                                              break, env-field removal, deleted payload,
                                              unlisted entry, physical-claim boundary,
                                              unsupported version, non-ZIP garbage
  rebuild_and_resign_limitation EB-RESIGN-01  see below

Run it
------
  python3 bundle_check.py --vectors vectors.json ../tools/quberon-verify/tests/fixtures/simulated-stop.qeb
  python3 bundle_check.py ../tools/quberon-verify/tests/fixtures/simulated-stop.qeb
  python3 -m pytest test_bundle_conformance.py -q     # from this directory

Rebuild-and-resign limitation (read this before trusting any PASS)
------------------------------------------------------------------
EB-RESIGN-01 is a limitation disclosure, not a security claim. An attacker
who flips/replaces payload bytes, recomputes every manifest hash and
binding, swaps in their own verifying key, and re-signs the envelope and
attestation produces a bundle that every bundled-key verifier (this one,
tools/quberon-verify, and the Rust validator alike, by design) reports as
PASS_LIMITED_CLAIMS. Bundled-key verification proves internal consistency
only; it proves no signer authority. Mitigation is an external trust
anchor: bundle_check.py --pinned-key-hex <expected hex> (and/or
--pinned-kid) rejects such a rebuild with PINNED_KEY_MISMATCH. The pytest
suite asserts both halves and asserts the pre-existing verifier also
passes the rebuilt bundle internally, so the limitation cannot be
mistaken for a bug in one checker.

Expected verdicts are machine-readable in vectors.json ("expected" per
vector: verdict, errors_contains, limitation flag). No vector upgrades
the unsupported claims listed in SPEC.md / bundle_check.UNSUPPORTED.
