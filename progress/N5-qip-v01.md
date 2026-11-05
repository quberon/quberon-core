# N5 QIP v0.1 — progress (Wave 4, Tier 1)

Node: Wave4 N5 | Owns: docs/specs/intervention-profile/** and
progress/N5-qip-v01.md only (plus permitted append to
progress/n7-requests.md). Attempts: 1 of 3 used.
Base: origin/main baa18a1522aeb9dc5865afbbfffe89fc94de2ece

## Deliverable

- docs/specs/intervention-profile/QIP-v0.1.md — normative RFC 2119
  profile. Page one states: not a safety standard, no certification,
  complements rather than replaces machinery/functional-safety duties.
  Four cumulative classes: OBSERVE, INTERVENE (=OBSERVE+), AUTHORIZE
  (=INTERVENE+), EVIDENCE (=AUTHORIZE+). 34 requirements QIP-R1.1..R11.3
  covering R1-R11 unchanged from gate-zero OUTLINE.md.
- docs/specs/intervention-profile/TRACEABILITY.md — Wave 4 addendum only
  (gate-zero content unchanged).
- progress/n7-requests.md — appended request tracking (see below).

## Traceability (deterministic check first)

N4 shipped its stable taxonomy on wave4/n4 310fc208555f59a2027f8e3496555e05244b229e:
QIP-ID-01..04, QIP-AUTH-01..04, QIP-INT-01..05, QIP-LATCH-01..03,
QIP-STATE-01..03, QIP-AUDIT-01..03, QIP-PROP-01..03, QIP-DEG-01..03.
N5 adopted it verbatim; no competing taxonomy was invented in the final
text (an initial requested-taxonomy draft was replaced in the same
attempt once the actual N4 IDs were read).

Verification run in this attempt (from the wave4-n4 worktree, N5 venv,
no N4 files modified):
  .venv/bin/python -m pytest conformance/ -q -rs -p no:cacheprovider
  Raw: 27 passed, 1 skipped, 1 warning in 4.32s
  SKIPPED QIP-DEG-03: NOT TESTED (persistence failure / reachable
  refusal not neutrally injectable) — gap, not a pass.

Section 11 of QIP-v0.1.md maps all 34 requirements: 16 rows trace to
verified-present N4 IDs (each traced token grep-verified present in
wave4/n4:conformance/test_conformance.py, 0 missing); 18 rows are
explicit UNIMPLEMENTED, including all of R3 (priority), R10
(manufacturer mapping), R11 (claims), QIP-R7.1/R7.4 (depend on skipped
QIP-DEG-03), QIP-R5.1 (restart persistence), and QIP-R8.1 (full audit
field set). Partial coverage was marked UNIMPLEMENTED, not rounded up.
No QIP class is claimed in v0.1.

Pre-merge amendment rule (binding, in QIP Section 11): after N4 merges,
fetch origin/main, rebase this branch onto it, grep merged conformance/
and N4 raw output for each traced ID, keep only traces with a passing
(not skipped) raw result, downgrade the rest to UNIMPLEMENTED, record
raw output here, and only then merge when CI passes. This node does
NOT self-merge before that: at this attempt N4 is pushed
(310fc20 on origin/wave4/n4) but has no merged PR.

Prior-art discipline: review-depth markers preserved verbatim in
QIP Annex A; paywalled works remain
`scope and abstract reviewed; full text not reviewed`; no normative
requirement is derived from any abstract (no PL/SIL, timing, force,
pressure, speed, separation, or device requirement appears in QIP).

## Local tests

  make-equivalent: .venv/bin/python -m pytest -q (this branch)
  Raw: 69 passed, 11 skipped, 1 warning in 20.20s
Deterministic self-check of QIP-v0.1.md: 34 requirements defined,
34 traceability rows, 0 missing, R1-R11 all covered, four classes
present, page-one phrases and all four review-depth markers present.

## Requests

progress/n7-requests.md appended: N4 taxonomy adoption recorded and the
hold on merging this PR until post-N4 rebase/verification + CI.

## Merge status

PR to be opened from wave4/n5. NOT self-merged: N4 not yet merged to
origin/main, so actual-ID traceability on merged main and CI are not
yet verifiable. That is a Wave-4-order hold, not a content blocker.
