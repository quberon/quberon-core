"""Deterministic synthetic dataset generation for safety-input qualification.

SYNTHETIC ONLY. No microphone, camera, sensor, speaker, person, or learned
model is involved. Cases are enumerated boundary grids (no RNG), so a
re-run produces byte-identical JSONL. Ground truth is the *labelled intent*
of the synthetic case (stop / no-stop), independent of recognizer thresholds:
a below-threshold intended STOP therefore counts as a missed trigger
(abstention), which is exactly the trade-off this harness reports.

Expectations follow the declared scope in docs/INTERVENTION-INPUTS.md and
QIP-R9: voice = final transcript, confidence >= 0.85, standalone STOP/STOPP,
non-negated; gesture = 21 landmarks, visibility >= 0.8, >= 3 consecutive
qualifying frames, >= 700 ms hold. This module never edits app/control code;
it only imports the existing recognizers indirectly via harness.py.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
CHAINS = ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))


def landmarks(kind="open_palm", visibility=1.0):
    """Return 21 synthetic landmarks [{"x","y","visibility"}] for `kind`."""
    pts = [{"x": 0.5, "y": 0.85, "visibility": visibility} for _ in range(21)]
    pts[0] = {"x": 0.5, "y": 0.9, "visibility": visibility}
    if kind == "open_palm":
        for chain, x in zip(CHAINS, (0.38, 0.47, 0.56, 0.65)):
            for idx, y in zip(chain, (0.62, 0.49, 0.36, 0.22)):
                pts[idx] = {"x": x, "y": y, "visibility": visibility}
        pts[4] = {"x": 0.25, "y": 0.48, "visibility": visibility}
    elif kind == "fist":
        for chain, x in zip(CHAINS, (0.38, 0.47, 0.56, 0.65)):
            for idx, y in zip(chain, (0.62, 0.66, 0.70, 0.74)):  # tips curl down
                pts[idx] = {"x": x, "y": y, "visibility": visibility}
        pts[4] = {"x": 0.42, "y": 0.60, "visibility": visibility}
    elif kind == "pointing":
        for i, (chain, x) in enumerate(zip(CHAINS, (0.38, 0.47, 0.56, 0.65))):
            ys = (0.62, 0.49, 0.36, 0.22) if i == 0 else (0.62, 0.66, 0.70, 0.74)
            for idx, y in zip(chain, ys):
                pts[idx] = {"x": x, "y": y, "visibility": visibility}
        pts[4] = {"x": 0.42, "y": 0.60, "visibility": visibility}
    elif kind == "thumb_tucked":
        for chain, x in zip(CHAINS, (0.38, 0.47, 0.56, 0.65)):
            for idx, y in zip(chain, (0.62, 0.49, 0.36, 0.22)):
                pts[idx] = {"x": x, "y": y, "visibility": visibility}
        pts[4] = {"x": 0.36, "y": 0.48, "visibility": visibility}  # span too small
    elif kind == "palm_sideways":
        # Fingers extended horizontally: y-ordering (upright) check must fail.
        for chain, y in zip(CHAINS, (0.38, 0.47, 0.56, 0.65)):
            for idx, x in zip(chain, (0.62, 0.49, 0.36, 0.22)):
                pts[idx] = {"x": x, "y": y, "visibility": visibility}
        pts[4] = {"x": 0.48, "y": 0.25, "visibility": visibility}
    else:
        raise ValueError(kind)
    return pts


def frame(ts, kind="open_palm", visibility=1.0, count=21, x_shift=0.0):
    pts = landmarks(kind, visibility)[:count] if count <= 21 else (
        landmarks(kind, visibility) + [landmarks(kind, visibility)[0]] * (count - 21))
    if x_shift:
        pts = [{**p, "x": p["x"] + x_shift} for p in pts]
    return {"timestamp_ms": ts, "landmarks": pts}


def voice_cases():
    c = []
    def add(cid, cat, intent, transcript, conf, final=True, age=None, replay_of=None):
        case = {"id": cid, "modality": "voice", "category": cat,
                "intent_stop": intent, "synthetic": True,
                "transcript": transcript, "confidence": conf, "final": final}
        if age is not None:
            case["age_seconds"] = age
        if replay_of:
            case["replay_of"] = replay_of
        c.append(case)
    # Canonical intended STOP (must trigger) and confidence boundary sweep.
    for i, t in enumerate(["STOP", "stop", "Stopp", "STOP!", "stopp.", "please stop"]):
        add(f"V-POS-{i:02d}", "canonical_positive", True, t, 0.99)
    for i, conf in enumerate([0.0, 0.5, 0.80, 0.84, 0.849, 0.85, 0.851, 0.90, 1.0]):
        add(f"V-CONF-{i:02d}", "degraded_confidence", True, "STOP", conf)
    for i, conf in enumerate([-0.1, 1.01, 1.5]):
        add(f"V-INVALIDCONF-{i:02d}", "degraded_confidence", True, "STOP", conf)
    for i in range(3):
        add(f"V-INTERIM-{i:02d}", "missed_trigger_boundary", True, "STOP", 0.99, final=False)
    # False-trigger negatives: negation, embedded token, conversation, other words.
    negs = ["do not stop", "don't stop", "never stop", "inte stopp", "ej stopp",
            "no stop", "nonstop", "stopwatch", "the bus stop is near", "stopping by",
            "continue", "resume", "go ahead", ""]
    # Note: "the bus stop is near" has a standalone token -> matcher triggers by
    # declared token policy; it is labelled intent=False so it counts as FP.
    for i, t in enumerate(negs):
        add(f"V-NEG-{i:02d}", "false_trigger", False, t, 0.99)
    for i, t in enumerate(["do not stop", "nonstop", "continue"]):
        add(f"V-NEGCONF-{i:02d}", "false_trigger", False, t, 0.99, final=False)
    # Stale / replay (harness pipeline layer: InterventionEvent freshness bounds).
    add("V-STALE-00", "stale_replay", True, "STOP", 0.99, age=301)
    add("V-STALE-01", "stale_replay", True, "STOP", 0.99, age=3600)
    add("V-STALE-02", "stale_replay", True, "STOP", 0.99, age=-31)
    add("V-FRESH-00", "stale_replay", True, "STOP", 0.99, age=299)
    add("V-REPLAY-00", "stale_replay", True, "STOP", 0.99, age=0)
    add("V-REPLAY-01", "stale_replay", True, "STOP", 0.99, age=0, replay_of="V-REPLAY-00")
    add("V-REPLAY-02", "stale_replay", True, "STOP", 0.99, age=0, replay_of="V-REPLAY-00")
    return c


def gesture_cases():
    c = []
    def add(cid, cat, intent, frames):
        c.append({"id": cid, "modality": "gesture", "category": cat,
                  "intent_stop": intent, "synthetic": True, "frames": frames})
    def seq(times, kind="open_palm", vis=1.0):
        return [frame(t, kind, vis) for t in times]
    add("G-POS-00", "canonical_positive", True, seq([0, 350, 700]))
    add("G-POS-01", "canonical_positive", True, seq([0, 250, 500, 750]))
    add("G-POS-02", "canonical_positive", True, seq([1000, 1400, 1800]))
    # Hold / consecutive-frame boundaries (intent = held palm).
    add("G-HOLD-00", "hold_frame_boundary", True, seq([0, 300, 600]))       # 600 ms
    add("G-HOLD-01", "hold_frame_boundary", True, seq([0, 350, 699]))       # 699 ms
    add("G-HOLD-02", "hold_frame_boundary", True, seq([0, 350, 701]))
    add("G-HOLD-03", "hold_frame_boundary", True, seq([0, 700]))            # only 2 frames
    add("G-HOLD-04", "hold_frame_boundary", True, seq([0]))                 # 1 frame
    add("G-HOLD-05", "hold_frame_boundary", True,
        seq([0, 350]) + seq([400], "fist") + seq([450, 800, 1150]))        # interrupted, then valid run
    add("G-HOLD-06", "hold_frame_boundary", True,
        seq([0, 350]) + seq([400], "fist") + seq([450, 600]))               # interrupted, short run
    # Degraded visibility / geometry.
    for i, vis in enumerate([0.0, 0.5, 0.79, 0.80, 0.81, 1.0]):
        add(f"G-VIS-{i:02d}", "degraded_confidence", True, seq([0, 350, 700], vis=vis))
    add("G-GEO-00", "degraded_confidence", True, [frame(t, "open_palm", 1.0, count=20) for t in (0, 350, 700)])
    add("G-GEO-01", "degraded_confidence", True, [frame(t, "open_palm", 1.0, count=22) for t in (0, 350, 700)])
    add("G-GEO-02", "degraded_confidence", True, [frame(t, "open_palm", 1.0, x_shift=0.6) for t in (0, 350, 700)])
    add("G-EMPTY-00", "degraded_confidence", True, [])
    # False-trigger negatives.
    add("G-NEG-00", "false_trigger", False, seq([0, 350, 700], "fist"))
    add("G-NEG-01", "false_trigger", False, seq([0, 350, 700], "pointing"))
    add("G-NEG-02", "false_trigger", False, seq([0, 350, 700], "thumb_tucked"))
    add("G-NEG-03", "false_trigger", False, seq([0, 350, 700], "palm_sideways"))
    add("G-NEG-04", "false_trigger", False, seq([0, 100, 200]))  # brief palm wave, intent=False
    # Stale/replay at frame layer: duplicate timestamps must reject.
    add("G-DUPTS-00", "stale_replay", True, seq([0, 350, 350, 700]))
    add("G-DUPTS-01", "stale_replay", True, seq([700, 700, 700]))
    add("G-REPLAY-00", "stale_replay", True, seq([0, 350, 700]))
    c[-1]["event_id"] = "G-REPLAY-EVT"
    add("G-REPLAY-01", "stale_replay", True, seq([0, 350, 700]))
    c[-1].update({"event_id": "G-REPLAY-EVT", "replay_of": "G-REPLAY-00"})
    # Out-of-order input: recognizer sorts; labelled as observation, intent stop.
    add("G-ORDER-00", "stale_replay", True, seq([700, 0, 350]))
    return c


def crossmodal_cases():
    """Harness-level OR policy only (no app fusion exists): any valid STOP-only
    signal triggers; a negated/absent signal does not veto a valid other one."""
    def palm(times=(0, 350, 700), kind="open_palm", vis=1.0):
        return [frame(t, kind, vis) for t in times]
    base = {"modality": "crossmodal", "category": "contradictory_signals", "synthetic": True}
    rows = [
        ("X-00", True,  {"transcript": "STOP", "confidence": 0.99, "final": True}, palm()),
        ("X-01", True,  {"transcript": "STOP", "confidence": 0.99, "final": True}, palm(kind="fist")),
        ("X-02", True,  {"transcript": "do not stop", "confidence": 0.99, "final": True}, palm()),
        ("X-03", False, {"transcript": "do not stop", "confidence": 0.99, "final": True}, palm(kind="fist")),
        ("X-04", True,  {"transcript": "STOP", "confidence": 0.50, "final": True}, palm()),
        ("X-05", False, {"transcript": "STOP", "confidence": 0.50, "final": True}, palm((0, 100, 200))),
        ("X-06", True,  {"transcript": "STOP", "confidence": 0.99, "final": False}, palm()),
        ("X-07", False, {"transcript": "continue", "confidence": 0.99, "final": True}, palm((0, 100, 200))),
    ]
    return [{**base, "id": cid, "intent_stop": intent, "voice": v, "gesture_frames": g}
            for cid, intent, v, g in rows]


def build_cases():
    return {"voice": voice_cases(), "gesture": gesture_cases(), "crossmodal": crossmodal_cases()}


def main():
    out = HERE / "datasets"
    out.mkdir(parents=True, exist_ok=True)
    for name, cases in build_cases().items():
        (out / f"{name}.jsonl").write_text(
            "".join(json.dumps(x, sort_keys=True) + "\n" for x in cases))
        print(f"{name}={len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
