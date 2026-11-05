# Local voice-STOP & gesture-STOP: training / evaluation roadmap

Scope: research & offline evaluation only. Models may only ever *propose*
STOP into the existing authenticated intervention path. They must never
reset/unlatch, resume, start tasks, or command motion. The deterministic
recognizers in integrations/recognizers.py remain the reference baseline;
any learned model is shadow-mode until a human deployment gate passes.
SIMULATED ROBOT — NOT AN EMERGENCY STOP.

## Targets (acceptance thresholds to validate, not achieved results)
Define per release candidate, measured on held-out + field-like sets:
- False-negative (missed STOP) rate: target < 1% overall and < 2% in every
  reported subgroup; a missed STOP is the highest-severity error.
- False-positive (spurious STOP) rate: target < 1 per 8 operating hours in
  negative streams (conversation, media playback, similar words/gestures).
- Abstention: model must abstain (no action) under low confidence/OOD;
  abstention rate reported, never silently converted to accept/reject.
- Latency: on-device decision budget to be set from baseline measurements;
  report p50/p95. No cloud round-trip for the STOP path.
These are targets to test against — publishing them is not claiming them.

## Coverage matrix (report metrics per cell, no aggregate-only claims)
Voice: languages starting Swedish + English, then expand by speaker pool;
accents/dialects, age bands, speech impairments where consented, distance
(0.5/1/3/5 m), noise (quiet, household, street, factory-like, music/TV),
microphone types, shouted vs normal STOP, negations ("do not stop"),
homophones and media speech as negatives.
Gesture: open-palm baseline (existing 21-landmark contract); handedness,
skin tones, sleeves/gloves, lighting/backlight, occlusion, camera angle,
distance, mobility differences, holding objects as negatives, other raised-
hand gestures as hard negatives.

## Data governance
- Only consented recordings or datasets with verified licence + documented
  consent basis (see dataset schema privacy fields). Unknown = no training.
- No downloaded copyrighted video; no scraping against terms. Synthetic and
  self-recorded consented data preferred for Phase 4 collection.
- Consent records, withdrawal/deletion path, retention limits, minors:
  excluded unless a specific approved protocol exists. Voiceprints: treat
  as biometric-adjacent — minimise, store landmarks/embeddings policy TBD
  by GDPR research (see legal roadmap), never identify speakers.
- Dataset cards (research/humanoids/cards/) mandatory before training.

## Training & reproducibility
Local training only; pinned deps, seeds, data hashes, config in git (no data
in git). Train/val/test split by speaker/person (no identity leakage across
splits). Version every model + card together. Baseline comparisons:
current deterministic voice matcher (conf >= 0.85, final transcript) and
open-palm geometry recognizer (>=0.8 visibility, >=3 frames, >=700 ms).

## Evaluation harness (offline first)
1) Replay recorded consented sets through recognizers; score FN/FP/abstain
per coverage cell with confidence intervals. 2) Adversarial negatives:
negations, "nonstop"-type near misses, TV speech, waving vs held palm.
3) Stale/replayed inputs must stay rejected by the existing service —
models do not get a separate channel. 4) Failure injection: mic/camera
dropout, corrupt frames => abstain + UNKNOWN, never success.

## Fail-closed deployment (if ever approved)
Shadow mode -> advisory log-only -> gated proposer into execute_stop only.
Any uncertainty, model/load failure, or drift alarm => feature disables
itself (abstention), latch state unaffected, observed state UNKNOWN.
Human approval record + rollback required per gate; no automatic promotion.
Periodic re-evaluation on fresh consented data; subgroup regressions block
promotion. This roadmap authorises no deployment by itself.
