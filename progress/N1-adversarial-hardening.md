# N1-adversarial-hardening — progress (Wave 4)

Node: Wave4 N1 | Tier 2 | Base: baa18a1522aeb9dc5865afbbfffe89fc94de2ece
Owns ONLY: app/main.py, integrations/meta.py, tests/test_adversarial_hardening.py,
this file. progress/n7-requests.md: not needed, not touched.
No Pi/hardware/blockchain/public claim. No merge.

## N5 findings hardened (actual, from progress/N5-adversarial.md + evidence)

A. adv-08-0002/0007/0012 NaN -> HTTP 500 (I1 S2/I2 S1).
   integrations/meta.py: find_nonfinite_values() (bounded iterative walk)
   rejects NaN/+Inf/-Inf in numeric AND string form ("NaN", "Infinity",
   "inf", overflowing "1e999") anywhere in the proposal with structured
   error "non-finite number not allowed". app/main.py /plan returns only
   sanitize_proposal(), so a non-finite value is never JSON-rendered back.
B. adv-07-0000/0005/0010 oversize summary -> 100,457B echoed response (I8 S3).
   sanitize_proposal(): allow-listed keys only, summary <=256 chars,
   caps <=4x32, hazards <=8x200, ids/action <=64, non-objects reduced to a
   type name, non-scalars omitted. Rejection/acceptance responses are
   therefore bounded (<64KB proven by tests and I8) and never reflect
   attacker large content beyond the bounded preview.
C. Finding (evidence sec.4): validate_plan ignored forged trusted fields.
   find_trusted_looking_fields() detects secure_core(.decision),
   stop_latched, provenance, source/source_status, timestamp, sequence,
   audit_record, decision, authorization, signature, issuer, verified,
   attestation etc. at any depth. Decision (per order wording
   "stripped/rejected from downstream-visible data"): the fields are
   stripped from every downstream-visible copy (endpoint proposal and
   validation.sanitized_proposal), flagged as
   provenance_forgery_attempt/trusted_fields_rejected, and never influence
   allowed_as_proposal, capabilities, latch, adapter, or secure core. The
   otherwise-valid advisory proposal is not over-blocked, matching the
   corpus expect-accept labels for adv-03/05/09/10. /plan writes exactly
   one plan-related audit event (action=PLAN_PROPOSAL, I6-compatible,
   auth_result=provenance_forgery_rejected, field paths only, never
   attacker values) per forgery attempt. Benign plans write no audit event;
   benign extra fields are stripped but not audited or rejected.

## Regression tests (tests/test_adversarial_hardening.py, 28 tests)

Named/derived from corpus IDs: adv-08-0002/0007/0012 (parametrized),
adv-08 string forms, adv-07-0000/0005/0010, adv-03-0003, adv-03-0004,
adv-05-0004, adv-09-0003, adv-10-0001/0002/0003, nested provenance,
mut-00068-style benign extra field, benign control.

## Raw verification (attempt 1 of 3; no gate weakened)

- .venv/bin/python -m pytest tests/test_adversarial_hardening.py -q
  -> 28 passed
- N5 corpus re-run (unmodified harness, out/summary to /tmp):
  cases=5206 unique_payloads=5188 paths=direct,endpoint
  total_results=5412 escapes=0 overblocked=0 s0=0
  (baseline at baa18a1: 9 escapes; I1/I2/I8 now 0 violations, I10 0)
- Without Rust (no target/debug CLI): make test -> 97 passed, 11 skipped
- With Rust (cargo build --workspace): make test -> 108 passed
- Preserved named STOP fail-direction tests, both pass:
  test_stop_executes_without_secure_core_but_reset_does_not
  test_stop_rejected_by_secure_core_does_not_invoke_adapter -> 2 passed

## Attempts / limits

Attempt 1: two test-expectation fixes only (summary preview bound 256;
trusted fields stripped+audited rather than proposal-rejected, per order
wording and corpus labels). No production gate weakened.
Limits: walk bounded at 4096 nodes/32 path depth for detection; sanitized
output drops anything beyond allow-list regardless. String-form detection
covers exact non-finite tokens and numeric strings that overflow float.
