# viz/truthmap — architecture TRUTH MAP

This directory is the generator for the generated architecture truth map.
Note on location: the node brief said "viz/README.md"; the owned-paths list
for this node is `viz/truthmap/**`, so this README lives at
`viz/truthmap/README.md` inside the owned tree rather than at `viz/README.md`
outside it.

## Regenerate (single command, from repo root)

    python3 -m viz.truthmap.generate

That one command rewrites exactly one generated file:

    docs/assets/architecture-truth-map.svg

Optional machine-readable dump (not committed by default):

    python3 -m viz.truthmap.generate --json-output viz/truthmap/truthmap.json

## What is generated, and what is not

- GENERATED: `docs/assets/architecture-truth-map.svg` — do not hand-edit it;
  re-run the command above. Every component (QIP R1–R11) is coloured by its
  actual evidence status parsed from
  `docs/specs/intervention-profile/QIP-v0.1.md` section 11, using the status
  vocabulary of `docs/assurance/CLAIM-TO-EVIDENCE.md`. The generator refuses
  to emit output if section 11 is missing or the status vocabulary is absent.
- NOT GENERATED / KEPT: `docs/assets/architecture.svg` — the hand-drawn
  system diagram (Phone UI, Raspberry Pi FastAPI, Rust Secure Core,
  SimulatedRobotAdapter, Meta Planner, e-ink, planned items). It is kept,
  not superseded: the generated map covers QIP R1–R11 only, while the
  hand-drawn diagram shows system layout that the two named evidence sources
  cannot colour without inventing status. Which is generated is stated here
  and in the generated SVG itself.

## Reading the map

- Green TRACE PRESENT: section 11 traces every requirement of that component
  to an N4 test ID (`TRACE_PRESENT_NO_CLASS_CLAIM` in CLAIM-TO-EVIDENCE.md).
- Amber PARTIAL: some requirements traced, the rest are gaps.
- Hatched GAP: no requirement has a traced passing test.
  A gap means not built or not tested.

A trace is not a QIP class, conformance, certification, or physical-safety
claim. No QIP class is claimed in v0.1. The generator does not run the N4
tests; it reports the committed section 11 trace status, so a stale trace
can only change by changing that committed table through its own amendment
rule.

## Tests

    python -m pytest viz/truthmap/tests -q
