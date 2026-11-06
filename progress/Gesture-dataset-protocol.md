# Gesture dataset protocol (Wave 6) — Tier 1, research only

Base: origin/main 65f5271aa59d90a76ec53a0f0f6d750f9e566f4b
Owned paths only: research/gesture-dataset/** and this file.
No Pi/camera access, no app/control/endpoint/recognizer modification,
no model training, no sensor qualification claim (QIP-R9.3, R11.2).

## Deliverable
- research/gesture-dataset/README.md — capture/evaluation protocol:
  open-palm STOP positive class, negative controls, near-boundary cases,
  distance/lighting/occlusion/motion-blur/background variation,
  consecutive-frame/hold timing, stale/replay/duplicate/out-of-order
  frames, contradictory voice+gesture (separate-endpoint OR, STOP-only);
  folder layout, JSONL metadata schema, labelling rules, session/person/
  environment-grouped train/val/test split, consent/privacy handling,
  metrics with denominators (false/missed/abstention), acceptance gates
  G1-G7 tied to existing gesture/voice intervention endpoints
  (>=3 frames, >=700 ms, visibility >=0.8, stale >300 s, future >30 s,
  event_id replay, STOP-only/no-reset).
- research/gesture-dataset/schema.json — descriptive schema.
- research/gesture-dataset/validate.py — stdlib validator; fails on
  malformed JSON/fields/enums, inconsistent derived expectation,
  temporal-tag inconsistency, human capture without consent,
  pending/withdrawn consent, PII keys, and leakage (session/person/
  environment/frames_hash across splits, duplicate clip_id).
- research/gesture-dataset/examples/{generate_example.py,
  synthetic-example.jsonl} — 12 deterministic synthetic records
  (train/val/test 4/4/4), sha256 7f5fd02a9cf42fc4793cacfdca421fc40a780588b2e4ca68899abc6f2b98447f,
  byte-identical on regeneration (verified twice).
- research/gesture-dataset/tests/test_gesture_dataset_validator.py — 9 tests.

## Verification (attempt 1 of max 3)
- validate.py on example: OK: 12 records; splits={'train': 4, 'val': 4, 'test': 4}
- New tests: 9 passed (system python3, stdlib only).
- Full suite: make test = 199 passed, 12 skipped (python3.11 venv,
  requirements installed locally; .venv removed before commit, not tracked).
- Example generator run twice: identical sha256 (above).

## PR
PR: TBD (filled in on this branch before merge; see final report).
CI: TBD.
