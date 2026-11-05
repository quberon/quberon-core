# EU research questions (primary sources only)

Status: research questions for qualified human/legal review. This file
states NO legal conclusion, makes NO applicability determination, and
claims NO compliance, conformity, or certification. It follows
docs/frontier-phase1/LEGAL-RESEARCH-ROADMAP.md ("record open questions;
do not resolve them by assertion") and the review-depth discipline of
docs/specs/intervention-profile/PRIOR-ART.md.

## EU Machinery Regulation - Regulation (EU) 2023/1230

Primary source: Official Journal text, https://eur-lex.europa.eu/eli/reg/2023/1230/oj
(review depth in PRIOR-ART.md: `official full public text reviewed`,
for legal context only).

Open questions (unresolved):
- Q-M1: Where is the boundary between simulation-only intervention
  software such as this repo's and "machinery"/"related product"
  scope, for a deployment that later connects to a real robot?
- Q-M2: If a future deployment entered scope, which essential health
  and safety requirements and which conformity-assessment route would
  a qualified assessor identify, and what evidence would they require
  beyond a software claim-to-evidence checklist?
- Q-M3: Which provisions on autonomous/self-evolving behaviour, if
  any, would be relevant to a planner-proposes/deterministic-law-
  disposes architecture, and who must answer that - manufacturer,
  integrator, or operator?
- Q-M4: What application dates and transitional provisions would
  govern a first real deployment, per the Official Journal text?

## EU AI Act - Regulation (EU) 2024/1689

Primary source: Official Journal text, https://eur-lex.europa.eu/eli/reg/2024/1689/oj
EUR-Lex is the EU's official primary-source repository; no secondary
commentary is relied on here, and no article-level claim is made.

Open questions (unresolved):
- Q-A1: How would risk classification questions be framed for AI
  components embedded in a robot intervention path versus a
  research-only registry or simulator, and which actors bear them?
- Q-A2: Which transparency and human-oversight questions, if any,
  would arise for deterministic recogniser inputs (voice/gesture)
  that may request STOP only?
- Q-A3: What is the staged application timeline in the Official
  Journal text, and which dates would matter to a first deployment?
- Q-A4: What role, if any, would harmonised standards play, and what
  would reliance on them require beyond this repo's evidence pack?

## Gate

No question above moves to an answer in this repo without: the
primary text cited per point, a dated issue-spotting note, and
qualified legal/safety review recorded by a human. Until then every
item stays `requires_qualified_legal_review` (roadmap wording).
