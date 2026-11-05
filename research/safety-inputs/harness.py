"""Synthetic safety-input qualification harness (offline, deterministic).

Runs the EXISTING deterministic recognizers (integrations/recognizers.py,
unmodified) plus the existing InterventionEvent freshness bounds
(integrations/interventions.py: stale >300 s, future skew <-30 s) over the
enumerated synthetic datasets in datasets/. Adds one explicitly harness-only
layer: an event_id replay guard (first delivery may trigger; a replay_of
delivery with the same event key may not trigger again). That guard mirrors
the app's downstream idempotency concept for measurement only -- it is NOT
claimed to be inside either recognizer, and recognizer-only replay behaviour
is reported separately in the summary (`recognizer_only_replay`).

Crossmodal policy is harness-only OR: any valid STOP-only signal triggers.
No fusion exists in the app (separate endpoints); this does not claim one.

SYNTHETIC ONLY: no sensor, microphone, camera, person, or model is qualified.
Rates are reported with denominators everywhere. No app/control code is used
except read-only imports of the recognizers / freshness constants.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1]))  # repo root, read-only imports

from integrations.interventions import MAX_EVENT_AGE_SECONDS, MAX_FUTURE_SKEW_SECONDS  # noqa: E402
from integrations.recognizers import (  # noqa: E402
    GestureFrame, HandLandmark, OpenPalmStopRecognizer, VoiceObservation, VoiceStopRecognizer,
)

VOICE = VoiceStopRecognizer()          # defaults: conf >= 0.85 (docs/INTERVENTION-INPUTS.md)
GESTURE = OpenPalmStopRecognizer()     # defaults: >=3 frames, >=700 ms, vis >= 0.8


def load(name):
    return [json.loads(l) for l in (HERE / "datasets" / f"{name}.jsonl").read_text().splitlines() if l.strip()]


def is_stale(case):
    age = case.get("age_seconds")
    return age is not None and (age > MAX_EVENT_AGE_SECONDS or age < -MAX_FUTURE_SKEW_SECONDS)


def run_voice(case, seen):
    rec = VOICE.recognize(VoiceObservation(case["transcript"], case["confidence"], case["final"]))
    key = case.get("replay_of")
    replay_blocked = bool(key and key in seen)
    if case["id"]:
        seen.add(case["id"])
    pipeline = rec.stop_requested and not is_stale(case) and not replay_blocked
    return {"recognizer": rec.stop_requested, "pipeline": pipeline,
            "reason": rec.reason + ("; stale (harness freshness layer)" if is_stale(case) else "")
            + ("; replay blocked (harness event_id guard)" if replay_blocked else "")}


def to_frames(frames):
    return [GestureFrame(f["timestamp_ms"],
                         [HandLandmark(p["x"], p["y"], p["visibility"]) for p in f["landmarks"]])
            for f in frames]


def run_gesture(case, seen):
    rec = GESTURE.recognize(to_frames(case["frames"]))
    key = case.get("event_id") if case.get("replay_of") else None
    replay_blocked = bool(key and key in seen)
    if case.get("event_id"):
        seen.add(case["event_id"])
    elif case["id"]:
        seen.add(case["id"])
    pipeline = rec.stop_requested and not replay_blocked
    return {"recognizer": rec.stop_requested, "pipeline": pipeline,
            "reason": rec.reason + ("; replay blocked (harness event_id guard)" if replay_blocked else ""),
            "qualifying_frames": rec.qualifying_frames, "held_ms": rec.held_ms}


def run_crossmodal(case):
    v = VOICE.recognize(VoiceObservation(case["voice"]["transcript"],
                                         case["voice"]["confidence"], case["voice"]["final"]))
    g = GESTURE.recognize(to_frames(case["gesture_frames"]))
    out = v.stop_requested or g.stop_requested  # harness-only OR, see module docstring
    return {"recognizer": out, "pipeline": out,
            "reason": f"voice={v.reason}; gesture={g.reason}; harness_policy=OR"}


RUNNERS = {"voice": run_voice, "gesture": run_gesture}


def classify(intent, triggered):
    return "TP" if intent and triggered else "FN" if intent else "FP" if triggered else "TN"


def rates(rows):
    tp = sum(r["class"] == "TP" for r in rows); fn = sum(r["class"] == "FN" for r in rows)
    fp = sum(r["class"] == "FP" for r in rows); tn = sum(r["class"] == "TN" for r in rows)
    def rate(num, den):
        return {"numerator": num, "denominator": den,
                "rate": round(num / den, 6) if den else None}
    return {"n": len(rows), "TP": tp, "FN": fn, "FP": fp, "TN": tn,
            "false_trigger_rate_FP_over_FP_plus_TN": rate(fp, fp + tn),
            "missed_trigger_rate_FN_over_FN_plus_TP": rate(fn, fn + tp)}


def main():
    results, seen_voice, seen_gesture = [], set(), set()
    replay_probe = []
    for modality in ("voice", "gesture", "crossmodal"):
        for case in load(modality):
            if modality == "crossmodal":
                d = run_crossmodal(case)
            else:
                d = RUNNERS[modality](case, seen_voice if modality == "voice" else seen_gesture)
            row = {"id": case["id"], "modality": modality, "category": case["category"],
                   "intent_stop": case["intent_stop"], "synthetic": True,
                   "recognizer_triggered": d["recognizer"], "pipeline_triggered": d["pipeline"],
                   "class": classify(case["intent_stop"], d["pipeline"]), "reason": d["reason"]}
            if "qualifying_frames" in d:
                row.update({"qualifying_frames": d["qualifying_frames"], "held_ms": d["held_ms"]})
            results.append(row)
            if case["category"] == "stale_replay":
                replay_probe.append({"id": case["id"], "recognizer_triggered": d["recognizer"],
                                     "pipeline_triggered": d["pipeline"]})
    by = {}
    for key_fn, name in ((lambda r: r["modality"], "by_modality"),
                         (lambda r: f"{r['modality']}:{r['category']}", "by_category")):
        groups = defaultdict(list)
        for r in results:
            groups[key_fn(r)].append(r)
        by[name] = {k: rates(v) for k, v in sorted(groups.items())}
    summary = {
        "synthetic_only": True,
        "qualification_claim": "NONE - synthetic deterministic boundary harness only; "
                               "no sensor, microphone, camera, speaker, person, or learned-model qualification",
        "system_under_test": "integrations.recognizers VoiceStopRecognizer(conf>=0.85,final,standalone STOP/STOPP) "
                             "+ OpenPalmStopRecognizer(vis>=0.8,>=3 consecutive,>=700ms), unmodified; "
                             "harness layers: InterventionEvent freshness (stale>300s, future<-30s) + event_id replay guard (harness-only)",
        "thresholds": {"voice_min_confidence": VOICE.minimum_confidence,
                       "gesture_min_hold_ms": GESTURE.minimum_hold_ms,
                       "gesture_min_frames": GESTURE.minimum_frames,
                       "gesture_min_visibility": GESTURE.minimum_visibility,
                       "max_event_age_seconds": MAX_EVENT_AGE_SECONDS,
                       "max_future_skew_seconds": MAX_FUTURE_SKEW_SECONDS},
        "crossmodal_policy": "harness-only OR (no app fusion exists; separate endpoints in app)",
        "total": rates(results), "by_modality": by["by_modality"], "by_category": by["by_category"],
        "recognizer_only_replay_and_stale_probe": replay_probe,
        "nontriggering_intended_stop_ids": [r["id"] for r in results if r["class"] == "FN"],
        "false_trigger_ids": [r["id"] for r in results if r["class"] == "FP"],
    }
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "results.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in results))
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary["total"], indent=2))
    for k, v in summary["by_category"].items():
        print(k, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
