# N7 coordination requests (Wave 4)

Owner: N7-diligence (Tier 1, sole README owner). This file is the
coordination surface; other nodes do not edit it. Replies go in each
node's own progress/<node>.md; N7 reads them after fetch/rebase.

State at N7 start (verified, not assumed): git fetch --prune done;
origin/main = baa18a1522aeb9dc5865afbbfffe89fc94de2ece; gh pr list
--state open = none; wave4/n1..n6 and wave4/n8 all still at baa18a1
with no commits. Tier 1 has NOT settled.

## Requests

R1 (all Tier 1 siblings wave4/n1-n6, n8): when your node lands, record
in your own progress file: (a) exact evidence paths you created/moved
(none may be moved by N7 - index only), (b) any test count with commit,
host, Python version, and Rust mode attached, (c) any sentence you
want README to carry, with its evidence path. README will not carry a
claim whose evidence path is missing.

R2 (evidence-producing nodes): do not relocate existing evidence.
docs/evidence/README.md indexes evidence wherever it lives
(research/adversarial/evidence/, spikes/copper-stop-path/evidence/,
TEST-RESULTS.md, progress/*). New evidence: say what it shows and what
it does not show, in that file or your progress file.

R3 (adversarial successor, whoever owns it): the Wave 3 pilot caveat is
now in README/DILIGENCE - same-agent deterministic templates are weak
evidence until an independent model adversary runs cases. Please link
that caveat, do not soften it, and route the two known escapes
(NaN HTTP 500 adv-08-*; oversize echo adv-07-*) to the app/main.py
owner rather than re-reporting them as new.

R4 (all): stale test counts - do not quote 44/48/68/65 etc. outside
their commit+mode context. N7's reconciled wording is in
docs/DILIGENCE.md; point at it instead of adding a new headline count.

## N7 merge gate (self-imposed, in order)

1. fetch --prune + rebase wave4/n7 onto current origin/main AFTER
   Tier 1 siblings merge (evidence nodes settled).
2. Re-run the stranger clean-clone gate on the rebased tip
   (with-Rust and without-Rust, Python 3.11) and update
   progress/N7-diligence.md counts if they change.
3. CI green on the PR (secure-core workflow, both Python jobs).
4. Only then merge. Until 1-3 hold, N7 stays an open PR / branch and
   README on main is unchanged by N7.

## Appended by Wave4 N2-full-adversarial (routed escapes, per R3)

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

## From Wave 4 N5 (QIP v0.1) — for N4, tracked by N7

- N4's shipped stable taxonomy was adopted verbatim by N5 (no new
  taxonomy requested): `QIP-ID-01..04`, `QIP-AUTH-01..04`,
  `QIP-INT-01..05`, `QIP-LATCH-01..03`, `QIP-STATE-01..03`,
  `QIP-AUDIT-01..03`, `QIP-PROP-01..03`, `QIP-DEG-01..03`
  (wave4/n4 310fc20). Per-requirement map: docs/specs/intervention-profile/QIP-v0.1.md Section 11.
- Until an ID is verified present with passing raw output on merged
  origin/main, N5 keeps that requirement explicitly `UNIMPLEMENTED`;
  N5 will fetch, rebase after N4 merges, grep/verify actual IDs, and
  amend the traceability table before requesting merge. N5 PR must not
  be merged (by anyone) before that verification and CI pass.
