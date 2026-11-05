# Intervention inputs — deterministic safety recognition

Status: **implemented and tested for simulation.** The application accepts bounded, authenticated voice transcript observations and normalized hand-landmark frames. It does not capture microphone or camera data and does not control physical hardware.

## Safety invariants

- Recognition can only request `STOP`; it cannot reset/unlatch, resume, start a task, or issue motion.
- Every accepted result converges on the existing authenticated, CSRF-protected, idempotent, persistently latched STOP service.
- Low-confidence, interim, negated, malformed, stale, or insufficient observations do nothing.
- Source labels remain descriptive, not proof of authority. Session role and CSRF establish authority.
- Adapter failure remains `UNKNOWN`; recognition never upgrades an unconfirmed stop to success.

## Voice input

`POST /api/robots/{robot_id}/safety-inputs/voice`

```json
{
  "event_id": "microphone-session-42-final-7",
  "transcript": "STOP",
  "confidence": 0.97,
  "final": true
}
```

`VoiceStopRecognizer` requires a final transcript, confidence of at least `0.85`, and the existing conservative standalone `STOP`/`STOPP` matcher. `nonstop`, `do not stop`, and interim or low-confidence results are rejected.

## Gesture input

`POST /api/robots/{robot_id}/safety-inputs/gesture`

The body contains an event ID and up to 60 frames. Each frame has a monotonic millisecond timestamp and exactly 21 normalized hand landmarks (`x`, `y`, `visibility`). `OpenPalmStopRecognizer` requires:

- all landmarks visible at `>= 0.8`;
- an upright, extended four-finger geometry and separated thumb;
- at least three consecutive qualifying frames;
- a hold duration of at least 700 ms.

This is a deterministic geometry recognizer for recorded/device/Isaac-derived observations, not a claim that camera capture or field accuracy has been validated. Thresholds require dataset calibration before any broader use.

## Existing generic event route

`POST /api/robots/{robot_id}/interventions` remains available for synthetic fixtures and upstream recognizers. `PANIC_CANDIDATE` remains audit-only and never triggers or clears STOP.
