"""Validator for gesture-dataset metadata (JSONL). Stdlib only, offline.

Fails (exit 1 / ValueError listing all errors) on malformed records and on
leakage: any session_id, person_id or environment_id appearing in more
than one split, duplicate clip_id, or duplicate frames_hash across splits.
No camera/Pi access, no training, no qualification claim (QIP-R9.3/R11.2).
"""
import json, sys
from pathlib import Path

SCHEMA = "gesture-dataset-v0.1"
SPLITS = {"train", "val", "test"}
SOURCES = {"synthetic", "human_capture"}
CATEGORIES = {"canonical_positive", "negative_control", "near_boundary",
              "variation", "temporal_anomaly", "crossmodal_contradiction"}
LABELS = {"open_palm_stop", "no_gesture", "fist", "pointing", "thumb_tucked",
          "sideways_palm", "brief_wave", "partial_open_palm",
          "other_hand_gesture", "person_no_hand", "empty_scene"}
TEMPORAL = {"none", "stale", "replay", "duplicate_timestamp", "out_of_order", "duplicate_frame"}
BLUR = {"none", "mild", "severe"}
LIGHTING = {"bright", "normal", "dim", "backlit"}
CONSENT = {"consented", "not_applicable_synthetic", "pending", "withdrawn"}
PROHIBITED = {"name", "full_name", "email", "phone", "address", "face_image", "raw_video_url"}
REQUIRED = {"clip_id", "schema_version", "split", "source", "synthetic", "session_id",
            "person_id", "environment_id", "category", "label", "intent_stop",
            "expected_endpoint_trigger", "modality", "voice", "frames", "conditions",
            "consent", "annotation", "frames_hash"}

def _err(errors, cid, msg): errors.append(f"{cid or '<no clip_id>'}: {msg}")

def validate_records(records):
    errors, seen_clip, hash_split = [], {}, {}
    group_split = {"session_id": {}, "person_id": {}, "environment_id": {}}
    for i, r in enumerate(records):
        if not isinstance(r, dict): errors.append(f"line {i+1}: not an object"); continue
        cid = r.get("clip_id")
        missing = REQUIRED - set(r)
        if missing: _err(errors, cid, f"missing fields {sorted(missing)}"); continue
        if PROHIBITED & set(r): _err(errors, cid, f"prohibited PII fields {sorted(PROHIBITED & set(r))}")
        if r["schema_version"] != SCHEMA: _err(errors, cid, "bad schema_version")
        if cid in seen_clip: _err(errors, cid, "duplicate clip_id")
        seen_clip[cid] = r["split"]
        if r["split"] not in SPLITS: _err(errors, cid, "bad split")
        if r["source"] not in SOURCES: _err(errors, cid, "bad source")
        if bool(r["synthetic"]) != (r["source"] == "synthetic"): _err(errors, cid, "synthetic flag != (source==synthetic)")
        if r["category"] not in CATEGORIES: _err(errors, cid, "bad category")
        if r["label"] not in LABELS: _err(errors, cid, "bad label")
        if r["modality"] not in {"gesture_only", "gesture_plus_voice"}: _err(errors, cid, "bad modality")
        # split-group leakage registry
        for k in group_split:
            prev = group_split[k].setdefault(r[k], r["split"])
            if prev != r["split"]: _err(errors, cid, f"leakage: {k}={r[k]} in {prev} and {r['split']}")
        fh = r["frames_hash"]
        if fh in hash_split and hash_split[fh] != r["split"]: _err(errors, cid, "leakage: frames_hash across splits")
        hash_split.setdefault(fh, r["split"])
        # intent / label rule
        if r["intent_stop"] != (r["label"] == "open_palm_stop"): _err(errors, cid, "intent_stop must be true iff label==open_palm_stop")
        f, c, cons = r["frames"], r["conditions"], r["consent"]
        if not isinstance(f, dict) or not {"frame_count", "frame_timestamps_ms", "min_visibility", "consecutive_qualifying_frames", "hold_ms", "temporal_tag"} <= set(f):
            _err(errors, cid, "frames missing subfields"); continue
        ts = f["frame_timestamps_ms"]
        if not isinstance(ts, list) or not ts or f["frame_count"] != len(ts): _err(errors, cid, "frame_count != len(frame_timestamps_ms)")
        if f["temporal_tag"] not in TEMPORAL: _err(errors, cid, "bad temporal_tag")
        if f["temporal_tag"] == "none" and any(b <= a for a, b in zip(ts, ts[1:])):
            _err(errors, cid, "timestamps not strictly increasing but temporal_tag==none")
        if f["temporal_tag"] == "duplicate_timestamp" and len(ts) == len(set(ts)): _err(errors, cid, "tagged duplicate_timestamp but timestamps unique")
        if f["temporal_tag"] == "out_of_order" and ts == sorted(ts): _err(errors, cid, "tagged out_of_order but timestamps sorted")
        if r["category"] == "temporal_anomaly" and f["temporal_tag"] == "none": _err(errors, cid, "temporal_anomaly category requires temporal_tag != none")
        if not (0 <= f["min_visibility"] <= 1): _err(errors, cid, "min_visibility out of [0,1]")
        if f["hold_ms"] < 0 or f["consecutive_qualifying_frames"] < 0: _err(errors, cid, "negative hold/frames")
        if not isinstance(c, dict) or not {"distance_m", "lighting_lux", "lighting_category", "occlusion_pct", "motion_blur", "background_id"} <= set(c):
            _err(errors, cid, "conditions missing subfields"); continue
        if not (0.2 <= c["distance_m"] <= 10): _err(errors, cid, "distance_m out of [0.2,10]")
        if not (0 <= c["occlusion_pct"] <= 100): _err(errors, cid, "occlusion_pct out of [0,100]")
        if c["motion_blur"] not in BLUR or c["lighting_category"] not in LIGHTING: _err(errors, cid, "bad blur/lighting")
        # Endpoint-derived expectation: OpenPalmStopRecognizer >=3 consec, >=700ms, vis>=0.8
        # (integrations/recognizers.py; docs/INTERVENTION-INPUTS.md), STOP-only endpoint.
        gesture_qualifies = (r["label"] == "open_palm_stop" and f["consecutive_qualifying_frames"] >= 3
                             and f["hold_ms"] >= 700 and f["min_visibility"] >= 0.8 and f["temporal_tag"] == "none")
        voice_qualifies = False
        if r["modality"] == "gesture_plus_voice":
            v = r["voice"]
            if not isinstance(v, dict) or not {"transcript_intent", "final", "confidence"} <= set(v):
                _err(errors, cid, "voice missing subfields")
            else:
                if not (0 <= v["confidence"] <= 1): _err(errors, cid, "voice confidence out of [0,1]")
                voice_qualifies = v["transcript_intent"] == "stop" and v["final"] is True and v["confidence"] >= 0.85
            if r["category"] != "crossmodal_contradiction": _err(errors, cid, "gesture_plus_voice requires crossmodal_contradiction category")
        elif r["voice"] is not None: _err(errors, cid, "gesture_only requires voice==null")
        expected = gesture_qualifies or voice_qualifies  # harness/app endpoints are separate; OR for contradiction protocol, STOP-only
        if r["expected_endpoint_trigger"] != expected:
            _err(errors, cid, f"expected_endpoint_trigger={r['expected_endpoint_trigger']} inconsistent with derived {expected} (gesture>=3f/>=700ms/vis>=0.8, voice final/conf>=0.85/stop, temporal_tag==none)")
        # consent / privacy
        if not isinstance(cons, dict) or not {"status", "consent_id", "retention_until", "raw_media_stored"} <= set(cons):
            _err(errors, cid, "consent missing subfields"); continue
        if cons["status"] not in CONSENT: _err(errors, cid, "bad consent status")
        if cons["status"] in {"pending", "withdrawn"}: _err(errors, cid, "pending/withdrawn consent must not be in dataset")
        if r["source"] == "human_capture" and (cons["status"] != "consented" or not cons["consent_id"] or not cons["retention_until"]):
            _err(errors, cid, "human_capture requires consented + consent_id + retention_until")
        if r["source"] == "synthetic" and (cons["status"] != "not_applicable_synthetic" or not str(r["person_id"]).startswith("synth-")):
            _err(errors, cid, "synthetic requires not_applicable_synthetic + synth- person_id")
        if "@" in str(r["person_id"]): _err(errors, cid, "person_id looks like PII")
        a = r["annotation"]
        if not isinstance(a, dict) or not {"annotator_id", "label_rule_version", "double_labelled"} <= set(a):
            _err(errors, cid, "annotation missing subfields")
    return errors

def load_jsonl(path):
    records = []
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip(): continue
        try: records.append(json.loads(line))
        except json.JSONDecodeError as e: raise ValueError(f"line {n}: invalid JSON: {e}") from e
    return records

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1: print("usage: validate.py <metadata.jsonl>"); return 2
    try: records = load_jsonl(argv[0])
    except ValueError as e: print(f"FAIL: {e}"); return 1
    errors = validate_records(records)
    if errors:
        print(f"FAIL: {len(errors)} error(s)"); [print(" -", e) for e in errors]; return 1
    from collections import Counter
    print(f"OK: {len(records)} records; splits={dict(Counter(r['split'] for r in records))} labels={dict(Counter(r['label'] for r in records))}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
