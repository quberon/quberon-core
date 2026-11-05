# Humanoid research registry (Frontier Phase 1)

Purpose: a provenance-first, machine-readable starting point for researching
humanoid companies, sources, datasets, API/SDK surfaces and compliance —
without fabricating facts.

What this is NOT: a verified directory, a census, or a claim about how many
humanoid companies exist. All 25 seed records in registry/candidates.jsonl are
candidate_unverified. A seed name may turn out to be a company, brand, product,
lab, duplicate, or out of scope; research decides, this scaffold does not.

Layout:
  schemas/    JSON Schema 2020-12: company, source, dataset, api-surface,
              compliance-assessment, provenance-claim
  capability-tuples/  Wave 5 F6 (QIP R10): capability-tuple schema +
              78 manufacturer capability tuples (observed/inferred/
              unknown/not_found; no QIP mapping claimed, no promotion).
              See capability-tuples/README.md.
  registry/   candidates.jsonl (25 seeds) + empty source/dataset/api/
              compliance/claim registries + index.json
  cards/      dataset-card and model-card templates
  examples/   one clearly synthetic example record (fictional, do not cite)
  tools/      validate_registry.py (stdlib-only, no network)

Hard rules: do not scrape against terms or robots.txt; do not download
copyrighted video; do not invent APIs, endpoints, licences or headquarters;
do not use this research to deploy physical control. STOP/reset boundaries in
integrations/ and app/ are untouched by this workstream.

Validate: python3 research/humanoids/tools/validate_registry.py
