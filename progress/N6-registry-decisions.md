# N6-registry-decisions progress (Wave 4)

Node: Wave 4 N6 (registry decision packet), Tier 1.
Branch: wave4/n6
Scope owned: research/humanoids/** plus this file
(progress/N6-registry-decisions.md). progress/n7-requests.md was NOT
appended: not needed — the human-decision route is the signed packet to
N0 for checks.md assembly (graph.md), not a new node request.
Gate: one human decision packet for all 25 candidates; official sources
for every recommendation; no edit to checks.md; no decision made; no
promotion. universe_size_claim stays null.

Inputs read: research/humanoids/registry/{candidates,sources,
provenance-claims}.jsonl, research/humanoids/registry/index.json,
progress/N4-registry-dedup.md (Wave 3 N4 proposals), graph.md,
checks.md (read only; its two N4 rows remain unresolved).

## 1. Deterministic check first (raw output)

Command: python3 research/humanoids/tools/validate_registry.py

```json
{
  "ok": true,
  "errors": [],
  "counts": {
    "company": 25,
    "source": 26,
    "dataset": 0,
    "api_surface": 0,
    "compliance_assessment": 0,
    "provenance_claim": 38
  },
  "verified_companies": 0
}
```

Command: python3 -m pytest tests/test_humanoid_registry.py -q
Raw result: 8 passed. Full suite: make test (after make setup) = 80 passed.

Deterministic packet counts (generated from the registry files):
candidates=25, official sources=26, provenance claims=38,
recommendations=25, by code: RETAIN-UNVERIFIED=15,
PARTIAL-LEGAL-ENTITY=2, PARTIAL-BRAND-OF-ENTITY=2,
ALIAS-THEN-PARTIAL=1, PARENT-CONTEXT-ONLY=1, OUT-OF-SCOPE=2,
DEFER-NO-ACCESS=1, DEFER-METADATA-ONLY=1. Total 15+2+2+1+1+2+1+1=25.
index.json unchanged: candidate_count=25, verified_count=0,
universe_size_claim=null.

## 2. Node report

Created research/humanoids/DECISION-PACKET.md — the single human
decision packet for all 25 candidates. For each candidate it gives:
official source URL(s) with source_type/access/evidence_strength,
publisher_claim and retrieval_note; entity-vs-brand analysis quoted
from provenance-claims.jsonl (a brand/publisher name is not a legal
entity; legal names mentioned only in a source publisher_claim are
flagged as unadopted "publisher-claim leads"); the exact yes/no
decision the human must answer; a recommended answer with a decision
code and confidence; and the unchanged current state
(candidate_unverified, canonical_name=null).

One-sitting format: section 4 is a 25-row batch sheet (Approve /
Reject / Defer per candidate) plus name/signature/date lines. Signing
only authorises N0 to record checks.md rows; it changes no registry
record by itself.

Proposed checks.md outcome rows: packet section 5 lists 25 per-
candidate rows plus the two existing N4 requirement rows, all with
verdict "unresolved pending signature", for N0 to insert only after
signing. checks.md was NOT edited in this node.

No promotion or decision was applied: no registry .jsonl or index.json
file was modified; verified_count remains 0.

Files changed:
- research/humanoids/DECISION-PACKET.md (new; packet only)
- progress/N6-registry-decisions.md (this file)

Attempts: attempt 1 — packet generated deterministically from registry
JSONL, validated (25 sections, counts sum to 25). Within the
3-attempt gate limit; no gate failure encountered.

## 3. Model confidence (last)

High that no record was promoted, counts are exact, and every
recommendation cites an official source already in the registry —
all deterministically checked above. Medium overall for the
entity-vs-brand recommendations themselves: they rest on the manual
official-page reviews recorded in Wave 3 N4 / sources.jsonl, Tesla is
explicitly unassessed (not_accessed) and LimX is metadata-only, and a
human must still answer every exact decision in the packet.
