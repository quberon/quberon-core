NODE: reg-decision-packet-refresh
TIER: 1
BRANCH: node/reg-decision-packet-refresh
COMMITS: see final message / git log on this branch (report updated in a follow-up commit after clean-clone tests)
STATUS: pending final clean-clone verification (updated below)

CHANGED:
- research/humanoids/DECISION-PACKET.md (refresh only: refreshed-by header, new section 3A capability-tuple context table for all 25 candidates, section 6 verbatim current validator output + current test counts + refresh cross-check, section 7 no-QIP-claim bullet)
- progress/reg-decision-packet.md (this report, owned path)
- progress/reg-decision-packet-refresh.md (same report, path named in the task report instruction)
No registry .jsonl, index.json, checks.md, graph.md, or any other file changed. No promotion.

WHAT THE REFRESH DID:
- Re-derived all 25 section-3 entries from registry/candidates.jsonl,
  sources.jsonl and provenance-claims.jsonl: every source ID and claim
  ID in each candidate record, with its official https URL, is present
  in the matching packet section. Result: errors=[] (raw checker
  output reproduced in EVIDENCE).
- Recommendation codes unchanged and re-counted from section 4:
  {'ALIAS-THEN-PARTIAL': 1, 'DEFER-METADATA-ONLY': 1, 'DEFER-NO-ACCESS': 1,
  'OUT-OF-SCOPE': 2, 'PARENT-CONTEXT-ONLY': 1, 'PARTIAL-BRAND-OF-ENTITY': 2,
  'PARTIAL-LEGAL-ENTITY': 2, 'RETAIN-UNVERIFIED': 15}, total 25.
- Added section 3A: Wave 5 F6 capability tuples (78) per candidate,
  explicitly marked NOT entity evidence, mapping_claimed=false for all.
- Replaced stale section 6 validator JSON (pre-F6, no capability_tuple
  fields) and stale test counts ("8 passed / 80 passed") with verbatim
  current output.

EVIDENCE:
- command: python3 research/humanoids/tools/validate_registry.py
  exit: 0
  raw output (verbatim, also in DECISION-PACKET.md section 6):
{
  "ok": true,
  "errors": [],
  "counts": {
    "company": 25,
    "source": 26,
    "dataset": 0,
    "api_surface": 0,
    "compliance_assessment": 0,
    "provenance_claim": 38,
    "capability_tuple": 78
  },
  "capability_tuple_epistemic_counts": {
    "inferred": 1,
    "not_found": 65,
    "observed": 6,
    "unknown": 6
  },
  "verified_companies": 0
}
- command: python3 <scratch>/check_packet.py . (deterministic re-derivation checker, scratch only, not a repo file)
  raw summary: batch rows 25, counts as above; caps total 78
  {'inferred': 1, 'not_found': 65, 'observed': 6, 'unknown': 6};
  mapping_claimed any False; cap candidates covered 25; ERRORS [];
  universe_size_claim None.
- toolchain/host/UTC: Darwin Quberon1.local 24.3.0 arm64;
  system python3 3.9.6 for validator; .venv python for pytest;
  rustc 1.99.1 / cargo at /opt/homebrew/bin (with-Rust mode);
  observed 2026-11-06T13:37:09Z (system date) for pre-refresh check.
- raw output path: this file (verbatim outputs above) and
  research/humanoids/DECISION-PACKET.md section 6.

TESTS (both modes):
- with Rust (this worktree, after make setup): make test = 211 passed.
  Humanoid subset: .venv/bin/python -m pytest
  tests/test_humanoid_registry.py research/humanoids/tests/test_capability_tuples.py -q = 12 passed.
- without Rust: PENDING clean-clone run, updated in follow-up commit.
- fail-direction: full suite includes
  tests/test_humanoid_registry.py::test_verified_without_evidence_is_rejected
  (validator rejects verified-without-evidence); result covered by make test above.

STILL NOT TRUE:
- No candidate is verified or partially_verified; all 25 remain
  candidate_unverified, canonical_name=null, evidence_source_ids=[].
- universe_size_claim is still null; 25 is a seed count, not a census.
- No human has signed DECISION-PACKET.md section 4; no decision in
  it has been applied; checks.md was not edited by this node.
- Tesla Optimus official page is still not_accessed and LimX Dynamics
  is still metadata_only in the recorded sources.
- Capability tuples make no QIP mapping, certification,
  physical-safety, latency, or regulatory-compliance claim, and no
  such claim is supported by this repository.
- The section 3 recommendations are still Wave 4 N6 recommendations
  re-validated against unchanged registry data, not new research
  into the companies' current (2026) status.

NEEDS A HUMAN DECISION:
- Sign or reject/defer each of the 25 rows on DECISION-PACKET.md
  section 4 (A/R/D per candidate), then hand the signed packet to
  N0 for checks.md rows per packet section 5. Until then every
  recommendation remains an unsigned proposal and no registry
  field may change.
