# Registry — how records move

Status vocabulary (never skip a step):
candidate_unverified -> partially_verified -> verified | rejected | duplicate | out_of_scope

Rules:
1. One JSON object per line in each `.jsonl` file. IDs are stable: cand- / src- / ds- / api- / cmp- / claim-.
2. A record may move to partially_verified/verified ONLY with evidence_source_ids
   pointing at source records, plus reviewed_by + reviewed_at. The validator
   enforces this (fabrication guard).
3. canonical_name stays null while candidate_unverified.
4. Empty `.jsonl` files (sources, datasets, api-surfaces, compliance,
   provenance-claims) mean "none researched yet" — not "none exist".
5. Run: python3 research/humanoids/tools/validate_registry.py
6. index.json must keep universe_size_claim=null until a defensible census
   methodology with evidence exists. Candidate count != universe size.
