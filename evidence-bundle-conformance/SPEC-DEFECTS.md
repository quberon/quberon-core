# SPEC defects found by the ind-3 cross-verifier

SIMULATION ONLY. NO PHYSICAL CONTROL. NOT A SAFETY-RATED E-STOP.
NO CERTIFICATION CLAIM.

Method: independent_verify.py was written from SPEC.md without reading
the Rust crate source. It was then compared, from outside, with
tools/quberon-verify on both committed fixtures and on a deterministic
mutation corpus (test_cross_verifier.py). Every disagreement below is
recorded here as a defect in the specification (or, where noted, in an
implementation's conformance to it), not silently coded around and not
reported as a passing test of the ambiguous behaviour.

SD-1 Supported-claims list is not in SPEC.md
  SPEC.md says a PASS is PASS_LIMITED_CLAIMS "with the supported list in
  the report" and says inexact claims lists must be rejected, but never
  enumerates the supported strings. The unsupported list is enumerated.
  A second implementer can only obtain the supported strings from the
  fixture manifest's claims.supported_if_valid. Independent verifier
  uses those observable strings and says so in its docstring.

SD-2 Exact error codes and check names are not in SPEC.md
  SPEC.md requires "precise error codes" but defines none. All error
  and check strings (FORMAT_VERSION_UNSUPPORTED, AUDIT_CHAIN_INVALID,
  zip_container_read, ...) are observable only from an existing
  verifier's report or from fixture data. Exact-report parity is
  therefore parity with an implementation, not with the text of SPEC.md.

SD-3 Envelope and decision JSON schemas are only partly in SPEC.md
  The canonical payload_hash field order and integer widths are stated,
  which fixes kid/issuer/robot_id/simulation_id/subject/action/epoch/
  sequence/issued_at_unix/expires_at_unix. The decision literals
  (outcome ACCEPTED, code ACCEPTED_SIMULATION_STOP_AUTHORIZATION,
  observed_state UNKNOWN, physical_state_claim NONE), the
  verifying-key fields, and the attestation fields are not stated;
  they are observable only in the fixture entries.

SD-4 comparison.txt acceptance tokens are not in SPEC.md
  SPEC.md requires rejection when there is "no STOP in comparison.txt".
  The reference behaviour (and this verifier, for parity) requires all
  of command=STOP, authorized=true and byte_identical=true. A file
  containing only the word STOP would satisfy the text and fail both
  implementations.

SD-5 Attestation fields kid/algorithm/domain are unchecked
  Mutating attestation.json kid or domain (leaving manifest_sha256 and
  signature intact) still yields PASS_LIMITED_CLAIMS in
  tools/quberon-verify, and in this verifier for parity, because
  attestation.json is not a manifest-listed file and only its
  manifest_sha256 + signature are verified. SPEC.md does not state
  whether those descriptive fields must match the envelope kid or the
  ATTEST domain constant. Documented, not "fixed" unilaterally:
  tightening only one verifier would create a verdict disagreement
  that SPEC.md cannot adjudicate. See
  test_attestation_descriptive_fields_are_a_documented_gap.

SD-6 Audit-tip/envelope binding wording vs observable behaviour
  SPEC.md requires rejection on "audit-tip/envelope binding mismatch".
  The observable reference behaviour binds bindings.audit_tip_hash to
  the last record's record_hash and separately requires the FIRST
  audit record's payload_hash to equal the envelope payload_hash. With
  the single-record fixture these coincide; with several records the
  text and the behaviour describe different checks. This verifier
  follows the observable behaviour for parity and records the gap.

SD-7 Several manifest bindings are not independently verified
  bindings.sequence, bindings.decision_code and the two copper-log
  bindings are not checked by tools/quberon-verify. Mutating any of
  them is still REJECT, but only indirectly, because the manifest no
  longer matches the attestation signature. SPEC.md says bindings{}
  exist but does not enumerate which bindings a verifier MUST check.

SD-8 Reference verifier crashes on some malformed JSON types
  Observed 2026-11-06 with tools/quberon-verify on mutated fixtures:
  audit.json as a JSON object (AttributeError: 'str' object has no
  attribute 'get'), manifest files as a string (same AttributeError),
  and environment git_commit as an integer (TypeError: object of type
  'int' has no len()). SPEC.md says a verifier MUST reject on missing/
  malformed entries; it does not permit an unhandled exception, and it
  does not specify the error code. independent_verify.py REJECTs all
  three (AUDIT_MALFORMED / MANIFEST_FILES_MALFORMED /
  ENV_FIELD_MISSING:git_commit + ENV_GIT_COMMIT_MALFORMED respectively,
  alongside the integrity errors). These are verdict disagreements (REJECT vs crash) caused
  by an underspecified type domain: test_malformed_types_reject_not_crash
  asserts only this verifier's REJECT; the crash observation lives here
  so a future fix to the reference can close SD-8 without a test here
  having enshrined the crash as expected behaviour.

SD-9 Rebuild-and-resign limitation (from SPEC.md itself)
  A bundle rebuilt and re-signed with an attacker's own bundled key is
  internally consistent and passes bundled-key verification. SPEC.md
  lists authenticity against that attacker as unsupported, so a PASS
  must never be read as signer authority. The F2 suite already asserts
  this against bundle_check.py; nothing in this node upgrades it.

Non-defects confirmed by the corpus: on both committed fixtures the
two verifiers agree exactly on verdict, exit code, checks, errors,
supported_claims and unsupported_claims; on every non-SD-8 mutation in
the corpus they agree on verdict, and on the curated subset they agree
on the exact error list. See test_cross_verifier.py.
