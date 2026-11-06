# STOP-path animation (viz-3) — SIMULATED, replayed evidence only

This is not an artist's impression and not a physical robot. Every frame
is rendered from a trace built by replaying actual sources in this repo:

1. Copper deterministic replay — `spikes/copper-stop-path/evidence/`
   (`comparison.txt`, original/replay task-output bins and unified logs).
   Byte-identity is re-verified at build time; hashes are in `trace.json`.
2. fleet-sim — `fleet-sim/fleet_sim.py:scripted_scenario()` executed
   twice in-process; traces must match and `trace_digest()` is recorded.
3. Fail-direction probes — the real `app.main` `execute_stop` path run
   against a temporary DB (same pattern as `tests/test_secure_core.py`):
   - core unavailable (`secure_core=None`): HTTP 200, adapter invoked
     once, STOP proceeds UNSIGNED, `stop_latched=True`.
   - core rejecting (stub raising `SecureCoreRejected(REPLAY_REJECTED)`,
     as in the upstream tests): HTTP 503, adapter invoked zero times,
     `command_state`/`observed_state` = UNKNOWN, `stop_latched=True`.
   That asymmetry is scenarios B vs C in the animation.

## Build

    .venv/bin/python -m viz.animation.render --repo . --out viz/animation/output
    .venv/bin/python -m pytest viz/animation/tests -q

Outputs (`viz/animation/output/`): `frames/frame-*.svg` (one per trace
event, stages sensor -> recognition -> authorization -> actuator),
`stop-path-animation.svg` (animated), `trace.json`, `manifest.json`,
`png/frame-*.png`, and `stop-path-animation.mp4` **only if ffmpeg is on
PATH**. If ffmpeg is absent, `manifest.json` records
`video: {status: "SKIPPED", reason: ...}` — the step is never silently
dropped (covered by `test_video_skipped_recorded_when_ffmpeg_absent`).

Every frame carries the red `SIMULATED - NOT A PHYSICAL ROBOT` band and
`source_trace_sha256` (SHA-256 of the canonical trace JSON), so any
drift between the animation and the replayed evidence changes the hash.

## Limits

Simulated tasks only, mock/replayed traces, no hardware, no latency,
certification, physical-safety or regulatory claim. See the STILL NOT
TRUE section of `progress/viz-3-stop-path-animation.md`.
