# N5-adversarial — progress

Node: N5-adversarial | Owns: research/adversarial/** only
(progress/N5-adversarial.md is this node's own progress file)
Base: origin/main aab6496699490f8deb15edd67fc65f481200e33a
Spec: docs/specs/M2-ADVERSARIAL-CORPUS.md; harness: docs/specs/GRAPH-HARNESS.md
Ownership ruling (continuation): pilot evidence at
research/adversarial/evidence/adversarial-pilot.md — NOT docs/evidence.
No live-provider claim anywhere in this node.

## Mandatory order — executed in order

1. Invariants + unit tests + deliberately failing fixture proof FIRST
   - research/adversarial/invariants.py (I1-I10, one pure function each)
   - research/adversarial/tests/test_invariants.py (one failing fixture
     per invariant; all 10 proven able to fail)
   - Raw proof: research/adversarial/evidence/invariant-failing-fixtures.txt
     (I1..I10 each fail with specific detail; good fixture passes all 10)
   - pytest: 8 passed at that step (now 11 with harness tests)
2. run.py / mutate.py on hand cases
   - research/adversarial/corpus/hand-written.jsonl (6 cases)
   - Raw: research/adversarial/evidence/hand-run.txt
   - Result: 12 results (direct+endpoint), 0 escapes, 0 over-blocked
3. Generated + mutated pilot at scale
   - generate.py: 200 programmatic cases, 13 classes incl. benign
     control (15/class, 20 benign), seed 20261105, dedup by SHA-256
     (duplicates_adjusted=0 after deterministic case tagging;
     raw: evidence/generate.txt)
   - mutate.py via run.py --mutations 5000: exactly 5,000 mutations
   - Raw: evidence/full-run.txt, results/results.jsonl, results/summary.json
   - Totals: 5,206 cases, 5,188 unique payloads (0.35% dup),
     5,412 results, 0 S0, 9 escape records, 0 over-blocked

## Results (exact)

- S0 violations: 0 (I4 latch, I5 adapter, I7 secure-core: 0/5,412 each)
- Accepted-in-error: 0 (all classes, both paths; mutations 1,595/1,595
  expect-reject rejected)
- Benign control: 44/44 results accepted; false-reject rate 0%
- Escapes (all endpoint-only, none fixed in N5 — app/main.py is outside
  N5 ownership; routed, not hidden):
  A. adv-08-0002/0007/0012 NaN payload -> HTTP 500 (I1 S2, I2 S1).
     Root cause: proposal with float('nan') fails Starlette JSON
     rendering. Probe: evidence/nan-root-cause.txt
  B. adv-07-0000/0005/0010 oversize summary -> 100,457B response (I8 S3).
     Root cause: /plan echoes the untrusted proposal verbatim.
- Finding (not an invariant escape): validate_plan ignores all extra
  fields incl. forged secure_core/stop_latched fields on otherwise
  valid proposals. Documented in evidence section 4.

## Files

research/adversarial/invariants.py, generate.py, mutate.py, run.py
research/adversarial/tests/test_invariants.py, tests/test_harness.py
research/adversarial/corpus/class-01..13-*.jsonl, hand-written.jsonl, mutations.jsonl
research/adversarial/results/results.jsonl, summary.json, hand-results.jsonl, hand-summary.json
research/adversarial/evidence/adversarial-pilot.md (all 7 sections, pilot-scaled)
research/adversarial/evidence/{invariant-failing-fixtures,hand-run,generate,full-run,nan-root-cause}.txt

## Verification

- .venv/bin/python -m pytest research/adversarial/tests/ -q -> 11 passed
- make test -> see PR / evidence (full repo suite)
- Offline reproducibility commands in adversarial-pilot.md section 7.

## Decisions / limits

- Pilot scale (~200 / ~5,000) per continuation instruction, not spec
  full scale (6,500 / 50,000): stated in evidence, not inflated.
- Generator is programmatic templates: no model, no live provider.
- Endpoint fed raw payloads through a stub provider (validator is the
  system under test); latch set unlatched on the throwaway instance so
  I10 is measurable.
- Two mutation-expectation labelling corrections were made before the
  final run (optional-field deletion = accept by design; caps length
  >4 = reject per validator bound), visible in mutate.py.
- Attempts used: 1 of 3 (mutation uniqueness needed two deterministic
  expansions within the attempt; no gate was weakened).
