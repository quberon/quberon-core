"""Gate tests for viz/animation. Run: python -m pytest viz/animation/tests -q

These tests REPLAY the sources (Copper evidence bytes, fleet-sim twice,
real app fail-direction probes) and check the rendered frames against
them. They write only to tmp_path.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from viz.animation.render import render  # noqa: E402
from viz.animation.trace import STAGES, build_trace  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(scope="module")
def trace():
    return build_trace(REPO)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("viz-out")
    manifest = render(REPO, out)
    return out, manifest


def test_sources_replay_byte_identical(trace):
    c = trace["copper"]
    assert c["task_outputs_byte_identical"] is True
    assert c["copper_logs_byte_identical"] is True
    assert c["original_task_outputs_sha256"] == c["replay_task_outputs_sha256"]
    assert c["original_copper_log_sha256"] == c["replay_copper_log_sha256"]
    assert c["comparison"]["command"] == "STOP"
    assert c["comparison"]["authorized"] == "true"


def test_fleet_trace_deterministic(trace):
    f = trace["fleet"]
    assert f["replayed_twice_identical"] is True
    assert len(f["trace_sha256_digest"]) == 64
    assert f["single_node_stop_outcome"] == "LATCHED"
    assert f["single_node_motion_permitted_after_stop"] is False


def test_trace_sha_is_reproducible(trace):
    again = build_trace(REPO)
    assert again["source_trace_sha256"] == trace["source_trace_sha256"]


def test_fail_direction_asymmetry(trace):
    """THE asymmetry: unavailable -> unsigned STOP proceeds; rejecting ->
    STOP blocked. Both retain the latch; only rejecting yields UNKNOWN."""
    p = trace["fail_probes"]
    assert p["status"] == "RUN", p
    u, r = p["core_unavailable"], p["core_rejecting"]
    # core unavailable: STOP proceeds unsigned with the latch retained
    assert u["http_status"] == 200
    assert u["adapter_invocations"] == 1
    assert u["secure_core"]["status"] == "unavailable"
    assert u["secure_core"]["decision"] is None
    assert u["stop_latched"] is True
    assert u["command_state"] == "ACKNOWLEDGED"
    # core rejecting: STOP is blocked with state UNKNOWN, latch retained
    assert r["http_status"] == 503
    assert r["adapter_invocations"] == 0
    assert r["secure_core"]["status"] == "rejected"
    assert r["secure_core"]["decision"] == "REPLAY_REJECTED"
    assert r["stop_latched"] is True
    assert r["observed_state"] == "UNKNOWN"
    assert r["command_state"] == "UNKNOWN"


def test_every_frame_carries_simulated_band_and_sha(built, trace):
    out, manifest = built
    sha = trace["source_trace_sha256"]
    assert manifest["source_trace_sha256"] == sha
    frames = sorted((out / "frames").glob("frame-*.svg"))
    assert len(frames) == len(trace["events"]) == len(manifest["frames"])
    for f in frames:
        text = f.read_text()
        assert "SIMULATED - NOT A PHYSICAL ROBOT" in text
        assert f"source_trace_sha256={sha}" in text
    animated = (out / "stop-path-animation.svg").read_text()
    assert "SIMULATED" in animated and sha in animated


def test_stages_in_order_per_scenario(trace):
    seen = {}
    for ev in trace["events"]:
        seen.setdefault(ev["scenario"], []).append(ev["stage"])
    for scenario, stages in seen.items():
        if scenario == "fail_direction":
            continue
        assert stages == STAGES, (scenario, stages)


def test_video_step_never_silently_dropped(built):
    out, manifest = built
    video = manifest["video"]  # key must exist whatever happened
    assert video["status"] in ("encoded", "SKIPPED")
    if video["status"] == "encoded":
        mp4 = out / video["file"]
        assert mp4.exists() and mp4.stat().st_size > 0
    else:
        assert video["reason"], "SKIPPED must record why"


def test_video_skipped_recorded_when_ffmpeg_absent(tmp_path, monkeypatch):
    import viz.animation.render as rmod
    monkeypatch.setattr(rmod.shutil, "which", lambda name: None)
    manifest = rmod.render(REPO, tmp_path / "noffmpeg")
    assert manifest["video"]["status"] == "SKIPPED"
    assert "ffmpeg" in manifest["video"]["reason"]


def test_no_physical_robot_claim(built):
    out, _ = built
    for f in list((out / "frames").glob("*.svg")) + [out / "stop-path-animation.svg"]:
        text = f.read_text()
        # the only robot wording allowed is the explicit negation
        assert "physical robot" not in text.lower().replace(
            "not a physical robot", "")
    m = json.loads((out / "manifest.json").read_text())
    assert m["simulated"] is True and m["physical_robot"] is False


def test_trace_json_on_disk_matches(built, trace):
    out, _ = built
    disk = json.loads((out / "trace.json").read_text())
    assert disk["source_trace_sha256"] == trace["source_trace_sha256"]
    assert disk["events"] == trace["events"]
