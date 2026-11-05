# Frontier Phase 1 — rigorous program plan

Status: Phase 1 scaffold implemented in this commit. Everything below separates
DONE (in repo, tested) from PLANNED (backlog). No physical control is deployed.

## Objective
Build the evidence layer for humanoid research and local STOP recognition:
machine-readable schemas, a provenance-first registry, a legal research
roadmap, and a voice/gesture STOP training roadmap — without fabricating
companies, APIs, licences, or legal conclusions.

## Non-goals / hard boundaries (inherited, not weakened)
- Simulated robot only. No physical humanoid control, no certified e-stop claim.
- Recognition may only propose STOP through the existing authenticated,
  idempotent, latched path (`integrations/interventions.py`). Nothing here
  resets/unlatches, resumes, or moves anything.
- No scraping against terms/robots.txt, no downloading copyrighted video,
  no invented endpoints/facts, no claim that seed names are verified companies.

## Workstreams
W1 Registry & schemas (DONE in Phase 1)
  - 6 JSON Schema 2020-12 schemas under research/humanoids/schemas/
  - 25 seed candidates, exact names preserved, all candidate_unverified
  - stdlib validator + tests (fabrication guard, no universe-size claim)
W2 Source verification (PLANNED, parallelizable per candidate)
  - For each candidate: find official site first; only then docs/API/SDK/
    GitHub/papers. Record source records with robots/ToS status, hash, date.
  - Gate: partially_verified requires >=1 primary official source + reviewer.
W3 Datasets & APIs inventory (PLANNED)
  - Dataset records only with licence + privacy fields; unknown stays unknown.
  - API surfaces only from official docs; endpoints need source_ids.
W4 Legal research (PLANNED — see LEGAL-RESEARCH-ROADMAP.md, not legal advice)
W5 Voice/gesture STOP models (PLANNED — see VOICE-GESTURE-STOP-TRAINING-ROADMAP.md)
  - Local-only training/eval; abstention + fail-closed; never bypasses the
    deterministic recognizers' path or the latch.
W6 Integration (FUTURE, gated) — any new recognizer enters only as another
  proposer into the same intervention service; requires human approval,
  subgroup metrics, and rollback. Isaac Sim before any hardware discussion.

## Phases & exit gates
Phase 1 (this commit): schemas, registry scaffold, validator, tests, roadmaps.
  Exit: full test suite green; validator clean; zero verified records.
Phase 2: verify candidates in P0/P1 batches (see BACKLOG.md). Exit per record:
  evidence-linked status change reviewed by a named human.
Phase 3: dataset/API inventory for verified entities only. Exit: licence and
  privacy fields evidenced, or explicitly unknown.
Phase 4: STOP dataset collection (consented) + offline evaluation harness.
  Exit: dataset/model cards complete; FP/FN targets assessed per subgroup.
Phase 5: shadow-mode recognizer (proposes, never actuates beyond STOP path),
  human gate before any change in deployment status.

## Evidence & review protocol
- Atomic claims (claim-*) link subject -> predicate -> sources. Contested
  claims stay contested; retractions are recorded, not deleted silently.
- Every status change: reviewer, timestamp, basis. Anna Medelvärde plans /
  analyzes / reviews; implementation instances execute; humans approve
  verification and any deployment gate.

## Metrics of program health
- % candidates with >=1 primary source; % claims contested/retracted;
  validator violations (must be 0); datasets with unknown licence (drive down
  only by evidence); STOP eval coverage by language/environment (Phase 4+).

## Risks
Seed-name ambiguity & duplicates (mitigate: duplicate/out_of_scope statuses);
SEO/marketing pages masquerading as primary sources (require official-domain
evidence); licence laundering via aggregators (licence_source_ids must point
to licence text); dataset consent gaps (no training on unknown-consent data);
legal drift (roadmap requires primary regulator sources + counsel review).
