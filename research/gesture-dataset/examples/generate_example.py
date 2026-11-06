"""Deterministic synthetic example generator (no RNG, no human data)."""
import hashlib, json
from pathlib import Path
OUT = Path(__file__).with_name("synthetic-example.jsonl")

def rec(clip, split, sess, person, env, cat, label, consec, hold, vis, ts, temporal="none",
        dist=1.0, lux=300, light="normal", occ=0, blur="none", bg=None, modality="gesture_only", voice=None):
    gesture_q = label=="open_palm_stop" and consec>=3 and hold>=700 and vis>=0.8 and temporal=="none"
    voice_q = bool(voice and voice["transcript_intent"]=="stop" and voice["final"] and voice["confidence"]>=0.85)
    fh = hashlib.sha256(f"{clip}|{ts}|{label}".encode()).hexdigest()[:16]
    return {"clip_id": clip, "schema_version": "gesture-dataset-v0.1", "split": split,
      "source": "synthetic", "synthetic": True, "session_id": sess, "person_id": person,
      "environment_id": env, "category": cat, "label": label, "intent_stop": label=="open_palm_stop",
      "expected_endpoint_trigger": gesture_q or voice_q, "modality": modality, "voice": voice,
      "frames": {"frame_count": len(ts), "frame_timestamps_ms": ts, "min_visibility": vis,
                 "consecutive_qualifying_frames": consec, "hold_ms": hold, "temporal_tag": temporal},
      "conditions": {"distance_m": dist, "lighting_lux": lux, "lighting_category": light,
                     "occlusion_pct": occ, "motion_blur": blur, "background_id": bg or f"bg-{env}"},
      "consent": {"status": "not_applicable_synthetic", "consent_id": None, "retention_until": None, "raw_media_stored": False},
      "annotation": {"annotator_id": "synth-annotator-1", "label_rule_version": "gesture-labels-v0.1", "double_labelled": False},
      "frames_hash": fh}

R = [
 rec("SYN-POS-001","train","sess-train-1","synth-person-01","env-train-a","canonical_positive","open_palm_stop",3,700,1.0,[0,350,700]),
 rec("SYN-NEG-001","train","sess-train-1","synth-person-01","env-train-a","negative_control","fist",0,700,1.0,[0,350,700]),
 rec("SYN-BND-001","train","sess-train-1","synth-person-01","env-train-a","near_boundary","open_palm_stop",3,699,1.0,[0,350,699]),
 rec("SYN-VAR-001","train","sess-train-1","synth-person-01","env-train-a","variation","open_palm_stop",4,900,0.85,[0,300,600,900],dist=2.5,lux=50,light="dim",occ=20,blur="mild"),
 rec("SYN-POS-002","val","sess-val-1","synth-person-02","env-val-a","canonical_positive","open_palm_stop",3,701,0.8,[0,350,701],dist=0.5,lux=800,light="bright"),
 rec("SYN-NEG-002","val","sess-val-1","synth-person-02","env-val-a","negative_control","brief_wave",1,200,1.0,[0,200]),
 rec("SYN-TMP-001","val","sess-val-1","synth-person-02","env-val-a","temporal_anomaly","open_palm_stop",3,700,1.0,[700,350,700],temporal="duplicate_timestamp"),
 rec("SYN-XMO-001","val","sess-val-1","synth-person-02","env-val-a","crossmodal_contradiction","open_palm_stop",3,700,1.0,[0,350,700],modality="gesture_plus_voice",voice={"transcript_intent":"negated_stop","final":True,"confidence":0.99}),
 rec("SYN-POS-003","test","sess-test-1","synth-person-03","env-test-a","canonical_positive","open_palm_stop",5,1200,0.9,[0,300,600,900,1200],dist=3.0,occ=10,blur="mild",bg="bg-env-test-a"),
 rec("SYN-NEG-003","test","sess-test-1","synth-person-03","env-test-a","negative_control","empty_scene",0,0,0.0,[0]),
 rec("SYN-TMP-002","test","sess-test-1","synth-person-03","env-test-a","temporal_anomaly","open_palm_stop",3,700,1.0,[700,350,0],temporal="out_of_order"),
 rec("SYN-XMO-002","test","sess-test-1","synth-person-03","env-test-a","crossmodal_contradiction","fist",0,700,1.0,[0,350,700],modality="gesture_plus_voice",voice={"transcript_intent":"stop","final":True,"confidence":0.9}),
]
if __name__ == "__main__":
    OUT.write_text("".join(json.dumps(r, sort_keys=True)+"\n" for r in R)); print(f"wrote {len(R)} -> {OUT}")
