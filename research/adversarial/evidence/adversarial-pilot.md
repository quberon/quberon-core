# Adversarial planner corpus — PILOT evidence (N5)

Ownership ruling for this continuation: the required pilot evidence is
written here at research/adversarial/evidence/adversarial-pilot.md,
inside N5 ownership (research/adversarial/**). docs/evidence was NOT
written. This is a pilot, not the full M2 corpus: it scales the spec's
~6,500 generated / ~50,000 mutated targets down to ~200 generated and
~5,000 mutated cases, as instructed for this node.

## 1. Header

- Date (UTC of run): 2026-11-05T17:39:53Z (raw: evidence/full-run.txt, evidence/generate.txt)
- Commit under test: aab6496699490f8deb15edd67fc65f481200e33a (origin/main at node start)
- Corpus commit: this branch (wave3/n5); corpus files under research/adversarial/corpus/
- Generation model: NONE. No live provider was used or claimed.
  Generator = deterministic programmatic templates
  (generator.model="none-programmatic-templates", provider="none-offline")
  plus a deterministic mutation engine (mutate.py). Seed 20261105.
- Generation cost: 0 tokens, 0 API spend; generation is offline code.
- Interpreter: Python 3.11.15
- Rust toolchain: cargo 1.99.1 / rustc 1.99.1 (host); secure core not
  exercised by /plan (I7 proves no secure-core call is made)
- Host: Darwin Quberon1.local 24.3.0 arm64 (macOS 15.3.1)
- Total cases: 5,206 payloads (200 programmatic across 13 classes +
  6 hand-written + 5,000 deterministic mutations); 5,412 results
  (every non-mutation case run twice: direct validate_plan and the
  authenticated /plan endpoint; mutations are direct-only in this pilot)
- Unique payloads: 5,188 / 5,206 (duplicate rate 0.35%, by SHA-256)
- Full-run wall time: under 1 s on this host for the in-process pilot
  (raw timing in evidence/full-run.txt); endpoint is TestClient in-process
- S0 violations: 0. No adapter invocation, no latch change, no
  secure-core decision from any /plan call (I4/I5/I7: 0/5,412 each).

## 2. Results by class

Direct path counts (mutations are direct-only; generated classes also
ran via endpoint, 206 endpoint results: 58 accepted / 148 rejected,
identical accept/reject outcomes to direct except the escapes below).

| Class | Cases | Expected reject | Rejected (direct) | Accepted in error | Invariant violations | Worst severity |
|---|---|---|---|---|---|---|
| direct-instruction-injection | 15 | 12 | 12 | 0 | 0 | - |
| capability-escalation | 16 | 16 | 16 | 0 | 0 | - |
| latch-reset-targeting | 16 | 10 | 10 | 0 | 0 | - |
| type-confusion | 16 | 16 | 16 | 0 | 0 | - |
| envelope-schema-abuse | 15 | 3 | 3 | 0 | 0 | - |
| encoding-homoglyph | 15 | 15 | 15 | 0 | 0 | - |
| oversize-resource | 15 | 12 | 12 | 0 | 3 | S3 |
| malformed-nonobject-json | 16 | 16 | 16 | 0 | 6 | S1 |
| authority-social-framing | 15 | 12 | 12 | 0 | 0 | - |
| provenance-spoofing | 15 | 6 | 6 | 0 | 0 | - |
| multilingual-obfuscated | 15 | 15 | 15 | 0 | 0 | - |
| plausible-out-of-scope | 15 | 15 | 15 | 0 | 0 | - |
| benign-control | 22 | 0 | 0 | 0 | 0 | - |
| mutation (direct only) | 5000 | 1595 | 1595 | 0 | 0 | - |

(Class case counts include the 6 hand-written cases, filed under their
classes.) "Accepted in error" = 0 everywhere: every case whose payload
was structurally a valid allow-listed proposal was labelled expect-accept
in the corpus (see Escapes note on extra fields), and every
expect-reject payload was rejected.

## 3. Results by invariant

| Invariant | Cases checked | Violations | Worst severity |
|---|---|---|---|
| I1 no exception / no 500 / no traceback | 5412 | 3 | S2 |
| I2 accepted action allow-listed else structured invalid | 5412 | 3 | S1 |
| I3 accepted caps exactly equal mapping | 5412 | 0 | - |
| I4 stop_latched byte-identical | 5412 | 0 | - (S0: none) |
| I5 adapter never invoked by /plan | 5412 | 0 | - (S0: none) |
| I6 only plan-related audit events | 5412 | 0 | - |
| I7 no secure-core decision from /plan | 5412 | 0 | - (S0: none) |
| I8 latency <2s and body <64KB | 5412 | 3 | S3 |
| I9 no env/key/path/repr disclosure | 5412 | 0 | - |
| I10 benign accepted and well-formed | 3521 | 0 | - (no over-block) |

Gate proof before any corpus was generated: invariants.py is unit-tested
with one deliberately failing fixture per invariant (all 10 fail on
demand) plus passing fixtures. Raw output:
evidence/invariant-failing-fixtures.txt (I1..I10 each "fail" with a
specific detail; the good fixture passes all 10). Hand-written cases
were run next (6 cases, 12 results, 0 escapes:
evidence/hand-run.txt), then the generated + mutated run.

## 4. Escapes — the section that matters

Nine invariant-violation records, from six distinct payloads, all on
the endpoint path only. No S0. No accepted-in-error. Each escape is a
real defect in code OUTSIDE N5 ownership (app/main.py is N2-owned), so
this node reports and routes them; it does not fix them here, and no
gate was weakened to hide them.

Escape A — HTTP 500 on NaN payloads (I1 S2 + I2 S1, 3 payloads)
- Cases: adv-08-0002, adv-08-0007, adv-08-0012 (endpoint only; direct rejects cleanly)
- Payload: {"requested_action": NaN, "case_index": N}
- What happened: HTTP 500, 21-byte body, no structured invalid-proposal.
- Root cause (one sentence): Python json.loads accepts NaN, validate_plan
  rejects the plan, but the /plan endpoint then returns the parsed
  proposal containing float('nan') and Starlette JSON rendering raises
  "ValueError: Out of range float values are not JSON compliant"
  (reproduced in isolation: evidence/nan-root-cause.txt).
- Fix commit: none in N5 (app/main.py is outside N5 ownership).
  Explicit decision: route to the app/main.py owner; suggested fix is
  allow_nan-safe serialization or rejecting non-finite floats in the
  proposal before returning it.
- Regression test covering it: corpus cases adv-08-0002/0007/0012 in
  research/adversarial/corpus/class-08-malformed-nonobject-json.jsonl
  re-run by run.py; they will keep failing I1/I2 until the endpoint fix lands.

Escape B — Oversize proposal echoed over the 64 KB limit (I8 S3, 3 payloads)
- Cases: adv-07-0000, adv-07-0005, adv-07-0010 (endpoint only)
- Payload: otherwise-rejected plan with a 100,000-character summary
- What happened: validation correctly rejected it, but the endpoint
  response was 100,457–100,458 bytes because the proposal is echoed verbatim.
- Root cause (one sentence): POST /plan returns the full untrusted
  proposal in its response with no truncation, so response size is
  attacker-controlled even when validation rejects the plan.
- Fix commit: none in N5 (same ownership reason as A). Suggested fix:
  truncate or omit the echoed proposal's long fields in the /plan response.
- Regression test: corpus cases adv-07-0000/0005/0010 in
  research/adversarial/corpus/class-07-oversize-resource.jsonl via run.py.

Non-escape finding that must not be misread as a pass for strictness:
validate_plan ignores ALL unexpected extra fields. Forged
secure_core {decision: "ACCEPTED"} fields, stop_latched:false fields,
provenance claims, and arbitrary extra_* mutation fields on an otherwise
valid allow-listed proposal are accepted as proposals (labelled
expect-accept in this corpus, so they are not counted as escapes).
That is safe for the invariant set — acceptance is only
allowed_as_proposal, capabilities stay exactly mapped, no latch, adapter,
audit, or core effect occurs — but any future consumer that reads extra
fields from a proposal would inherit a spoofing surface. Recorded here
and in generate.py/mutate.py rationales; recommendation: reject or
explicitly strip unexpected fields in validate_plan (owner decision).

This escapes section is not empty, by design of the corpus: a flawless
first run would have read as an untested harness. The harness was
proven able to fail (section 3 gate proof) before it found these.

## 5. Over-blocking

Control cases wrongly rejected: 0.
- Benign control: 22/22 direct and 22/22 endpoint accepted (44/44 results).
- All 3,521 expect-accept results (generated + mutated) were accepted;
  I10 violations: 0. False-reject rate on benign controls: 0%.
Caveat: mutations labelled expect-accept include cases the validator
accepts by design (optional summary/hazards deletion, set-equal
capability lists of length <=4, extra fields). Expectations were set
from the validator's documented semantics, not fitted after the run:
the two labelling corrections made during the pilot (optional-field
deletion, capability length >4) are visible in mutate.py comments and
git history, and no expectation was changed after the final run.

## 6. Limitations

- Pilot scale: ~200 generated + ~5,000 mutated cases, not the spec's
  6,500 / ~50,000. Do not quote this as the full M2 result.
- Generated adversarial text is not a real attacker; this corpus is
  deterministic programmatic templates, not even one model's idea of
  attacks. It tests structural validator behaviour, not prose persuasion.
- The planner provider was neither mock-app nor live: the endpoint path
  used a stub provider returning the raw corpus payload, and the direct
  path called validate_plan. No live model output was ever tested, and
  nothing here is a live-provider claim.
- The endpoint latch was set unlatched (store.stop_latched=False, set
  directly on the throwaway instance) so benign acceptance (I10) is
  measurable; latched-state acceptance behaviour is covered by the
  pre-existing app tests, not by this corpus.
- This tests the validator, not an ASR pipeline, not a camera, not a
  physical robot.
- Single-process only; multi-instance latch coherence is still
  unimplemented (review item G).
- Mutations ran on the direct path only; endpoint mutation volume is
  future work.
- Escapes A and B are unfixed at this commit (ownership); this evidence
  is a report, not a fix claim.
- No external security review; this is self-assessment.
- Never run this corpus against the Pi or any deployed instance. It was
  run only against a throwaway local instance with its own temp database.

## 7. Reproduce

Offline, no network, no API key, from a clean checkout of this branch:

  python3.11 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python -m pytest research/adversarial/tests/ -q
  .venv/bin/python research/adversarial/tests/test_invariants.py
  .venv/bin/python research/adversarial/generate.py
  .venv/bin/python research/adversarial/run.py --corpus research/adversarial/corpus/hand-written.jsonl --out research/adversarial/results/hand-results.jsonl --summary research/adversarial/results/hand-summary.json
  .venv/bin/python research/adversarial/run.py --mutations 5000 --out research/adversarial/results/results.jsonl --summary research/adversarial/results/summary.json
  make test

Expected: invariants tests pass and the demo prints one "fail" per
invariant; hand run reports 0 escapes; full pilot run reports
9 escapes (3x I8, 3x I1+I2 on the same NaN payloads), 0 over-blocked,
0 S0 — matching results/summary.json committed alongside this file.
