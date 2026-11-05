"""Deterministic, simulation-only voice and gesture safety recognizers.

These recognizers consume already-derived observations. They do not access a
microphone, camera, physical robot, or vendor SDK. Their only actionable
output is a STOP intervention candidate; they can never request reset, resume,
or motion.
"""
from dataclasses import dataclass
from typing import Optional, Sequence

from integrations.interventions import match_transcript


@dataclass(frozen=True)
class VoiceObservation:
    transcript: str
    confidence: float
    final: bool = True


@dataclass(frozen=True)
class VoiceDecision:
    stop_requested: bool
    reason: str
    matched_token: Optional[str] = None


class VoiceStopRecognizer:
    """Conservative recognizer over a final transcript observation."""

    def __init__(self, minimum_confidence: float = 0.85):
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        self.minimum_confidence = minimum_confidence

    def recognize(self, observation: VoiceObservation) -> VoiceDecision:
        if not observation.final:
            return VoiceDecision(False, "interim transcript rejected")
        if not 0.0 <= observation.confidence <= 1.0:
            return VoiceDecision(False, "invalid confidence")
        if observation.confidence < self.minimum_confidence:
            return VoiceDecision(False, "confidence below threshold")
        token = match_transcript(observation.transcript)
        if token is None:
            return VoiceDecision(False, "no standalone stop command")
        return VoiceDecision(True, "final transcript matched stop command", token)


@dataclass(frozen=True)
class HandLandmark:
    x: float
    y: float
    visibility: float = 1.0


@dataclass(frozen=True)
class GestureFrame:
    timestamp_ms: int
    landmarks: Sequence[HandLandmark]


@dataclass(frozen=True)
class GestureDecision:
    stop_requested: bool
    reason: str
    qualifying_frames: int = 0
    held_ms: int = 0


class OpenPalmStopRecognizer:
    """Detect a sustained upright open palm from normalized hand landmarks.

    Landmark order follows the common 21-point hand layout used by MediaPipe
    and similar pipelines. The recognizer is intentionally deterministic and
    dependency-free so recorded or Isaac Sim-derived fixtures can test the
    safety path without claiming a camera integration.
    """

    FINGER_CHAINS = ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))

    def __init__(self, minimum_hold_ms: int = 700, minimum_frames: int = 3, minimum_visibility: float = 0.8):
        if minimum_hold_ms < 0 or minimum_frames < 1 or not 0.0 <= minimum_visibility <= 1.0:
            raise ValueError("invalid gesture recognizer thresholds")
        self.minimum_hold_ms = minimum_hold_ms
        self.minimum_frames = minimum_frames
        self.minimum_visibility = minimum_visibility

    def _is_open_palm(self, frame: GestureFrame) -> bool:
        points = frame.landmarks
        if len(points) != 21:
            return False
        if any(not 0.0 <= p.x <= 1.0 or not 0.0 <= p.y <= 1.0 or p.visibility < self.minimum_visibility for p in points):
            return False
        wrist = points[0]
        palm_width = abs(points[5].x - points[17].x)
        palm_height = wrist.y - points[9].y
        if palm_width < 0.08 or palm_height < 0.08:
            return False
        for mcp, pip, dip, tip in self.FINGER_CHAINS:
            if not (points[tip].y < points[dip].y < points[pip].y < points[mcp].y < wrist.y):
                return False
        thumb_span = abs(points[4].x - points[5].x)
        return points[4].y < wrist.y and thumb_span >= palm_width * 0.35

    def recognize(self, frames: Sequence[GestureFrame]) -> GestureDecision:
        if not frames:
            return GestureDecision(False, "no frames")
        ordered = sorted(frames, key=lambda f: f.timestamp_ms)
        best_count = best_held = run_count = 0
        run_start: Optional[int] = None
        previous: Optional[int] = None
        for frame in ordered:
            if previous is not None and frame.timestamp_ms <= previous:
                return GestureDecision(False, "timestamps must be unique and increasing")
            previous = frame.timestamp_ms
            if self._is_open_palm(frame):
                if run_count == 0:
                    run_start = frame.timestamp_ms
                run_count += 1
                assert run_start is not None
                held = frame.timestamp_ms - run_start
                if run_count > best_count or (run_count == best_count and held > best_held):
                    best_count, best_held = run_count, held
            else:
                run_count = 0
                run_start = None
        if best_count < self.minimum_frames:
            return GestureDecision(False, "insufficient consecutive open-palm frames", best_count, best_held)
        if best_held < self.minimum_hold_ms:
            return GestureDecision(False, "open palm not held long enough", best_count, best_held)
        return GestureDecision(True, "sustained upright open palm", best_count, best_held)
