# F4 — Safety-input qualification harness (Wave 5)

Base: 35ee2ae. Tier 1. Owned paths only: research/safety-inputs/** and this
file. No app/control/endpoint/recognizer edits (recognizers imported read-only).

## Deliverable

Synthetic deterministic datasets + harness for the existing voice/gesture
recognizer boundaries: generate.py (enumerated grids, no RNG, byte-identical
regeneration verified by sha256sum), harness.py, datasets/{voice 45,
gesture 30, crossmodal 8}.jsonl (83 cases), tests/test_safety_input_harness.py
(5 tests), results/{results.jsonl, summary.json, report.md}, README.md.

Categories covered: false trigger, missed trigger, stale/replay,
contradictory signals (harness-only OR; no app fusion exists), degraded
confidence (voice conf + gesture visibility/geometry), consecutive-frame /
hold rules (699/700/701 ms, 1/2/3+ frames, interrupted runs).

## Exact results (synthetic only; denominators are labelled intent)

- Total (83): false triggers 1/25 = 0.04; missed 31/58 = 0.534483 (includes
  deliberate boundary abstentions + stale/replay suppression; see report).
- Voice (45): false 1/17 = 0.058824 (sole FP V-NEG-08 "the bus stop is near",
  known standalone-token limit); missed 16/28 = 0.571429; canonical 0/6 missed.
- Gesture (30): false 0/5 = 0.0; missed 15/25 = 0.6; canonical 0/3 missed.
- Crossmodal OR (8): false 0/3, missed 0/5.
- Exact boundaries verified: voice 0.849 no / 0.85 yes; gesture 699 ms no /
  700 ms yes, 2 frames no / 3 yes, visibility 0.79 no / 0.80 yes.
- Layer finding: stale (301 s) and replayed voice inputs trigger
  recognizer-only and are blocked only by the harness freshness
  (>300 s / future <-30 s) + event_id replay layers; gesture duplicate
  timestamps are rejected by the recognizer itself. Full per-category rates
  with denominators: research/safety-inputs/results/report.md + summary.json.

## Claim discipline

SYNTHETIC ONLY. No sensor, microphone, camera, speaker, person, field, or
learned-model qualification; no QIP class/conformance claim; QIP-R9.1
traceability status unchanged (UNIMPLEMENTED in profile terms).

## Verification (attempt 1 of max 3)

- Attempt 1: initial full `make test` hit a collection collision (duplicate
  test_harness.py basename + `generate` module name vs research/adversarial);
  fixed within the owned paths by renaming the test module and loading
  generate.py by path. No second/third attempt needed for CI failures beyond
  this local fix if PR CI is green.
- Local: `make test` = 148 passed, 1 skipped (Python 3.11 venv, Rust core built).
- Determinism: generate.py + harness.py run twice, sha256sum -c OK for all
  datasets and summary.json.

## PR

PR #31 https://github.com/quberon/quberon-core/pull/31 — CI green on attempt 1
(dependency-review pass, python-without-rust pass 54s, rust-and-python pass
5m28s), self-merged as 6433a53. Ancestry verified post-merge:
`git merge-base --is-ancestor 35ee2ae origin/main` OK and
`git merge-base --is-ancestor 30a176b origin/main` OK.
