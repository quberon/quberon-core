from datetime import datetime, timedelta, timezone

from adapters.isaac_sim import (
    DeterministicIsaacTransport,
    IsaacBridgeRequest,
    IsaacSimBridgeAdapter,
)
from integrations.recognizers import (
    GestureFrame,
    HandLandmark,
    OpenPalmStopRecognizer,
    VoiceObservation,
    VoiceStopRecognizer,
)


def open_palm(timestamp_ms: int, visibility: float = 1.0) -> GestureFrame:
    points = [HandLandmark(0.5, 0.85, visibility) for _ in range(21)]
    points[0] = HandLandmark(0.5, 0.9, visibility)
    for chain, x in zip(OpenPalmStopRecognizer.FINGER_CHAINS, (0.38, 0.47, 0.56, 0.65)):
        for index, y in zip(chain, (0.62, 0.49, 0.36, 0.22)):
            points[index] = HandLandmark(x, y, visibility)
    points[4] = HandLandmark(0.25, 0.48, visibility)
    return GestureFrame(timestamp_ms, points)


def test_voice_recognizer_requires_final_confident_standalone_stop():
    recognizer = VoiceStopRecognizer(minimum_confidence=0.85)
    assert recognizer.recognize(VoiceObservation("STOP", 0.9, True)).stop_requested is True
    assert recognizer.recognize(VoiceObservation("STOP", 0.84, True)).stop_requested is False
    assert recognizer.recognize(VoiceObservation("STOP", 0.99, False)).stop_requested is False
    assert recognizer.recognize(VoiceObservation("do not stop", 0.99, True)).stop_requested is False
    assert recognizer.recognize(VoiceObservation("nonstop", 0.99, True)).stop_requested is False


def test_open_palm_requires_visibility_consecutive_frames_and_hold():
    recognizer = OpenPalmStopRecognizer(minimum_hold_ms=700, minimum_frames=3)
    accepted = recognizer.recognize([open_palm(0), open_palm(350), open_palm(700)])
    assert accepted.stop_requested is True and accepted.held_ms == 700
    assert recognizer.recognize([open_palm(0), open_palm(300), open_palm(600)]).stop_requested is False
    assert recognizer.recognize([open_palm(0, 0.5), open_palm(400, 0.5), open_palm(800, 0.5)]).stop_requested is False


def test_isaac_bridge_contract_acknowledges_only_observed_stop():
    transport = DeterministicIsaacTransport("sim-1", "robot-1", "warehouse-a")
    adapter = IsaacSimBridgeAdapter(transport, "sim-1", "robot-1", "warehouse-a")
    result = adapter.stop("cmd-1")
    assert result.command_state == "ACKNOWLEDGED"
    assert result.observed_state == "ISAAC_SIM_STOPPED"
    assert adapter.simulated_task("SIMULATE_INSPECTION").command_state == "UNKNOWN"
    assert adapter.reset_simulation().command_state == "UNKNOWN"


def test_isaac_transport_rejects_wrong_scene_stale_replay_and_non_stop():
    transport = DeterministicIsaacTransport("sim-1", "robot-1", "scene-a")
    now = datetime.now(timezone.utc)

    def request(command_id, sequence, command="STOP", scene="scene-a", issued=now, expires=None):
        return IsaacBridgeRequest(
            "quberon.isaac-sim.v1", "sim-1", "robot-1", scene, command_id,
            sequence, command, issued.isoformat(), (expires or now + timedelta(seconds=5)).isoformat()
        )

    assert transport.exchange(request("wrong-scene", 1, scene="scene-b")).applied is False
    assert transport.exchange(request("stale", 2, issued=now - timedelta(seconds=10), expires=now - timedelta(seconds=1))).applied is False
    assert transport.exchange(request("move", 3, command="MOVE")).applied is False
    good = transport.exchange(request("good", 4))
    assert good.applied is True
    duplicate = transport.exchange(request("good", 4))
    assert duplicate == good
    assert transport.exchange(request("replay", 4)).applied is False
