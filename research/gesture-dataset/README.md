# Pi-camera gesture-recognition dataset protocol — RESEARCH ONLY (Tier 1)

Status: protocol + metadata validator + deterministic synthetic example only.
NO Pi/camera access, capture, model training, sensor/model qualification,
QIP class/conformance or physical-safety claim is made or implied
(QIP-v0.1 R9.3, R11.2; docs/specs/intervention-profile/QIP-v0.1.md §10).
Future capture requires separate human approval; this node must not be
used to authorise it. Existing recogniser/endpoint code is read, not changed.

## 1. Purpose and scope
Define, before any human image is collected, how a dataset for evaluating
the existing open-palm STOP path would be captured, labelled, split,
privacy-handled and scored — so a later, separately-approved capture can be
audited against a fixed protocol rather than retro-fitted to results.
System under evaluation (existing, unmodified):
- `OpenPalmStopRecognizer` (integrations/recognizers.py): 21 landmarks,
  every landmark visibility >= 0.8, upright extended geometry, >=3
  consecutive qualifying frames, >=700 ms hold; rejects non-unique
  timestamps after sorting.
- `POST /api/robots/{robot_id}/safety-inputs/gesture` (app/main.py):
  authenticated + CSRF, 1..60 frames, exactly 21 landmarks/frame; on
  recogniser acceptance it converges on the one idempotent latched STOP
  service. It cannot reset/resume/start motion (QIP-R9.2).
- Voice comparator: `POST .../safety-inputs/voice`, final transcript,
  confidence >=0.85, standalone STOP/STOPP. Separate endpoint — the app
  has NO voice+gesture fusion; cross-modal scoring below is a protocol
  (harness OR, STOP-only), not a claim about app fusion.
- Freshness bounds (integrations/interventions.py): event age >300 s is
  stale, timestamp >30 s in the future is rejected; event_id is the
  idempotency/replay key.

## 2. Folder layout (this node; future data follows it, not yet collected)
    research/gesture-dataset/
      README.md  schema.json  validate.py
      examples/synthetic-example.jsonl   # 12 deterministic synthetic records
      examples/generate_example.py       # regenerates it byte-identically
      tests/test_gesture_dataset_validator.py
    # Future approved capture (NOT created here, never commit raw media):
    #   data/<dataset-version>/metadata/{train,val,test}.jsonl
    #   data/<dataset-version>/derived-landmarks/  (21-pt landmarks only)
    #   Raw video/images stay off-repo, access-controlled, per §7.

## 3. Capture protocol (for a future approved capture)
- Device framing only (no settings are qualified here): record camera
  model/firmware, resolution, fps, distance, mount height in session log;
  capture at native fps, do not up-sample; keep clip = one attempt,
  <=60 frames submitted to the endpoint, timestamps monotonic ms from
  clip start plus a wall-clock `recorded_at` kept in session log.
- Script per clip: neutral start (hand down, 0.5 s) -> intended gesture
  or control action for 1.5 s -> neutral end. No coaching mid-clip.
- One `session_id` = one person, one environment, one continuous sitting.
  Any change of person/room/camera position starts a new session.
- Positive class `open_palm_stop`: upright open palm facing camera,
  four fingers extended and separated thumb (the geometry the existing
  recogniser checks), held as scripted. Intent is the script, not the
  recogniser output (avoids labelling by the system under test).
- Negative controls (all `intent_stop=false`): `fist`, `pointing`,
  `thumb_tucked`, `sideways_palm` (rotated 90°), `brief_wave`,
  `partial_open_palm` (one/two fingers folded), `other_hand_gesture`,
  `person_no_hand` (person present, hands down/out of frame),
  `empty_scene` (no person), ordinary activity (typing, holding cup/phone,
  waving goodbye, reaching toward camera).
- Near-boundary cases (label by script intent; expectation derived by
  validator, §5): hold 600/699/700/701/1000 ms; 1/2/3/4 consecutive
  qualifying frames; interrupted run (qualifying, 1 non-qualifying,
  qualifying); visibility/geometry near 0.79/0.80/0.81 (via annotated
  landmark visibility); thumb just inside/outside separation; fingers
  just bent; palm rotated 15/30/45°.
- Variation axes (record all in `conditions`, vary one axis per clip
  where feasible): distance 0.5/1/2/3/5 m; lighting bright/normal/dim/
  backlit with lux reading; occlusion 0/10/25/50% (self, sleeve, object,
  second hand); motion blur none/mild/severe (static, slow wave, fast
  pass); background: plain, cluttered, moving people behind, screen
  showing hands, outdoor-like; handedness L/R, sleeves/gloves/skin-tone
  diversity across consented participants (record only as aggregate
  coverage counts, never as person attributes in metadata).
- Consecutive frames & hold timing: annotate
  `consecutive_qualifying_frames` = longest run of frames meeting the
  per-frame geometry+visibility rule, and `hold_ms` = last-first
  timestamp of that run. Boundary grid above must appear in every split
  only via its own sessions (no re-slicing one session across splits).
- Temporal anomalies (synthetic/replayed derivatives, clearly tagged,
  never presented as live capture, QIP-R9.3): `stale` (event age
  299/300/301 s, >3600 s), `replay` (same event_id/clip delivered twice;
  second must not re-trigger), `duplicate_timestamp`, `duplicate_frame`
  (exact frame repeated), `out_of_order` (shuffled timestamps). These
  are constructed from already-consented/synthetic clips, tagged in
  `frames.temporal_tag`, and excluded from headline accuracy (§8).
- Contradictory voice+gesture (protocol clips): voice STOP + no gesture;
  voice negated/non-final/low-confidence STOP + open palm; voice
  "continue"/conversation + open palm; both negative. Scoring policy:
  either qualifying STOP-only signal may request STOP (logical OR of the
  two separate endpoints); neither may reset/resume; a negated or
  non-final voice signal is not a veto over a qualifying gesture, and a
  non-qualifying gesture is not a veto over a qualifying voice STOP.
  Record expectation per endpoint separately plus the OR result.

## 4. Metadata schema (JSONL, one record per clip)
Normative enforcement: `validate.py`; descriptive form: `schema.json`.
Fields (all required): clip_id (unique), schema_version
`gesture-dataset-v0.1`, split, source (synthetic|human_capture),
synthetic bool, session_id, person_id (pseudonymous `synth-*` or
study code, never name/email), environment_id, category
(canonical_positive|negative_control|near_boundary|variation|
temporal_anomaly|crossmodal_contradiction), label (§3), intent_stop,
expected_endpoint_trigger (derived, §5), modality
(gesture_only|gesture_plus_voice), voice (null or
{transcript_intent, final, confidence}), frames {frame_count,
frame_timestamps_ms[], min_visibility, consecutive_qualifying_frames,
hold_ms, temporal_tag}, conditions {distance_m, lighting_lux,
lighting_category, occlusion_pct, motion_blur, background_id},
consent {status, consent_id, retention_until, raw_media_stored},
annotation {annotator_id, label_rule_version, double_labelled},
frames_hash (hash of derived frame sequence; detects duplicate clips).

## 5. Labelling rules
1. Label = scripted intent, assigned at capture time, before any
   recogniser run. Never relabel from recogniser/endpoint output.
2. `intent_stop` is true iff label == `open_palm_stop`.
3. `expected_endpoint_trigger` is DERIVED, not annotated freely:
   gesture qualifies iff label==open_palm_stop AND
   consecutive_qualifying_frames>=3 AND hold_ms>=700 AND
   min_visibility>=0.8 AND temporal_tag==none; voice qualifies iff
   transcript_intent==stop AND final AND confidence>=0.85;
   expected = gesture OR voice. Validator recomputes and rejects
   mismatches — so boundary clips (699 ms, 2 frames, 0.79) are
   intent-positive but expectation-negative (deliberate abstention).
4. Ambiguous/unscripted clips are excluded, not force-labelled;
   exclusion count is reported with denominator (§8).
5. Double-label >=20% of human clips by a second annotator blind to the
   first label and to recogniser output; disagreements resolved by a
   third reviewer; agreement rate reported, unresolved clips excluded.
6. Temporal-anomaly and cross-modal records keep the original label;
   only temporal_tag / voice fields change. Synthetic records must have
   source=synthetic and are never mixed into human-capture denominators.

## 6. Split rules (leakage control)
- Split unit is the SESSION, grouped further by person and environment:
  no session_id, person_id, environment_id, or frames_hash may appear
  in more than one of train/val/test. Validator fails the whole file
  otherwise (this is the leaky-dataset gate).
- Assign whole sessions to splits before clip extraction; never split
  frames/clips from one session across splits; near-duplicate derivatives
  (crops, replays, anomaly variants) inherit the source clip's split.
- Target ratio by session count approx. 60/20/20; test sessions are
  sealed until gates are pre-registered; any re-split creates a new
  dataset version and invalidates prior test results.
- Stratify by category/condition coverage per split, but stratification
  never overrides the grouping rule above.

## 7. Consent & privacy (human images)
- No capture under this protocol without explicit, recorded consent per
  person: purpose, that frames/derived landmarks are used only to
  evaluate a STOP gesture, retention deadline, withdrawal route, and
  that refusal has no consequence. `consent.status` must be `consented`
  with consent_id + retention_until for every human_capture record;
  pending/withdrawn records are validator failures and must be deleted,
  not merely excluded.
- Data minimisation: store derived 21-point landmarks + metadata in the
  dataset; raw video/images stay off-repo in access-controlled storage,
  referenced only by hash. No names, contact details, faces-as-images,
  or free-text identifiers in metadata (validator rejects PII keys and
  email-like person_ids). Pseudonymous study codes; the code-to-identity
  key, if any, is held separately by the human data controller, never in
  this repo.
- Withdrawal: delete raw media + derived landmarks for that person_id,
  remove/replace affected records, bump dataset version, and note the
  removal (counts only) in the dataset changelog. Published aggregates
  already computed are listed as superseded.
- Children/vulnerable people, public-space bystanders, and covert
  capture are out of scope and prohibited. Background people make a
  clip `person_no_hand`-invalid for human data unless separately
  consented — exclude such clips; synthetic backgrounds are preferred.
- This section is an engineering protocol, not legal advice (GDPR etc.
  review by a human controller is a gate before any real capture).

## 8. Evaluation metrics (every rate carries its denominator)
Report per split, per category and per variation axis, with raw counts
(TP/FP/TN/FN/abstentions), never a bare percentage, never pooled
synthetic+human. A system output is TRIGGER (endpoint would request
STOP), NO-TRIGGER, or ABSTAIN (recogniser returns no decision /
insufficient quality — for the current deterministic recogniser,
below-threshold, non-consecutive, stale/replay and duplicate-timestamp
outcomes are counted as abstentions, listed by reason):
- False-trigger rate = FP / (FP + TN) over expectation-negative clips,
  and separately FP / all negative-control clips.
- Missed-trigger rate = FN / (FN + TP) over expectation-positive clips;
  deliberate boundary abstentions (intent-positive, expectation-
  negative, e.g. 699 ms) are reported separately and not counted here.
- Abstention rate = abstentions / all evaluated clips, by reason.
- Coverage-adjusted success = TP / all intent-positive clips (this, not
  the missed rate, shows the cost of abstaining on real STOP intent).
- Temporal: stale/replay/duplicate/out-of-order suppression =
  correctly non-triggering anomaly clips / all anomaly clips, per tag.
- Cross-modal: OR-policy false/missed as above per contradiction cell.
- Excluded/ambiguous rate = excluded / captured, with reasons.
Latency (capture->endpoint response) may be reported descriptively
only; it is not a gate here and proves no physical stopping time.

## 9. Acceptance gates tied to existing endpoints (pre-register before test)
A future evaluation may claim only "passes this protocol on this
dataset version", never sensor qualification or safety validation:
G1 Validator: validate.py passes on all split files; zero leakage,
   zero consent/PII failures. (Fail = dataset rejected, no scoring.)
G2 Canonical positives: missed-trigger 0/N on canonical_positive test
   clips at the existing endpoint thresholds (§1). Any miss blocks.
G3 Negative controls: false-trigger 0/N on test negative_controls.
   Any false trigger blocks and is documented as a known limit (cf.
   F4 voice FP), not tuned away on the test split.
G4 Boundaries reproduced: 699 ms no-trigger / 700 ms trigger,
   2 frames no / 3 yes, visibility 0.79 no / 0.80 yes (matching
   integrations/recognizers.py and research/safety-inputs results),
   via POST /api/robots/{robot_id}/safety-inputs/gesture, STOP-only,
   latch set on trigger, no reset via gesture/voice.
G5 Temporal: stale (>300 s / future >30 s), replayed event_id,
   duplicate and out-of-order timestamps never produce a new STOP
   (endpoint/idempotency layer), 100% suppression on anomaly set.
G6 Cross-modal: OR table (§3) holds cell-by-cell; no signal clears the
   latch; PANIC_CANDIDATE-style labels remain audit-only.
G7 Claims: report names dataset version, splits, denominators, raw
   outputs; thresholds changed after seeing test = new dataset version
   + new test sessions (no test-set tuning).
Failure of any gate returns the DATASET (not the endpoints, which this
node may not modify) for fix, max three attempts per GRAPH-HARNESS,
then blocker.

## 10. Run
    python3 research/gesture-dataset/examples/generate_example.py
    python3 research/gesture-dataset/validate.py research/gesture-dataset/examples/synthetic-example.jsonl
    python3 -m pytest research/gesture-dataset/tests -q
Example output: OK: 12 records; splits={'train': 4, 'val': 4, 'test': 4}
The synthetic example illustrates schema/leakage rules only; its
records are not measurements and support no performance claim.
