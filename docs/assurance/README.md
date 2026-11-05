# Assurance pack (Wave 5 F7) - scope and limits

This directory is the human-readable half of `tools/repro/`. Generated
run output lives in `repro-out/` (not committed); this directory holds
the method, the claim discipline, and primary-source research questions.

## What this pack is

- A reproducible record: one script (`tools/repro/repro.py`) that, from
  a clean clone, records an environment manifest, runs the repo's own
  build/test steps, hashes artifacts and the SBOM, and emits a
  claim-to-evidence checklist.
- An explicit unsupported list: claims with no clean-clone command
  (hardware/process records in `docs/DILIGENCE.md`), QIP requirements
  marked UNIMPLEMENTED in QIP v0.1 S.11, and steps that were skipped
  or unavailable are listed as unsupported/not-claimed - never rounded
  up to passes.

## What this pack is not

- Not certification, approval, or conformity assessment under any
  machinery, robotics, AI, or functional-safety standard or law.
- Not a legal conclusion. EU topics appear only in
  RESEARCH-QUESTIONS.md, as questions tied to primary sources.
- Not physical-safety validation, not a QIP conformance-class claim
  (no class is claimed in QIP v0.1; a traced test ID is a trace, not a
  class), and not evidence about hosts the run did not execute on
  (a Mac/CI pass is not a Pi or Isaac-host pass).

## Files

| File | Content |
|---|---|
| CLAIM-TO-EVIDENCE.md | How checklist statuses are assigned; the standing unsupported categories. Per-run checklists are generated, not hand-edited. |
| RESEARCH-QUESTIONS.md | EU Machinery Regulation / AI Act research questions, primary sources only, no conclusions. |
| ../tools/repro/README.md | Exact runner commands and output formats. |

Rule (graph.md R-IMM-4, QIP-R11): no claim ahead of evidence; raw
output required; deterministic check first, report second, confidence
last.
