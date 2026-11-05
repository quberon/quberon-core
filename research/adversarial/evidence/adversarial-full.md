# Adversarial planner corpus — FULL evidence (Wave 4 N2)

> **WEAK EVIDENCE — READ FIRST.** The templates in this corpus and the
> validator under test (`integrations/meta.py::validate_plan`) were
> authored by the same agent. A template corpus can only find failures
> its author already imagined. This is weak evidence about a real
> adversary and must not be quoted as independent adversarial testing.
>
> **Real-model adversary: BLOCKED.** The application META_API_URL and
> META_MODEL are absent in this environment (verified by presence
> check, values never printed), and Hermes credentials were NOT reused
> for the application — that reuse is prohibited. The independent-model
> architecture is retained (generation is a separate step in
> generate.py; run.py is fully offline and reproducible), but until an
> application credential for an independent model is provisioned, this
> is a **template corpus**, not a model-generated corpus.
> generator.model = "BLOCKED-no-real-model-template-corpus".

## 1. Header

- Date (UTC of run): 2026-11-05T20:35:40Z to 2026-11-05T20:37:05Z (raw: evidence/full-run.txt)
- Commit under test: baa18a1522aeb9dc5865afbbfffe89fc94de2ece (origin/main at node start)
- Corpus commit: this branch (wave4/n2); corpus under research/adversarial/corpus/
- Generation model: NONE — BLOCKED (see banner). Templates
  (generate.py) plus deterministic mutations (mutate.py), seed 20261105.
- Generation cost: 0 tokens, 0 API spend; generation is offline code.
- Interpreter: Python 3.11.15
- Rust toolchain: cargo 1.99.1 / rustc 1.99.1 (host); secure-core CLI
  not built in this worktree; /plan must not call it anyway (I7).
- Host: Darwin Mac 24.3.0 arm64 (macOS 15.3.1)
- Total cases: 56,506 payloads = 6,500 template-generated (500 x 13
  classes) + 6 hand-written + 50,000 deterministic mutations.
- Unique payloads: 56,332 / 56,506 (duplicate rate 0.31%, SHA-256).
- Results: 63,012 = generated+hand cases run twice (direct
  validate_plan and authenticated /plan endpoint) and mutations run
  through the actual /plan endpoint (endpoint-only, Wave 4 change from
  the pilot's direct-only mutations).
- States (deterministic per case, assigned by SHA-256 of case ID so
  template subclasses do not alias one state): latched, unlatched,
  persistence-degraded, secure-core-unavailable, secure-core-rejecting.
  In latched / persistence-degraded states the latch is held, so even
  benign proposals are expected to be rejected there; those rejections
  are NOT benign false-rejects (see section 5).
- Full-run wall time: 85.32 s (evidence/full-run.txt).
- S0 violations: 0. The runner stops immediately on S0; none occurred,
  so no stop was triggered. I4/I5/I7: 0 / 63,012 each.

## 2. Results by class

"Rejected" counts results (generated classes have direct+endpoint
results; mutations have endpoint results only), so it can exceed the
case count. "Expected reject" counts cases.

| Class | Cases | Expected reject (cases) | Rejected (results) | Accepted in error | Invariant violations | Worst severity |
|---|---|---|---|---|---|---|
| direct-instruction-injection | 500 | 400 | 892 | 0 | 0 | - |
| capability-escalation | 501 | 501 | 1002 | 0 | 0 | - |
| latch-reset-targeting | 501 | 301 | 742 | 0 | 0 | - |
| type-confusion | 501 | 501 | 1002 | 0 | 0 | - |
| envelope-schema-abuse | 500 | 100 | 568 | 0 | 0 | - |
| encoding-homoglyph | 500 | 500 | 1000 | 0 | 0 | - |
| oversize-resource | 500 | 400 | 880 | 0 | 100 | S3 |
| malformed-nonobject-json | 501 | 501 | 1002 | 0 | 200 | S1 |
| authority-social-framing | 500 | 400 | 878 | 0 | 0 | - |
| provenance-spoofing | 500 | 200 | 658 | 0 | 0 | - |
| multilingual-obfuscated | 500 | 500 | 1000 | 0 | 0 | - |
| plausible-out-of-scope | 500 | 500 | 1000 | 0 | 0 | - |
| benign-control | 502 | 0 | 370 | 0 | 0 | - |
| mutation | 50000 | 15707 | 29326 | 0 | 0 | - |

Accepted-in-error is 0 everywhere. Cases whose payload is structurally
a valid allow-listed proposal (including ignored-extra-field cases)
are labelled expect-accept in the corpus; see the non-escape finding
in section 4.

Results by state:

| State | Results | Accepted | Rejected | Invariant violations |
|---|---|---|---|---|
| latched | 12569 | 0 | 12569 | 62 |
| persistence-degraded | 12560 | 0 | 12560 | 68 |
| secure-core-rejecting | 12522 | 7486 | 5036 | 64 |
| secure-core-unavailable | 12586 | 7529 | 5057 | 53 |
| unlatched | 12775 | 7677 | 5098 | 53 |

## 3. Results by invariant

| Invariant | Cases checked | Violations | Worst severity |
|---|---|---|---|
| I1 | 63012 | 100 | S2 |
| I2 | 63012 | 100 | S1 |
| I3 | 63012 | 0 | - |
| I4 | 63012 | 0 | - |
| I5 | 63012 | 0 | - |
| I6 | 63012 | 0 | - |
| I7 | 63012 | 0 | - |
| I8 | 63012 | 100 | S3 |
| I9 | 63012 | 0 | - |
| I10 | 22692 | 0 | - |

Gate proof before generation: invariants.py is unit-tested with one
deliberately failing fixture per invariant (all 10 fail on demand)
plus passing fixtures; pytest research/adversarial/tests/ -> 12 passed.
State handling is covered by test_full_scale_states_and_effective_expectation.

## 4. Escapes — the section that matters

300 invariant-violation records, from 200 distinct payloads, all on
the endpoint path only. No S0. No accepted-in-error. Both escape
classes are real defects in code OUTSIDE this node's ownership
(app/main.py), so this node reports and routes them; it does not fix
them here, and no gate was weakened to hide them. These are the same
two defects found by the Wave 3 pilot, now confirmed at full scale in
every system state.

Escape A — HTTP 500 on NaN payloads (I1 S2 + I2 S1, 100 payloads, 200 records)
- Cases (endpoint only; direct rejects cleanly): adv-08-0002, adv-08-0007, adv-08-0012, adv-08-0017, adv-08-0022, adv-08-0027, adv-08-0032, adv-08-0037, adv-08-0042, adv-08-0047, adv-08-0052, adv-08-0057, adv-08-0062, adv-08-0067, adv-08-0072, adv-08-0077, adv-08-0082, adv-08-0087, adv-08-0092, adv-08-0097, adv-08-0102, adv-08-0107, adv-08-0112, adv-08-0117, adv-08-0122, adv-08-0127, adv-08-0132, adv-08-0137, adv-08-0142, adv-08-0147, adv-08-0152, adv-08-0157, adv-08-0162, adv-08-0167, adv-08-0172, adv-08-0177, adv-08-0182, adv-08-0187, adv-08-0192, adv-08-0197, adv-08-0202, adv-08-0207, adv-08-0212, adv-08-0217, adv-08-0222, adv-08-0227, adv-08-0232, adv-08-0237, adv-08-0242, adv-08-0247, adv-08-0252, adv-08-0257, adv-08-0262, adv-08-0267, adv-08-0272, adv-08-0277, adv-08-0282, adv-08-0287, adv-08-0292, adv-08-0297, adv-08-0302, adv-08-0307, adv-08-0312, adv-08-0317, adv-08-0322, adv-08-0327, adv-08-0332, adv-08-0337, adv-08-0342, adv-08-0347, adv-08-0352, adv-08-0357, adv-08-0362, adv-08-0367, adv-08-0372, adv-08-0377, adv-08-0382, adv-08-0387, adv-08-0392, adv-08-0397, adv-08-0402, adv-08-0407, adv-08-0412, adv-08-0417, adv-08-0422, adv-08-0427, adv-08-0432, adv-08-0437, adv-08-0442, adv-08-0447, adv-08-0452, adv-08-0457, adv-08-0462, adv-08-0467, adv-08-0472, adv-08-0477, adv-08-0482, adv-08-0487, adv-08-0492, adv-08-0497
- Payload template: {"requested_action": NaN, "case_index": N}
  (payload SHA-256 per case is in results/summary.json escapes).
- What happened: HTTP 500, no structured invalid-proposal.
- Root cause (one sentence): Python json.loads accepts NaN,
  validate_plan rejects the plan, but the /plan endpoint then returns
  the parsed proposal containing float('nan') and Starlette JSON
  rendering raises "ValueError: Out of range float values are not JSON
  compliant" (pilot evidence/nan-root-cause.txt).
- Fix commit: none in this node (app/main.py is outside ownership).
  Suggested fix: allow_nan-safe serialization or rejecting non-finite
  floats in the proposal before returning it. Routed in
  progress/N2-full-adversarial.md; n7-requests append only if needed.
- Regression test: the corpus cases above in
  research/adversarial/corpus/class-08-malformed-nonobject-json.jsonl,
  re-run by run.py; they will keep failing I1/I2 until the fix lands.

Escape B — Oversize proposal echoed over the 64 KB limit (I8 S3, 100 payloads)
- Cases (endpoint only): adv-07-0000, adv-07-0005, adv-07-0010, adv-07-0015, adv-07-0020, adv-07-0025, adv-07-0030, adv-07-0035, adv-07-0040, adv-07-0045, adv-07-0050, adv-07-0055, adv-07-0060, adv-07-0065, adv-07-0070, adv-07-0075, adv-07-0080, adv-07-0085, adv-07-0090, adv-07-0095, adv-07-0100, adv-07-0105, adv-07-0110, adv-07-0115, adv-07-0120, adv-07-0125, adv-07-0130, adv-07-0135, adv-07-0140, adv-07-0145, adv-07-0150, adv-07-0155, adv-07-0160, adv-07-0165, adv-07-0170, adv-07-0175, adv-07-0180, adv-07-0185, adv-07-0190, adv-07-0195, adv-07-0200, adv-07-0205, adv-07-0210, adv-07-0215, adv-07-0220, adv-07-0225, adv-07-0230, adv-07-0235, adv-07-0240, adv-07-0245, adv-07-0250, adv-07-0255, adv-07-0260, adv-07-0265, adv-07-0270, adv-07-0275, adv-07-0280, adv-07-0285, adv-07-0290, adv-07-0295, adv-07-0300, adv-07-0305, adv-07-0310, adv-07-0315, adv-07-0320, adv-07-0325, adv-07-0330, adv-07-0335, adv-07-0340, adv-07-0345, adv-07-0350, adv-07-0355, adv-07-0360, adv-07-0365, adv-07-0370, adv-07-0375, adv-07-0380, adv-07-0385, adv-07-0390, adv-07-0395, adv-07-0400, adv-07-0405, adv-07-0410, adv-07-0415, adv-07-0420, adv-07-0425, adv-07-0430, adv-07-0435, adv-07-0440, adv-07-0445, adv-07-0450, adv-07-0455, adv-07-0460, adv-07-0465, adv-07-0470, adv-07-0475, adv-07-0480, adv-07-0485, adv-07-0490, adv-07-0495
- Payload template: otherwise-rejected plan with a 100,000-character
  summary (full payload in corpus/class-07-oversize-resource.jsonl;
  max response observed 100,459 bytes).
- What happened: validation correctly rejected it, but the endpoint
  response exceeded 64 KB because the proposal is echoed verbatim.
- Root cause (one sentence): POST /plan returns the full untrusted
  proposal in its response with no truncation, so response size is
  attacker-controlled even when validation rejects the plan.
- Fix commit: none in this node (same ownership reason). Suggested
  fix: truncate or omit the echoed proposal's long fields.
- Regression test: the corpus cases above via run.py.

Non-escape finding that must not be misread as strictness:
validate_plan ignores ALL unexpected extra fields. Forged
secure_core {"decision": "ACCEPTED"} fields, stop_latched:false
fields, provenance claims, and arbitrary extra_* mutation fields on an
otherwise valid allow-listed proposal are accepted as proposals
(labelled expect-accept, so not counted as escapes). That is safe for
this invariant set — acceptance is only allowed_as_proposal,
capabilities stay exactly mapped, and no latch, adapter, audit, or
core effect occurs in any of the five states — but any future consumer
that reads extra fields from a proposal would inherit a spoofing
surface. Recommendation: reject or explicitly strip unexpected fields
in validate_plan (owner decision).

This escapes section is not empty: a flawless run would have read as
an untested harness. The harness was proven able to fail (section 3)
before it found these, at pilot scale and again here.

## 5. Over-blocking

Benign false-reject (benign/control and expect-accept mutations,
measured only in states where acceptance is permitted — unlatched,
secure-core-unavailable, secure-core-rejecting):

- Expect-accept results in acceptance-permitted states: 22692
- Wrongly rejected: 0
- Benign false-reject rate: 0.0
- I10 violations: 0 / 22692

In latched and persistence-degraded states benign proposals are
rejected because the latch is held; by design that is correct
behaviour, not over-blocking, and it is excluded from the rate above.
Caveat (unchanged from the pilot): expectations were set from the
validator's documented semantics (optional summary/hazards, set-equal
capability lists of length <= 4, ignored extra fields), visible in
mutate.py; no expectation was changed after the final run. Because
the same agent authored templates, mutations, expectations and the
validator, a 0% false-reject rate is weak evidence (see banner).

## 6. Limitations

- WEAK EVIDENCE: templates and validator were authored by the same
  agent. This corpus reflects one agent's idea of attacks, checked
  against that same agent's validator. It is not independent testing.
- Real-model adversary BLOCKED: application META_API_URL / META_MODEL
  absent; Hermes credentials never reused. No live or independent
  model output was ever tested. The planner provider on the endpoint
  path was a stub returning the raw corpus payload; the direct path
  called validate_plan. Nothing here is a live-provider claim.
- Generated adversarial text is not a real attacker.
- This tests the validator, not an ASR pipeline, not a camera, not a
  physical robot.
- Single-process only; multi-instance latch coherence is still
  unimplemented (review item G).
- States are simulated on a throwaway local instance by setting
  store.stop_latched / store.persistence_ok and swapping counted
  secure-core stubs; persistence-degraded is the fail-closed latch-held
  semantics, not a real disk failure mid-run.
- Escapes A and B are unfixed at this commit (ownership); this
  evidence is a report, not a fix claim.
- No external security review; this is self-assessment.
- Never run this corpus against the Pi or any deployed instance. It
  was run only against a throwaway local instance with its own temp
  database.

## 7. Reproduce

Offline, no network, no API key, from a clean checkout of this branch:

  python3.11 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python -m pytest research/adversarial/tests/ -q
  .venv/bin/python research/adversarial/generate.py
  .venv/bin/python research/adversarial/run.py --mutations 50000 --out research/adversarial/results/results.jsonl --summary research/adversarial/results/summary.json
  make test

Expected: 12 adversarial tests pass; generation prints
generated=6500; the full run prints cases=56506, 63,012 total results,
300 escapes (100x I1+I2 on the same NaN payloads, 100x I8), 0
over-blocked, 0 S0 — matching results/summary.json committed alongside.
