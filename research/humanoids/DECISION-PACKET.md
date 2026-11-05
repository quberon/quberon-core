# Humanoid registry — human decision packet (all 25 candidates)

Status: RECOMMENDATIONS ONLY. This packet is not a decision, does not
promote, reject, deduplicate, or reclassify any record, and does not
edit checks.md. Every candidate remains candidate_unverified with
canonical_name=null and evidence_source_ids=[] until a human signs
below and N0 (assembly owner, graph.md) records a human row in
checks.md; only a later applying node may then change registry data.

Prepared by: Wave 4 node N6 (registry decisions packet), Tier 1.
Inputs read: research/humanoids/registry/{candidates,sources,provenance-claims}.jsonl,
research/humanoids/registry/index.json, progress/N4-registry-dedup.md
(Wave 3 N4 proposals), graph.md (assembly and no-promotion rules).
universe_size_claim: null (index.json unchanged; 25 is the seed
candidate count, not a claim about how many humanoid companies exist).

## 1. One-sitting format (target: one reviewer, one sitting)

1. Read the summary counts in section 2.
2. For each of the 25 entries in section 3, tick exactly one box on
   the batch sheet in section 4: A = approve the recommendation,
   R = reject it (write the alternative in the margin), D = defer.
3. Sign and date section 4. An unsigned packet decides nothing.
4. Hand the signed packet to N0. N0 alone converts it into checks.md
   rows (proposed wording in section 5). No registry field changes
   in this packet or from this packet alone.

Confidence vocabulary: high / medium / unknown, copied from or
bounded by the assessed.confidence of the underlying claim in
provenance-claims.jsonl. Confidence is stated per recommendation,
never as a substitute for the deterministic checks in section 6.

## 2. Decision codes and deterministic summary

| code | meaning if a human approves it (applied later, not here) | count |
|---|---|---:|
| ALIAS-THEN-PARTIAL | Seed is an alias of the named entity (one record); later node may set partially_verified with that canonical_name. | 1 |
| DEFER-METADATA-ONLY | Stay candidate_unverified; no promotion on metadata-only official evidence. | 1 |
| DEFER-NO-ACCESS | Stay candidate_unverified; no entity/scope conclusion until the official page is actually accessed. | 1 |
| OUT-OF-SCOPE | Later node may set status out_of_scope (humanoid-company registry scope). | 2 |
| PARENT-CONTEXT-ONLY | Parent-company context only; not a standalone humanoid company; no separate lab/platform candidates. | 1 |
| PARTIAL-BRAND-OF-ENTITY | Later node may set partially_verified (not verified) with the legal entity as canonical_name and the seed kept as brand/alias. | 2 |
| PARTIAL-LEGAL-ENTITY | Later node may set partially_verified (not verified) with the named legal entity as canonical_name. | 2 |
| RETAIN-UNVERIFIED | Stay candidate_unverified, canonical_name=null, in scope for further research; no legal-entity conclusion. | 15 |
| TOTAL |  | 25 |

## 3. Per-candidate analysis, exact decision, and recommendation

Entity-vs-brand rule used throughout: a brand/product/publisher name
on an official page is not a legal entity. A legal-entity conclusion
is recommended only where the reviewed official source itself names
the entity (identity claim) and a humanoid product/relevance claim
from the same official source supports scope. Where the source
record's publisher_claim field mentions a legal name but the
entity-classification claim deliberately drew no legal conclusion
(noted as 'publisher-claim lead' below), the recommendation is to
retain unverified and let the human verify that lead, not to adopt it.

### 3.1 Leju Robot (cand-leju-robot)

- Official source(s) (every recommendation below cites these):
  - src-leju-robot-official-site: https://www.lejurobot.com/en (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Official Leju site identifies Leju (Shenzhen) Robotics Co., Ltd. and presents humanoid robot products.
    retrieval_note: Official page recorded for human review; no claim or candidate status promotion is made by this source record.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-leju-robot-entity-classification [status=supported_by_primary_source, assessed confidence=high]: brand_or_company_name: Leju presents humanoid robot products on its official site
    note: Official site recorded for human review; no legal-entity conclusion is drawn in this pass. Proposal only; no candidate status, canonical name, or scope field was promoted.
  - Publisher-claim lead (NOT adopted as a conclusion): Official Leju site identifies Leju (Shenzhen) Robotics Co., Ltd. and presents humanoid robot products.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.2 Kepler (cand-kepler)

- Official source(s) (every recommendation below cites these):
  - src-kepler-official-about: https://www.gotokepler.com/about (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Official about page identifies Shanghai Kepler Robot Co., Ltd. and describes its focus on general humanoid robots.
    retrieval_note: Official page recorded for human review; no claim or candidate status promotion is made by this source record.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-kepler-entity-classification [status=supported_by_primary_source, assessed confidence=high]: brand_or_company_name: Kepler presents general-purpose humanoid robots on its official about page
    note: Official about page recorded for human review; no legal-entity conclusion is drawn in this pass. Proposal only; no candidate status, canonical name, or scope field was promoted.
  - Publisher-claim lead (NOT adopted as a conclusion): Official about page identifies Shanghai Kepler Robot Co., Ltd. and describes its focus on general humanoid robots.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.3 Tesla Optimus (cand-tesla-optimus)

- Official source(s) (every recommendation below cites these):
  - src-tesla-optimus-official-ai: https://www.tesla.com/AI (source_type=official_site, access=not_accessed, evidence_strength=unassessed)
    publisher_claim: Official Tesla AI URL discovered for Optimus review, but page access was denied from the review environment.
    retrieval_note: Official URL recorded as not accessed; no claim or candidate status promotion is made by this source record.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-tesla-optimus-entity-classification [status=candidate_unverified, assessed confidence=unknown]: unassessed_pending_official_access: official Tesla AI URL recorded but not accessed in the review environment; no entity, dedup, or scope conclusion is asserted
    note: Official URL returned Access Denied and was recorded as not_accessed; no assertion is supported by this claim. Proposal pending human access to the official page; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve DEFER-NO-ACCESS for Tesla Optimus until the cited official page is actually accessed by a human?
- Recommended answer [DEFER-NO-ACCESS]: Defer any entity/scope decision; retain candidate_unverified with canonical_name=null until a human manually accesses the official Tesla page and records what it states.
- Recommendation confidence: high (in deferring; entity confidence unknown).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.4 Sanctuary AI (cand-sanctuary-ai)

- Official source(s) (every recommendation below cites these):
  - src-sanctuary-ai-official-about: https://sanctuary.ai/about-us/ (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Official Sanctuary AI site identifies the publisher as Sanctuary Cognitive Systems Corporation and presents its physical-AI robotics work.
    retrieval_note: Official page recorded for human review; no claim or candidate status promotion is made by this source record.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-sanctuary-ai-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: Sanctuary AI presents physical-AI robotics work on its official about page
    note: Official about page recorded for human review; no legal-entity conclusion is drawn in this pass. Proposal only; no candidate status, canonical name, or scope field was promoted.
  - Publisher-claim lead (NOT adopted as a conclusion): Official Sanctuary AI site identifies the publisher as Sanctuary Cognitive Systems Corporation and presents its physical-AI robotics work.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.5 Fourier (cand-fourier)

- Official source(s) (every recommendation below cites these):
  - src-fourier-gr1-official-docs: https://support-old.fftai.com/en/docs/GR-X-Humanoid-Robot/GR1/GR-1_Introduction/ (source_type=official_docs, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Official Fourier documentation describes the GR-1 series as a general-purpose humanoid robot.
    retrieval_note: Official page recorded for human review; no claim or candidate status promotion is made by this source record.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-fourier-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: Fourier publishes the GR-1 general-purpose humanoid robot documentation
    note: Official documentation establishes the Fourier publisher/product relationship but is insufficient for a legal-entity conclusion. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.6 Boston Dynamics (cand-boston-dynamics)

- Official source(s) (every recommendation below cites these):
  - src-boston-dynamics-atlas-official: https://bostondynamics.com/products/atlas/ (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Official Boston Dynamics product page describes Atlas as an industrial humanoid robot.
    retrieval_note: Official page recorded for human review; no claim or candidate status promotion is made by this source record.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-boston-dynamics-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: company_or_brand_name: Boston Dynamics publishes Atlas as an industrial humanoid robot
    note: Official product page establishes humanoid relevance; this pass does not make a legal-entity conclusion. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.7 X-humanoid (cand-x-humanoid)

- Official source(s) (every recommendation below cites these):
  - src-x-humanoid-official-site: https://www.x-humanoid.com/en (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: X-humanoid
    retrieval_note: Official site presents TianGong and embodied-AI robotic products; recorded for later human review only.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-x-humanoid-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: X-humanoid presents TianGong and embodied-AI robotic products on its official site
    note: Official site presents TianGong and embodied-AI robotic products; no legal-entity conclusion is drawn. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.8 Unitree (cand-unitree)

- Official source(s) (every recommendation below cites these):
  - src-unitree-official-site: https://www.unitree.com/ (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Unitree Robotics
    retrieval_note: Official site identifies Unitree Robotics and lists humanoid products; recorded for later human review only.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-unitree-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: Unitree Robotics lists humanoid products on its official site
    note: Official site identifies Unitree Robotics and lists humanoid products; no legal-entity conclusion is drawn. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.9 Engineai (cand-engineai)

- Official source(s) (every recommendation below cites these):
  - src-engineai-official-site: https://en.engineai.com.cn/about-us (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: ENGINEAI
    retrieval_note: Official ENGINEAI about page recorded for later human review only.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-engineai-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: ENGINEAI presents humanoid robots on its official about page
    note: Official ENGINEAI about page recorded for human review; no legal-entity conclusion is drawn. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.10 Robot Era (cand-robot-era)

- Official source(s) (every recommendation below cites these):
  - src-robot-era-official-site: https://www.robotera.com/en/ (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: ROBOTERA
    retrieval_note: Official site lists ROBOTERA humanoid products; recorded for later human review only.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-robot-era-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: ROBOTERA lists humanoid products on its official site
    note: Official site lists ROBOTERA humanoid products; no legal-entity conclusion is drawn. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.11 Pndbotics (cand-pndbotics)

- Official source(s) (every recommendation below cites these):
  - src-pndbotics-official-site: https://www.pndbotics.com/ (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: PNDbotics
    retrieval_note: Official site describes the Adam general-purpose humanoid platform; recorded for later human review only.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-pndbotics-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: PNDbotics publishes the Adam humanoid robot and developer platform
    note: Official site establishes humanoid relevance but does not provide sufficient legal-entity identity in the reviewed source. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.12 Xpeng (cand-xpeng)

- Official source(s) (every recommendation below cites these):
  - src-xpeng-official-site: https://www.xpeng.com/news/019a4d1549039eaa99ad9c9a33a00016 (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: XPENG
    retrieval_note: Official XPENG site source discovered for later human review of the candidate's humanoid relevance.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-xpeng-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: XPENG presents a humanoid robot on its official site
    note: Official XPENG page recorded for human review of humanoid relevance; no legal-entity conclusion is drawn. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.13 UBTech (cand-ubtech)

- Official source(s) (every recommendation below cites these):
  - src-ubtech-official-site: https://www.ubtrobot.com/en/humanoid/products/walker-s2 (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: UBTECH
    retrieval_note: Official UBTECH Walker S2 humanoid product page recorded for later human review only.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-ubtech-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: UBTECH publishes the Walker S2 humanoid robot
    note: Official product page establishes humanoid relevance but this pass does not make a legal-entity conclusion. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.14 DEEP Robotics (cand-deep-robotics)

- Official source(s) (every recommendation below cites these):
  - src-deep-robotics-official-dr02: https://www.deeprobotics.cn/en/index/dr02.html (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: DEEP Robotics
    retrieval_note: Official product page manually reviewed; it presents DR02 as an industry-grade all-weather humanoid robot and the footer displays a Chinese company name. The relationship between the DEEP Robotics brand and any legal entity remains a publisher claim.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-deep-robotics-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: DEEP Robotics publishes DR02 as an industry-grade humanoid robot
    note: Official product page presents DR02 as a humanoid robot; no legal-entity conclusion is drawn from the reviewed page. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.15 Physicalintelligence (cand-physicalintelligence)

- Official source(s) (every recommendation below cites these):
  - src-physical-intelligence-official-home: https://www.physicalintelligence.company/ (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Physical Intelligence
    retrieval_note: Official homepage manually reviewed; it describes a group developing learning algorithms/models to control robots. It does not establish that the candidate itself is a humanoid manufacturer or identify a legal entity.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-physicalintelligence-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: robot_ai_lab_or_company: Physical Intelligence develops general-purpose robot foundation models, not a claimed humanoid product
    note: Official homepage describes models intended to control robots generally and does not claim a humanoid manufacturer/product. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve OUT-OF-SCOPE for Physicalintelligence (robot-AI models, no claimed humanoid product on the cited official homepage)?
- Recommended answer [OUT-OF-SCOPE]: Approve marking out_of_scope in a later applying node: official homepage describes general robot foundation models, not a claimed humanoid product/manufacturer.
- Recommendation confidence: medium.
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.16 Limx Dynamics (cand-limx-dynamics)

- Official source(s) (every recommendation below cites these):
  - src-limx-dynamics-official-luna: https://www.limxdynamics.com/en/products/luna/spec (source_type=official_site, access=metadata_only, evidence_strength=primary_official)
    publisher_claim: LimX Dynamics
    retrieval_note: Metadata-only discovery records the official URL and title; no legal-entity conclusion is drawn.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-limx-dynamics-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: LimX Dynamics presents Luna as a full-size humanoid robot (metadata-only official title)
    note: Metadata-only official product page title records Luna as a full-size humanoid robot; WAF blocked manual review and no legal-entity conclusion is drawn. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve DEFER-METADATA-ONLY for LimX Dynamics until full manual official-page review is recorded?
- Recommended answer [DEFER-METADATA-ONLY]: Defer promotion; retain candidate_unverified with canonical_name=null until a human completes a full manual review of the cited official page (current record is metadata-only, WAF-blocked).
- Recommendation confidence: high (in not promoting on metadata only).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.17 Tencent (cand-tencent)

- Official source(s) (every recommendation below cites these):
  - src-tencent-tairos-official: https://tairos.tencent.com/en-US (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Tencent / Tairos
    retrieval_note: Official Tencent-hosted platform manually reviewed; it presents embodied models, agents, tools, and humanoid-robot case studies, including Tencent Robotics X collaborations. Robotics X and Tairos are treated as lab/platform claims, not separate legal entities.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-tencent-entity-classification [status=supported_by_primary_source, assessed confidence=high]: parent_company_with_lab_and_platform: Tencent is the parent identity; Robotics X is a lab and Tairos is an embodied-intelligence platform
    note: Official Tencent-hosted page attributes Tairos to Tencent Robotics X and presents models/platform capabilities, not a separate humanoid-company entity. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve PARENT-CONTEXT-ONLY for Tencent (no standalone humanoid-company promotion, no separate lab/platform candidates)?
- Recommended answer [PARENT-CONTEXT-ONLY]: Approve classifying Tencent only as parent-company context (Robotics X = lab, Tairos = platform); do not promote it as a standalone humanoid company and do not create separate Robotics X/Tairos company candidates.
- Recommendation confidence: high.
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.18 Pudu Robotics (cand-pudu-robotics)

- Official source(s) (every recommendation below cites these):
  - src-pudu-robotics-official-d9: https://www.pudurobotics.com/en/products/d9 (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Pudu Robotics
    retrieval_note: Official product page manually reviewed; it calls D9 the first full-sized bipedal humanoid robot by Pudu Robotics. Product and brand names are recorded as publisher claims, without a legal-entity conclusion.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-pudu-robotics-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_company_name: Pudu Robotics publishes PUDU D9 as its humanoid robot
    note: Official product page establishes PUDU D9 as a Pudu Robotics product; no legal-entity conclusion is made. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.19 Booster Robotics (cand-booster-robotics)

- Official source(s) (every recommendation below cites these):
  - src-booster-robotics-official-about: https://www.boosterobotics.com/about-us (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Booster Robotics
    retrieval_note: Official about page manually reviewed; it states Booster Robotics was founded in 2023 and creates humanoid robot products and developer platforms. Booster Robotics is retained as a publisher/brand claim rather than asserted as a legal entity.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-booster-robotics-entity-classification [status=supported_by_primary_source, assessed confidence=high]: brand_or_company_name: Booster Robotics creates humanoid robot products and developer platforms
    note: Official about page states Booster Robotics was founded in 2023 and creates humanoid robot products and developer platforms; no legal-entity conclusion is drawn. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve RETAIN-UNVERIFIED for this seed (no canonical name, no promotion), as defined in section 2?
- Recommended answer [RETAIN-UNVERIFIED]: Approve retaining as candidate_unverified, in scope for further humanoid research, with canonical_name=null and no legal-entity conclusion, until a human cites an official page that names the legal entity behind the brand.
- Recommendation confidence: high (in not promoting; entity itself unproven).
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.20 RoMeLa (cand-romela)

- Official source(s) (every recommendation below cites these):
  - src-romela-official-home: https://romela.org/ (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: RoMeLa
    retrieval_note: Official lab homepage manually reviewed; it identifies RoMeLa as the Robotics & Mechanisms Laboratory at UCLA, a research and education facility emphasizing humanoid robots. This supports treating the seed as a lab claim, not a company or legal entity.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-romela-entity-classification [status=supported_by_primary_source, assessed confidence=high]: university_laboratory: RoMeLa is the Robotics and Mechanisms Laboratory at UCLA
    note: Official lab homepage identifies RoMeLa as a UCLA research and education facility, not a company. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve OUT-OF-SCOPE for RoMeLa (UCLA laboratory, not a company)?
- Recommended answer [OUT-OF-SCOPE]: Approve marking out_of_scope in a later applying node: official homepage identifies a UCLA university laboratory, not a company.
- Recommendation confidence: high.
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.21 JAKA Robotics (cand-jaka-robotics)

- Official source(s) (every recommendation below cites these):
  - src-jaka-official-site: https://www.jaka.com/en_eu (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: JAKA Robotics Co., Ltd.
    retrieval_note: Official homepage/footer identifies JAKA Robotics Co., Ltd.; homepage navigation and news identify an Embodied Intelligent Family and JAKAπ as a lightweight humanoid robot.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-jaka-official-identity [status=supported_by_primary_source, assessed confidence=high]: JAKA Robotics Co., Ltd.
    note: Official homepage footer names JAKA Robotics Co., Ltd. This supports an identity proposal only; no candidate status or canonical name was promoted.
  - claim-jaka-humanoid-relevance [status=supported_by_primary_source, assessed confidence=high]: claimed_humanoid
    note: Official homepage identifies an Embodied Intelligent Family and calls JAKAπ a lightweight humanoid robot.
  - claim-jaka-robotics-entity-classification [status=supported_by_primary_source, assessed confidence=high]: legal_entity_publisher: JAKA Robotics Co., Ltd.
    note: Official homepage footer names the legal entity and presents a humanoid product. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve PARTIAL-LEGAL-ENTITY for JAKA Robotics with canonical_name='JAKA Robotics Co., Ltd.' (partially_verified only)?
- Recommended answer [PARTIAL-LEGAL-ENTITY]: Approve, in a later applying node, partially_verified (not verified) with canonical_name='JAKA Robotics Co., Ltd.' and evidence_source_ids=[src-jaka-official-site].
- Recommendation confidence: high.
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.22 AgiBot (cand-agibot)

- Official source(s) (every recommendation below cites these):
  - src-agibot-official-site: https://www.agibot.com/about_Zhiyuan (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: AGIBOT Innovation (Shanghai) Technology Co., Ltd.
    retrieval_note: Official About page states the AGIBOT identity and describes intelligent/general-purpose robots; its milestones explicitly mention humanoid robots and the AGIBOT A1 humanoid robot.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-agibot-official-identity [status=supported_by_primary_source, assessed confidence=high]: AGIBOT Innovation (Shanghai) Technology Co., Ltd.
    note: Official site title and footer state AGIBOT Innovation (Shanghai) Technology Co., Ltd. No candidate status or canonical name was promoted.
  - claim-agibot-humanoid-relevance [status=supported_by_primary_source, assessed confidence=high]: claimed_humanoid
    note: Official About page milestones explicitly reference humanoid robots and the AGIBOT A1 humanoid robot.
  - claim-agibot-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_of_legal_entity: AgiBot is associated with AGIBOT Innovation (Shanghai) Technology Co., Ltd.
    note: Official about page names the legal entity and humanoid robots. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve PARTIAL-BRAND-OF-ENTITY for AgiBot with canonical_name='AGIBOT Innovation (Shanghai) Technology Co., Ltd.' and AgiBot retained as alias?
- Recommended answer [PARTIAL-BRAND-OF-ENTITY]: Approve, in a later applying node, partially_verified (not verified) with canonical_name='AGIBOT Innovation (Shanghai) Technology Co., Ltd.', keeping 'AgiBot' as brand/alias.
- Recommendation confidence: medium.
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.23 MagicLab (cand-magiclab)

- Official source(s) (every recommendation below cites these):
  - src-magiclab-official-site: https://www.magiclab.top/en/about (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Magiclab Robotics Technology (Wuxi) Co., Ltd.
    retrieval_note: Official About page describes MagicLab as developing general humanoid robots and names Magiclab Robotics Technology (Wuxi) Co., Ltd. in the footer; the same official site directs users to magiclabglobal.com as its new global site.
  - src-magiclab-global-official-site: https://www.magiclabglobal.com/ (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: MagicLab Robotics
    retrieval_note: The legacy official site links this domain as its new Global Site; this site presents MagicLab humanoid and quadruped products.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-magiclab-official-identity [status=supported_by_primary_source, assessed confidence=high]: Magiclab Robotics Technology (Wuxi) Co., Ltd.
    note: Official About page footer names Magiclab Robotics Technology (Wuxi) Co., Ltd. No candidate status or canonical name was promoted.
  - claim-magiclab-humanoid-relevance [status=supported_by_primary_source, assessed confidence=high]: claimed_humanoid
    note: Official About page says the company researches, develops, and applies general humanoid robots and embodied intelligence technology.
  - claim-magiclab-site-alias [status=supported_by_primary_source, assessed confidence=high]: magiclab.top redirects users by explicit link to magiclabglobal.com as its new Global Site
    note: Record as duplicate/alias evidence for human decision. This is a site-domain alias claim, not a promoted duplicate-company fact.
  - claim-magiclab-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_of_legal_entity: MagicLab is associated with Magiclab Robotics Technology (Wuxi) Co., Ltd.
    note: Official about-page footer names the legal entity and presents general humanoid robots. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve PARTIAL-BRAND-OF-ENTITY for MagicLab with canonical_name='Magiclab Robotics Technology (Wuxi) Co., Ltd.', MagicLab as alias, and the two official domains treated as one record?
- Recommended answer [PARTIAL-BRAND-OF-ENTITY]: Approve, in a later applying node, partially_verified (not verified) with canonical_name='Magiclab Robotics Technology (Wuxi) Co., Ltd.', keeping 'MagicLab' as brand/alias and both official domains as one record (site alias, not a duplicate candidate).
- Recommendation confidence: medium.
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.24 Apptronik (cand-apptronik)

- Official source(s) (every recommendation below cites these):
  - src-apptronik-official-site: https://apptronik.com/ (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Apptronik, Inc.
    retrieval_note: Official homepage describes Apollo as a humanoid robotics platform; official Terms identify the website operator as Apptronik, Inc., a Delaware corporation.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-apptronik-official-identity [status=supported_by_primary_source, assessed confidence=high]: Apptronik, Inc.
    note: Official Website Terms identify the operator as Apptronik, Inc., a Delaware corporation. No candidate status or canonical name was promoted.
  - claim-apptronik-humanoid-relevance [status=supported_by_primary_source, assessed confidence=high]: claimed_humanoid
    note: Official homepage describes Apollo and a complete approach to humanoid robotics.
  - claim-apptronik-entity-classification [status=supported_by_primary_source, assessed confidence=high]: legal_entity_publisher: Apptronik, Inc.
    note: Official terms identify Apptronik, Inc.; official homepage presents Apollo humanoid robotics. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve PARTIAL-LEGAL-ENTITY for Apptronik with canonical_name='Apptronik, Inc.' (partially_verified only)?
- Recommended answer [PARTIAL-LEGAL-ENTITY]: Approve, in a later applying node, partially_verified (not verified) with canonical_name='Apptronik, Inc.' and evidence_source_ids=[src-apptronik-official-site].
- Recommendation confidence: high.
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

### 3.25 Agility (cand-agility)

- Official source(s) (every recommendation below cites these):
  - src-agility-official-site: https://www.agilityrobotics.com/ (source_type=official_site, access=manual_browser_review, evidence_strength=primary_official)
    publisher_claim: Agility Robotics
    retrieval_note: Official homepage metadata identifies Agility and states its humanoid robots are deployed in industrial settings; site navigation links Company and Digit pages under the agilityrobotics.com domain.
- Entity-vs-brand analysis (from provenance-claims.jsonl):
  - claim-agility-official-identity [status=supported_by_primary_source, assessed confidence=medium]: Agility Robotics
    note: Official domain and social/navigation identifiers use Agility Robotics, while page branding is shortened to Agility. Treat this as identity evidence requiring human canonical-name review.
  - claim-agility-humanoid-relevance [status=supported_by_primary_source, assessed confidence=high]: claimed_humanoid
    note: Official homepage title and description explicitly describe industrial humanoid automation and Agility's humanoid robots.
  - claim-agility-name-alias [status=supported_by_primary_source, assessed confidence=medium]: Agility may be a shortened brand reference for Agility Robotics
    note: Record as alias evidence for later human decision; do not promote canonical name or duplicate status from this claim alone.
  - claim-agility-entity-classification [status=supported_by_primary_source, assessed confidence=medium]: brand_or_short_name: Agility is a shortened public brand reference for Agility Robotics
    note: Official domain and navigation use Agility Robotics while page branding uses Agility; human canonical-name review is required. Proposal only; no candidate status, canonical name, or scope field was promoted.
- Exact decision required: Do you approve ALIAS-THEN-PARTIAL for Agility: 'Agility' = alias, canonical_name='Agility Robotics', partially_verified only?
- Recommended answer [ALIAS-THEN-PARTIAL]: Approve treating seed 'Agility' as the shortened brand/alias of 'Agility Robotics' (single record, not a duplicate), and approve, in a later applying node, partially_verified (not verified) with canonical_name='Agility Robotics' only if you confirm that canonical spelling.
- Recommendation confidence: medium.
- Current state (unchanged by this packet): status=candidate_unverified, canonical_name=null, evidence_source_ids=[], humanoid_relevance=unknown.

## 4. Batch decision sheet (complete all 25, then sign)

| # | candidate | seed | recommended code | A (approve) | R (reject) | D (defer) |
|---:|---|---|---|:---:|:---:|:---:|
| 1 | cand-leju-robot | Leju Robot | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 2 | cand-kepler | Kepler | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 3 | cand-tesla-optimus | Tesla Optimus | DEFER-NO-ACCESS | ☐ | ☐ | ☐ |
| 4 | cand-sanctuary-ai | Sanctuary AI | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 5 | cand-fourier | Fourier | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 6 | cand-boston-dynamics | Boston Dynamics | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 7 | cand-x-humanoid | X-humanoid | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 8 | cand-unitree | Unitree | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 9 | cand-engineai | Engineai | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 10 | cand-robot-era | Robot Era | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 11 | cand-pndbotics | Pndbotics | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 12 | cand-xpeng | Xpeng | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 13 | cand-ubtech | UBTech | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 14 | cand-deep-robotics | DEEP Robotics | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 15 | cand-physicalintelligence | Physicalintelligence | OUT-OF-SCOPE | ☐ | ☐ | ☐ |
| 16 | cand-limx-dynamics | Limx Dynamics | DEFER-METADATA-ONLY | ☐ | ☐ | ☐ |
| 17 | cand-tencent | Tencent | PARENT-CONTEXT-ONLY | ☐ | ☐ | ☐ |
| 18 | cand-pudu-robotics | Pudu Robotics | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 19 | cand-booster-robotics | Booster Robotics | RETAIN-UNVERIFIED | ☐ | ☐ | ☐ |
| 20 | cand-romela | RoMeLa | OUT-OF-SCOPE | ☐ | ☐ | ☐ |
| 21 | cand-jaka-robotics | JAKA Robotics | PARTIAL-LEGAL-ENTITY | ☐ | ☐ | ☐ |
| 22 | cand-agibot | AgiBot | PARTIAL-BRAND-OF-ENTITY | ☐ | ☐ | ☐ |
| 23 | cand-magiclab | MagicLab | PARTIAL-BRAND-OF-ENTITY | ☐ | ☐ | ☐ |
| 24 | cand-apptronik | Apptronik | PARTIAL-LEGAL-ENTITY | ☐ | ☐ | ☐ |
| 25 | cand-agility | Agility | ALIAS-THEN-PARTIAL | ☐ | ☐ | ☐ |

Reviewer name: ______________________  Signature: ______________________  Date (UTC): __________________

Effect of signing: only that N0 may record human decision rows in
checks.md (section 5). Registry records are changed afterwards by
the owning node, in a separate change, citing the signed packet.

## 5. Proposed checks.md outcome rows (for N0 only; do NOT insert from this packet)

Verdicts stay unresolved until the section 4 sheet is signed. After
signing, N0 may insert these rows verbatim, replacing 'unresolved'
pending signature' with the signed outcome and the signing date:

| node | requirement | verdict | evidence |
|---|---|---|---|
| N4-registry-dedup | Human decision for cand-leju-robot (Leju Robot): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.1 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.1 |
| N4-registry-dedup | Human decision for cand-kepler (Kepler): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.2 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.2 |
| N4-registry-dedup | Human decision for cand-tesla-optimus (Tesla Optimus): DEFER-NO-ACCESS as recommended in DECISION-PACKET section 3.3 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.3 |
| N4-registry-dedup | Human decision for cand-sanctuary-ai (Sanctuary AI): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.4 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.4 |
| N4-registry-dedup | Human decision for cand-fourier (Fourier): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.5 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.5 |
| N4-registry-dedup | Human decision for cand-boston-dynamics (Boston Dynamics): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.6 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.6 |
| N4-registry-dedup | Human decision for cand-x-humanoid (X-humanoid): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.7 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.7 |
| N4-registry-dedup | Human decision for cand-unitree (Unitree): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.8 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.8 |
| N4-registry-dedup | Human decision for cand-engineai (Engineai): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.9 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.9 |
| N4-registry-dedup | Human decision for cand-robot-era (Robot Era): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.10 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.10 |
| N4-registry-dedup | Human decision for cand-pndbotics (Pndbotics): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.11 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.11 |
| N4-registry-dedup | Human decision for cand-xpeng (Xpeng): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.12 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.12 |
| N4-registry-dedup | Human decision for cand-ubtech (UBTech): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.13 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.13 |
| N4-registry-dedup | Human decision for cand-deep-robotics (DEEP Robotics): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.14 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.14 |
| N4-registry-dedup | Human decision for cand-physicalintelligence (Physicalintelligence): OUT-OF-SCOPE as recommended in DECISION-PACKET section 3.15 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.15 |
| N4-registry-dedup | Human decision for cand-limx-dynamics (Limx Dynamics): DEFER-METADATA-ONLY as recommended in DECISION-PACKET section 3.16 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.16 |
| N4-registry-dedup | Human decision for cand-tencent (Tencent): PARENT-CONTEXT-ONLY as recommended in DECISION-PACKET section 3.17 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.17 |
| N4-registry-dedup | Human decision for cand-pudu-robotics (Pudu Robotics): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.18 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.18 |
| N4-registry-dedup | Human decision for cand-booster-robotics (Booster Robotics): RETAIN-UNVERIFIED as recommended in DECISION-PACKET section 3.19 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.19 |
| N4-registry-dedup | Human decision for cand-romela (RoMeLa): OUT-OF-SCOPE as recommended in DECISION-PACKET section 3.20 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.20 |
| N4-registry-dedup | Human decision for cand-jaka-robotics (JAKA Robotics): PARTIAL-LEGAL-ENTITY as recommended in DECISION-PACKET section 3.21 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.21 |
| N4-registry-dedup | Human decision for cand-agibot (AgiBot): PARTIAL-BRAND-OF-ENTITY as recommended in DECISION-PACKET section 3.22 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.22 |
| N4-registry-dedup | Human decision for cand-magiclab (MagicLab): PARTIAL-BRAND-OF-ENTITY as recommended in DECISION-PACKET section 3.23 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.23 |
| N4-registry-dedup | Human decision for cand-apptronik (Apptronik): PARTIAL-LEGAL-ENTITY as recommended in DECISION-PACKET section 3.24 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.24 |
| N4-registry-dedup | Human decision for cand-agility (Agility): ALIAS-THEN-PARTIAL as recommended in DECISION-PACKET section 3.25 | unresolved pending signature | research/humanoids/DECISION-PACKET.md section 3.25 |
| N4-registry-dedup | Every claim-* has an official source URL | unresolved pending signature (validator evidence in DECISION-PACKET section 6) | research/humanoids/DECISION-PACKET.md section 6; research/humanoids/tools/validate_registry.py |
| N4-registry-dedup | No status promotion without a human row in checks.md | unresolved pending signature (no promotion in this packet) | research/humanoids/DECISION-PACKET.md sections 1 and 4; research/humanoids/registry/index.json |

## 6. Deterministic validation and counts (raw output)

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
Raw result: 8 passed. Full suite: make test = 80 passed.

Packet counts (generated deterministically from the registry): candidates=25, official sources=26, provenance claims=38, recommendations by code={'ALIAS-THEN-PARTIAL': 1, 'DEFER-METADATA-ONLY': 1, 'DEFER-NO-ACCESS': 1, 'OUT-OF-SCOPE': 2, 'PARENT-CONTEXT-ONLY': 1, 'PARTIAL-BRAND-OF-ENTITY': 2, 'PARTIAL-LEGAL-ENTITY': 2, 'RETAIN-UNVERIFIED': 15}, total recommendations=25.
index.json: candidate_count=25, verified_count=0, universe_size_claim=null (unchanged).

## 7. What this packet deliberately does not do

- Does not edit checks.md, graph.md, progress.md, or any registry record.
- Does not decide: the human in section 4 decides; confidence here is advisory and last, after the deterministic evidence above.
- Does not promote any candidate to partially_verified/verified, set any canonical_name, or mark any candidate duplicate/out_of_scope.
- Makes no universe-size claim: universe_size_claim remains null.
