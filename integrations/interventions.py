"""Multimodal intervention events — experimental groundwork.

Frontier principle: a superintelligence-era interface may *receive* signals
from many modalities, but no signal source grants itself authority. Voice,
gesture and panic labels are untrusted inputs; authority comes only from the
authenticated session, and every accepted stop flows through the one
deterministic STOP service (latch, idempotency, audit, adapter result).

What this module is:
  - A typed event contract + a deterministic transcript matcher for tests.
  - Synthetic/browser/device source *labels* (labels are not provenance proof).

What this module is NOT:
  - Not speech recognition. Matching a transcript tests the matcher only.
  - Not gesture recognition. No camera detector exists in this project.
  - Not panic detection. A label never establishes distress; PANIC_CANDIDATE
    is audit-only and never triggers a stop by itself.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class InterventionKind(str, Enum):
    BUTTON = "BUTTON"
    VOICE_STOP = "VOICE_STOP"
    GESTURE_STOP = "GESTURE_STOP"
    PANIC_CANDIDATE = "PANIC_CANDIDATE"


class SourceStatus(str, Enum):
    SYNTHETIC = "SYNTHETIC"                    # test fixture, developer-injected
    BROWSER_RECOGNIZED = "BROWSER_RECOGNIZED"  # e.g. Web Speech result, unverified
    DEVICE_RECOGNIZED = "DEVICE_RECOGNIZED"    # on-device recognizer, unverified
    CLIENT_LABELLED = "CLIENT_LABELLED"        # caller merely claims a modality


# Kinds allowed to request a stop. PANIC_CANDIDATE is deliberately absent.
STOP_KINDS = {InterventionKind.BUTTON, InterventionKind.VOICE_STOP, InterventionKind.GESTURE_STOP}

MAX_EVIDENCE_CHARS = 200
MAX_EVENT_AGE_SECONDS = 300        # older events are stale
MAX_FUTURE_SKEW_SECONDS = 30       # small clock skew allowance

_NEGATIONS = {"don't", "dont", "do", "not", "never", "inte", "ej", "no"}
_STOP_TOKENS = {"stop", "stopp"}


def match_transcript(text: str) -> Optional[str]:
    """Return the matched stop token, or None.

    Policy (explicit, conservative):
      - Token-based: 'nonstop' never matches; the token must stand alone.
      - Negated commands ('do not stop', 'inte stopp') never match.
      - Quoted/reported speech is not distinguished — a human operator
        remains in the loop; this matcher is not a protective function.
    """
    if not isinstance(text, str) or len(text) > MAX_EVIDENCE_CHARS:
        return None
    tokens = re.findall(r"[a-zåäö']+", text.lower())
    if _NEGATIONS.intersection(tokens):
        # 'do' only negates when adjacent to not/n't patterns handled above;
        # any negation vocabulary present => refuse to infer a stop command.
        if {"not", "inte", "ej", "never", "don't", "dont", "no"} & set(tokens):
            return None
    for tok in tokens:
        if tok in _STOP_TOKENS:
            return tok
    return None


@dataclass
class InterventionEvent:
    robot_id: str
    event_id: str
    kind: InterventionKind
    source_status: SourceStatus
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_text: str = ""

    def age_seconds(self, now: Optional[datetime] = None) -> float:
        return ((now or datetime.now(timezone.utc)) - self.timestamp).total_seconds()

    def staleness(self, now: Optional[datetime] = None) -> Optional[str]:
        age = self.age_seconds(now)
        if age > MAX_EVENT_AGE_SECONDS:
            return f"stale event ({int(age)}s old)"
        if age < -MAX_FUTURE_SKEW_SECONDS:
            return "event timestamp is in the future"
        return None

    def validate(self, expected_robot_id: str, now: Optional[datetime] = None) -> list:
        errors = []
        if self.robot_id != expected_robot_id:
            errors.append("robot mismatch")
        if not self.event_id or len(self.event_id) > 128:
            errors.append("event_id required (<=128 chars, used as idempotency key)")
        if len(self.evidence_text or "") > MAX_EVIDENCE_CHARS:
            errors.append("evidence_text too long")
        stale = self.staleness(now)
        if stale:
            errors.append(stale)
        if self.kind == InterventionKind.VOICE_STOP and match_transcript(self.evidence_text or "") is None:
            errors.append("transcript does not contain a standalone stop command")
        return errors
