# N4-registry-dedup progress

Node: N4-registry-dedup
Branch: wave3/n4
Scope owned: research/humanoids/** plus this file (progress/N4-registry-dedup.md); tests/test_humanoid_registry.py updated only as the registry validation harness.
Gate (graph.md): Every claim-* has an official source URL; no status promotion without a human row in checks.md.

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
Raw result: 8 passed. Full suite (make test, python3.11 venv): 55 passed, 11 skipped.

Validator additions (deterministic, stdlib only, no network):
- every provenance claim references at least one source whose source_type is official_site/official_docs and whose URL is https;
- a claim with status supported_by_primary_source must reference a primary_official source that was actually accessed (access.method != not_accessed);
- candidate -> source, candidate -> claim, claim -> source, and source -> supported-claim references all resolve;
- duplicate source URLs, duplicate normalized candidate names, and an official source URL shared by two candidates are errors;
- every candidate has at least one dedup/scope claim and one official source;
- index.json discovery_progress counts must match the actual file counts.

Integrity fixes applied to the resumed partial work:
- claim-tesla-optimus-entity-classification downgraded to candidate_unverified: its official Tesla URL was recorded not_accessed, so no assertion is supported by it.
- Legal-entity names not stated in the reviewed official source record were removed from entity-classification claims (Booster, DEEP Robotics, EngineAI, Robot Era, Sanctuary AI, Kepler, Leju, Unitree, X-humanoid, XPENG, LimX Dynamics); those claims now assert only the brand/product relationship the source record supports, with an explicit no-legal-entity-conclusion note.

## 2. Node report

All 25 candidates were classified for human review. Proposals only:
- duplicate candidate-record pairs proposed: 0. Deterministic comparison of stable IDs, normalized seed names, and official source URLs found no pair; MagicLab's two domains and Agility/Agility Robotics naming are aliases inside single records (claim-magiclab-site-alias, claim-agility-name-alias, claim-registry-25-candidate-dedup-proposal), not duplicate candidate records.
- out-of-scope proposed (2, not applied): cand-physicalintelligence (robot AI lab/company, no claimed humanoid product) and cand-romela (UCLA university laboratory). Their verification.status remains candidate_unverified.
- retain_candidate_pending_human_review: the other 23.
- No verification promotion: every candidate remains candidate_unverified with canonical_name=null and evidence_source_ids=[]; checks.md contains no human decision row for N4, so no status, canonical name, scope, duplicate, or out-of-scope value was applied.
- universe_size_claim: null (index.json unchanged on this point); candidate_count=25, verified_count=0.

Per-candidate proposals (classification; proposed disposition; entity claim; official source URL):

| candidate | classification proposal | proposed disposition | claim | official source URL |
|---|---|---|---|---|
| cand-leju-robot | brand_or_company_name | retain_candidate_pending_human_review | claim-leju-robot-entity-classification | https://www.lejurobot.com/en |
| cand-kepler | brand_or_company_name | retain_candidate_pending_human_review | claim-kepler-entity-classification | https://www.gotokepler.com/about |
| cand-tesla-optimus | unassessed_pending_official_access | retain_candidate_pending_human_review | claim-tesla-optimus-entity-classification | https://www.tesla.com/AI |
| cand-sanctuary-ai | brand_or_company_name | retain_candidate_pending_human_review | claim-sanctuary-ai-entity-classification | https://sanctuary.ai/about-us/ |
| cand-fourier | brand_or_company_name | retain_candidate_pending_human_review | claim-fourier-entity-classification | https://support-old.fftai.com/en/docs/GR-X-Humanoid-Robot/GR1/GR-1_Introduction/ |
| cand-boston-dynamics | company_or_brand_name | retain_candidate_pending_human_review | claim-boston-dynamics-entity-classification | https://bostondynamics.com/products/atlas/ |
| cand-x-humanoid | brand_or_company_name | retain_candidate_pending_human_review | claim-x-humanoid-entity-classification | https://www.x-humanoid.com/en |
| cand-unitree | brand_or_company_name | retain_candidate_pending_human_review | claim-unitree-entity-classification | https://www.unitree.com/ |
| cand-engineai | brand_or_company_name | retain_candidate_pending_human_review | claim-engineai-entity-classification | https://en.engineai.com.cn/about-us |
| cand-robot-era | brand_or_company_name | retain_candidate_pending_human_review | claim-robot-era-entity-classification | https://www.robotera.com/en/ |
| cand-pndbotics | brand_or_company_name | retain_candidate_pending_human_review | claim-pndbotics-entity-classification | https://www.pndbotics.com/ |
| cand-xpeng | brand_or_company_name | retain_candidate_pending_human_review | claim-xpeng-entity-classification | https://www.xpeng.com/news/019a4d1549039eaa99ad9c9a33a00016 |
| cand-ubtech | brand_or_company_name | retain_candidate_pending_human_review | claim-ubtech-entity-classification | https://www.ubtrobot.com/en/humanoid/products/walker-s2 |
| cand-deep-robotics | brand_or_company_name | retain_candidate_pending_human_review | claim-deep-robotics-entity-classification | https://www.deeprobotics.cn/en/index/dr02.html |
| cand-physicalintelligence | robot_ai_lab_or_company | out_of_scope | claim-physicalintelligence-entity-classification | https://www.physicalintelligence.company/ |
| cand-limx-dynamics | brand_or_company_name | retain_candidate_pending_human_review | claim-limx-dynamics-entity-classification | https://www.limxdynamics.com/en/products/luna/spec |
| cand-tencent | parent_company_with_lab_and_platform | retain_candidate_pending_human_review | claim-tencent-entity-classification | https://tairos.tencent.com/en-US |
| cand-pudu-robotics | brand_or_company_name | retain_candidate_pending_human_review | claim-pudu-robotics-entity-classification | https://www.pudurobotics.com/en/products/d9 |
| cand-booster-robotics | brand_or_company_name | retain_candidate_pending_human_review | claim-booster-robotics-entity-classification | https://www.boosterobotics.com/about-us |
| cand-romela | university_laboratory | out_of_scope | claim-romela-entity-classification | https://romela.org/ |
| cand-jaka-robotics | legal_entity_publisher | retain_candidate_pending_human_review | claim-jaka-robotics-entity-classification | https://www.jaka.com/en_eu |
| cand-agibot | brand_of_legal_entity | retain_candidate_pending_human_review | claim-agibot-entity-classification | https://www.agibot.com/about_Zhiyuan |
| cand-magiclab | brand_of_legal_entity | retain_candidate_pending_human_review | claim-magiclab-entity-classification | https://www.magiclab.top/en/about, https://www.magiclabglobal.com/ |
| cand-apptronik | legal_entity_publisher | retain_candidate_pending_human_review | claim-apptronik-entity-classification | https://apptronik.com/ |
| cand-agility | brand_or_short_name | retain_candidate_pending_human_review | claim-agility-entity-classification | https://www.agilityrobotics.com/ |

Files changed:
- research/humanoids/registry/candidates.jsonl (25 classified, proposals in review notes only)
- research/humanoids/registry/sources.jsonl (26 official sources, supports_claim_ids aligned)
- research/humanoids/registry/provenance-claims.jsonl (38 claims; every claim has an official source URL)
- research/humanoids/registry/index.json (discovery_progress counts only; universe_size_claim stays null)
- research/humanoids/tools/validate_registry.py (deterministic official-source/reference/dedup/count checks)
- tests/test_humanoid_registry.py (stale lane counts updated; N4 proposal-only test added)
- progress/N4-registry-dedup.md (this file)

Attempts: resumed partial work in place (attempt already in progress on wave3/n4); audit found 2 test failures and 12 unsupported/over-specific claim assertions, fixed in this attempt without resetting. Total attempts used: 1 resumed completion pass (within the 3-attempt gate limit).

Gate verdict: pass, conditional only on PR CI and the full test suite recorded in the PR. Human decision still required in checks.md before any duplicate/out_of_scope/canonical/verified value is applied.

## 3. Model confidence (last)

High for reference integrity, counts, no-promotion, and duplicate-pair absence within these 25 seed records, because those are deterministically validated. Medium for entity-classification wording, because it rests on manual official-page review recorded in sources.jsonl; Tesla remains explicitly unassessed and LimX Dynamics metadata-only, and a human reviewer must decide every proposed disposition.
