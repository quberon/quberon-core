# n7-requests — routed requests from other nodes

## From Wave4 N2-full-adversarial (research/adversarial/**)

Both items are defects in app/main.py (outside N2 ownership). Full
detail: research/adversarial/evidence/adversarial-full.md section 4.
Regression coverage: re-run research/adversarial/run.py after the fix;
the named corpus cases should stop failing.

1. NaN payload -> HTTP 500 on POST /plan (I1 S2, I2 S1)
   Cases: adv-08-0002, adv-08-0007, ..., adv-08-0497 (100 cases,
   every 5th from 0002) in corpus/class-08-malformed-nonobject-json.jsonl.
   Root cause: endpoint returns parsed proposal containing float('nan');
   Starlette JSON rendering raises ValueError. Suggested fix:
   allow_nan-safe serialization or reject non-finite floats in the
   proposal before returning it.
2. Oversize proposal echoed over 64 KB on POST /plan (I8 S3)
   Cases: adv-07-0000, adv-07-0005, ..., adv-07-0495 (100 cases)
   in corpus/class-07-oversize-resource.jsonl. Root cause: /plan
   returns the full untrusted proposal verbatim. Suggested fix:
   truncate or omit long proposal fields in the response.
