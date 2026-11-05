# Intervention inputs — EXPERIMENTAL / PLANNED (not implemented)

Status: **roadmap only.** No voice recognizer, gesture detector, or intervention-event module was implemented in the final pass. This document defines the contract so future work cannot quietly become a weaker second stop path.

## Contract (planned `integrations/interventions.py`)

Typed event: robot ID, event ID, timestamp, input kind, source status, optional bounded evidence text.
Kinds: `BUTTON`, `VOICE_STOP`, `GESTURE_STOP`, `PANIC_CANDIDATE`.
Source status must record whether an event was synthetic, browser-recognized, or device-recognized. A client-supplied label is **not** proof of sensor provenance or user authority.

Rules for any future implementation:

- All accepted interventions go through the existing STOP service: authenticated capability check, CSRF for browser sessions, idempotency, persistent latch, actual adapter result. No second, weaker stop route.
- Generating an event never grants reset/resume or movement permission.
- No anonymous physical stop access. A guest demo, if ever designed, is isolated to a simulated robot with an explicit policy.
- Minimum tests before claiming anything: duplicates converge; wrong robot rejected; unauthorized source/session rejected; stale events rejected or labelled; model failure does not block STOP; injected event cannot clear latch; adapter failure remains `UNKNOWN`; source label cannot bypass authority.

## Voice

A deterministic transcript matcher (standalone `STOP`, optionally documented Swedish `STOPP`; no substring matching — `nonstop` must not trigger) tests the matcher only. Synthetic fixtures are not proof a microphone works. Browser SpeechRecognition, if added, must be opt-in, show consent/listening/failure states, and is not Meta-powered unless a real Meta transcription service is actually called. Panic recognition stays roadmap: a loud sound or text label does not establish distress or acceptable error rates.

## Gesture

Defined gesture (e.g. open palm held to camera) with visibility/distance/duration conditions. Until a detector is implemented and tested with measured false/missed detections, only explicitly labelled synthetic `GESTURE_STOP` fixtures may exercise the event path. A button labelled "inject gesture event" is a developer test control, not gesture recognition.
