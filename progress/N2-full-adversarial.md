# N2-full-adversarial — progress (Wave 4)

Node: Wave4 N2 full adversarial | Owns: research/adversarial/** only
(progress/N2-full-adversarial.md is this node's own progress file;
progress/n7-requests.md appended only for routed escapes, below)
Base: origin/main baa18a1522aeb9dc5865afbbfffe89fc94de2ece
Spec: docs/specs/M2-ADVERSARIAL-CORPUS.md (Wave 3 pilot: progress/N5-adversarial.md)

## WEAK EVIDENCE (prominent, also in evidence header)

Templates and validator were authored by the same agent: this is WEAK
evidence. Real-model adversary BLOCKED: application META_API_URL /
META_MODEL absent (presence-checked, values never printed); Hermes
credential never reused. Independent-model architecture retained
(separate generate step, offline run) but corpus is templates.

## Scale executed (attempt 1 aliasing flaw found and fixed, attempt 2 final)

- generate.py: 500/class x 13 = 6,500 template cases (evidence/generate-full.txt)
- mutate.py via run.py: 50,000 deterministic mutations, executed
  through the actual /plan endpoint (pilot was direct-only)
- Total: 56,506 cases (+6 hand-written), 56,332 unique (0.31% dup)
- Results: 63,012 (generated+hand direct+endpoint; mutations endpoint)
- States (per-case by SHA-256 of case ID, decoupled from subclass
  cycle after attempt 1 exposed positional aliasing): latched,
  unlatched, persistence-degraded, secure-core-unavailable,
  secure-core-rejecting — all covered (~12.5k results each)
- Wall: 85.32 s (evidence/full-run.txt)

## Results (exact, results/summary.json)

- S0 violations: 0 (I4/I5/I7 0/63,012). Runner stops immediately on S0; none occurred.
- Accepted-in-error: 0
- Benign false-reject: 0 / 22,692 acceptance-permitted expect-accept
  results (0.0); I10 0 violations. Latched/persistence-degraded benign
  rejections are latch-held by design, excluded from the rate.
- Escapes: 300 records / 200 payloads, endpoint-only, no fix in this
  node (app/main.py outside ownership), routed to n7-requests:
  A. 100x NaN payloads -> HTTP 500 (I1 S2 + I2 S1), all five states.
  B. 100x 100k-summary payloads -> >64KB echoed response (I8 S3).
- Non-escape finding: validate_plan ignores all extra fields incl.
  forged secure_core/stop_latched fields (accept-as-proposal only,
  exact capability mapping, no latch/adapter/audit/core effect).

## Evidence

research/adversarial/evidence/adversarial-full.md — all seven M2
sections (header, by class, by invariant, escapes with every case ID,
over-blocking, limitations, reproduce), weak-evidence + BLOCKED banner
first. Raw: evidence/{generate-full,full-run}.txt,
results/{results.jsonl,summary.json}.

## Verification

- .venv/bin/python -m pytest research/adversarial/tests/ -q -> 12 passed
- make test -> 70 passed, 11 skipped (exit 0)
- Attempts used: 2 of 3 (attempt 1: positional state rotation aliased
  subclasses to single states; fixed by case-ID hash, no gate weakened)

## Routed (progress/n7-requests.md)

Escape A (NaN 500) and Escape B (oversize echo) fix requests for the
app/main.py owner, with suggested fixes and regression corpus IDs.
