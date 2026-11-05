import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# Load by path under a unique name: research/adversarial also has a generate.py
# and plain `import generate` collides with it in full-suite collection.
_spec = importlib.util.spec_from_file_location(
    "safety_inputs_generate", os.path.join(os.path.dirname(__file__), "..", "generate.py"))
assert _spec is not None and _spec.loader is not None
_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gen)
build_cases = _gen.build_cases
from harness import load, rates, run_gesture, run_voice, to_frames  # noqa: E402
from integrations.recognizers import OpenPalmStopRecognizer, VoiceObservation, VoiceStopRecognizer  # noqa: E402

REQUIRED = {"false_trigger", "stale_replay", "degraded_confidence", "contradictory_signals"}


def all_cases():
    return [c for name in ("voice", "gesture", "crossmodal") for c in load(name)]


def summary():
    return json.loads(open(os.path.join(os.path.dirname(__file__), "..", "results", "summary.json")).read())


def test_datasets_are_deterministic_and_cover_required_boundaries():
    assert build_cases() == {n: load(n) for n in ("voice", "gesture", "crossmodal")}
    cats = {c["category"] for c in all_cases()}
    assert REQUIRED <= cats
    assert {"canonical_positive", "hold_frame_boundary", "missed_trigger_boundary"} <= cats
    assert all(c["synthetic"] is True for c in all_cases())
    ids = [c["id"] for c in all_cases()]
    assert len(ids) == len(set(ids)) == 83


def test_voice_confidence_and_finality_boundary_exact():
    r = VoiceStopRecognizer()
    assert r.recognize(VoiceObservation("STOP", 0.85, True)).stop_requested is True
    assert r.recognize(VoiceObservation("STOP", 0.849, True)).stop_requested is False
    assert r.recognize(VoiceObservation("STOP", 1.0, False)).stop_requested is False
    assert r.recognize(VoiceObservation("STOP", 1.01, True)).stop_requested is False


def test_gesture_hold_frames_visibility_boundary_exact():
    cases = {c["id"]: c for c in load("gesture")}
    g = OpenPalmStopRecognizer()
    assert g.recognize(to_frames(cases["G-POS-00"]["frames"])).stop_requested is True   # 3 frames, 700 ms
    assert g.recognize(to_frames(cases["G-HOLD-01"]["frames"])).stop_requested is False  # 699 ms
    assert g.recognize(to_frames(cases["G-HOLD-03"]["frames"])).stop_requested is False  # 2 frames, 700 ms
    assert g.recognize(to_frames(cases["G-VIS-02"]["frames"])).stop_requested is False  # 0.79
    assert g.recognize(to_frames(cases["G-VIS-03"]["frames"])).stop_requested is True   # 0.80
    assert g.recognize(to_frames(cases["G-DUPTS-00"]["frames"])).stop_requested is False  # duplicate ts


def test_stale_and_replay_blocked_only_at_harness_pipeline_layer():
    cases = {c["id"]: c for c in load("voice")}
    seen = set()
    fresh = run_voice(cases["V-REPLAY-00"], seen)
    replay = run_voice(cases["V-REPLAY-01"], seen)
    assert fresh["pipeline"] is True
    # Recognizer alone re-triggers on replay; harness event_id guard blocks it.
    assert replay["recognizer"] is True and replay["pipeline"] is False
    stale = run_voice(cases["V-STALE-00"], set())
    assert stale["recognizer"] is True and stale["pipeline"] is False


def test_summary_rates_have_denominators_and_no_qualification_claim():
    s = summary()
    assert s["synthetic_only"] is True and s["qualification_claim"].startswith("NONE")
    assert s["total"]["n"] == 83
    for group in (s["total"], *s["by_modality"].values(), *s["by_category"].values()):
        for key in ("false_trigger_rate_FP_over_FP_plus_TN", "missed_trigger_rate_FN_over_FN_plus_TP"):
            r = group[key]
            assert isinstance(r["numerator"], int) and isinstance(r["denominator"], int)
            assert 0 <= r["numerator"] <= r["denominator"]
    assert s["by_category"]["voice:canonical_positive"]["missed_trigger_rate_FN_over_FN_plus_TP"] == {
        "numerator": 0, "denominator": 6, "rate": 0.0}
    assert s["by_category"]["gesture:canonical_positive"]["missed_trigger_rate_FN_over_FN_plus_TP"] == {
        "numerator": 0, "denominator": 3, "rate": 0.0}
    assert s["false_trigger_ids"] == ["V-NEG-08"]  # standalone 'stop' in non-command sentence
    assert rates([])["false_trigger_rate_FP_over_FP_plus_TN"]["rate"] is None
