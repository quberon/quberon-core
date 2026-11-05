# Legal research roadmap — humanoid registry, datasets, STOP models

> NOT LEGAL ADVICE. This is a research plan for structuring questions and
> primary sources. It states no legal conclusion. Applicability entries in
> compliance records start as `unknown` / `requires_qualified_legal_review`
> and may only change with primary sources and qualified human review.

Each item: create compliance-assessment records (cmp-*) under
research/humanoids/schemas/compliance-assessment.schema.json, linked to
primary sources (regulator/official journal/standards body) before secondary
commentary. Record open questions; do not resolve them by assertion.

## 1. EU AI Act
Research: risk classification questions for AI components in robots, GPAI vs
embedded AI, transparency duties, human oversight, timelines/application
dates, harmonised standards route. Primary: Official Journal text, Commission
guidance. Open: which obligations, if any, attach to a research registry vs
a deployed recognizer?

## 2. EU Machinery Regulation
Research: scope for machinery/robotics, essential health & safety
requirements, conformity assessment, instructions, autonomous/self-evolving
behaviour provisions. Primary: regulation text, Commission guidance.
Open: relevance boundary between simulation-only software and machinery.

## 3. GDPR (and Swedish supplementary law)
Research: voice audio as personal data; voiceprints/gesture video as possible
biometric data; lawful basis, consent quality, DPIA triggers, retention,
data-subject rights, processors, transfers. Primary: GDPR text, EDPB/IMY
guidance. Rule for this program: no training on unknown-consent voice/video.

## 4. EU Cyber Resilience Act
Research: products with digital elements scope, vulnerability handling,
update/support duties, CE marking, application timeline. Primary: OJ text,
Commission FAQs. Open: status of open-source/research prototypes.

## 5. Product safety & liability
Research: General Product Safety Regulation, revised product liability
(incl. software/AI questions), consumer law, workplace safety if ever
deployed near people. Primary: OJ texts. Explicit: this prototype is not a
safety-rated emergency stop; no document may imply otherwise.

## 6. Standards (voluntary unless incorporated by law/guidance)
Research map only: ISO 10218 (industrial robots), ISO/TS 15066 (collaborative
robots), ISO 13482 (personal care robots), IEC 61508 / ISO 13849 (functional
safety), ISO/IEC 42001 & 23894 (AI management/risk), accessibility standards.
Record edition + source; never claim compliance from a roadmap.

## 7. Dataset copyright, licence & privacy
For every dataset: licence text source, redistribution/commercial/modification
terms, database rights (EU sui generis), moral rights, privacy/consent basis,
takedown path. Unknown licence = metadata only, no download, no training.

## 8. Export controls
Research: EU dual-use regulation and national (Swedish ISP) guidance, US EAR
exposure via components/software, China/other regimes for listed entities.
No controlled technical data is collected in Phase 1; flag, don't conclude.

## 9. Website Terms of Service & robots.txt
Program rule (operational, not a legal conclusion): respect robots.txt and
site terms; prefer official APIs/metadata; manual browser review over bulk
fetching; record robots_txt_status + terms_status on every source record;
when disallowed/restricted: metadata_only or not_accessed. No circumvention,
no downloading copyrighted video (e.g. YouTube) — link + metadata only.

## 10. Other
Trademarks in candidate names (naming/alias use), defamation risk in
unverified claims (hence candidate_unverified labelling), election/public-
communication rules if OD agents ever cite this registry.

## Sequence & gates
1) Primary-source collection per framework (compliance records, status
researching). 2) Issue-spotting memo per framework, drafted for human review.
3) Qualified counsel review before any record moves beyond
requires_qualified_legal_review. 4) Re-check on regulatory change; every
assessment carries reviewed_at and open_questions.
