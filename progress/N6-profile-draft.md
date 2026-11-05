# N6 profile draft — gate zero

Status: complete for prior-art and traceability gate zero; full N6 profile gate remains blocked on N4 manufacturer-interface evidence.

Base: `origin/main` at `aab6496699490f8deb15edd67fc65f481200e33a`.

## Outputs

- `docs/specs/intervention-profile/PRIOR-ART.md`
- `docs/specs/intervention-profile/OUTLINE.md`
- `docs/specs/intervention-profile/TRACEABILITY.md`
- `progress/N6-profile-draft.md`

## Deterministic gate evidence

- Prior-art entries include a source URL and an explicit review-depth marker.
- Each paywalled standards entry uses the exact marker `scope and abstract reviewed; full text not reviewed`; detailed clause/threshold claims are excluded.
- Outline contains R1-R11 and is explicitly non-normative.
- Traceability maps each R1-R11 item to exact existing test function names or an explicit gap.
- `research/humanoids/registry/api-surfaces.jsonl` is zero bytes at this base, so R10 and all observed-manufacturer-interface conclusions remain gaps.
- No files outside `docs/specs/intervention-profile/**` and `progress/N6-profile-draft.md` are owned or modified by this node.
- Deterministic verification on resume (2026-11-05): all 37 distinct `tests/...::test_*` references in TRACEABILITY.md resolve to existing `def` definitions (0 missing); `make test` = 65 passed.
- Two dead source URLs found on resume were replaced with live official sources (MassRobotics official GitHub repository; Open-RMF at openrmf.readthedocs.io). ISO catalogue URLs return 403 to automated clients (bot protection); they are the canonical iso.org standard pages and are retained with the paywalled marker only.

## Findings

The repository already tests several intervention design decisions: scoped identity, authentication, prioritization, idempotency, latch/reset separation, acknowledgement versus observation, unavailable authority versus reachable refusal, evidence capture, and conservative voice/gesture handling. These tests are useful trace evidence but are not physical safety validation or standards conformity.

N4-dependent conclusions were not fabricated. The full N6 gate cannot be accepted as a normative manufacturer-grounded profile until the manufacturer-interface matrix exists and is reviewed. Gate zero records the prior art, the outline, the exact test evidence, and the gaps needed for that later work.
