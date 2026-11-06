# Node viz-3-stop-path-animation

NODE: viz-3-stop-path-animation
TIER: 1
BRANCH: node/viz-3-stop-path-animation
COMMITS: f639261 (code + output + this file as first committed); PR #53. Any later hash is this progress-file amendment — see git log on the branch.
STATUS: complete (gate green locally; PR to be opened, not self-merged)

## What was built

Animation of the intervention path sensor -> recognition ->
authorization -> simulated actuator outcome, rendered frame-by-frame
from an ACTUAL replayed trace, not an artist's impression:

- viz/animation/trace.py builds the trace from three replayed sources:
  (1) Copper deterministic replay evidence in
  spikes/copper-stop-path/evidence/ — comparison.txt parsed,
  original/replay task-output bins and unified logs re-hashed and
  re-checked byte-identical at build time;
  (2) fleet-sim scripted_scenario() executed twice in-process —
  traces must be identical, trace_digest() recorded
  (bc00d02757b140236eff8687b4934a3cb373aee72759281b1f87087d13e79eb0);
  (3) fail-direction probes through the real app.main execute_stop
  path on a temporary DB, exactly as tests/test_secure_core.py does.
- viz/animation/render.py emits, per trace event, an SVG frame
  (viz/animation/output/frames/frame-000..011.svg, 12 frames =
  3 scenarios x 4 stages), an animated stop-path-animation.svg,
  trace.json, manifest.json, PNG frames, and — only because ffmpeg
  was present on this host — stop-path-animation.mp4 (75664 bytes).
  If ffmpeg is absent the manifest records
  video={status:"SKIPPED", reason:"ffmpeg not found on PATH"};
  that branch is covered by
  test_video_skipped_recorded_when_ffmpeg_absent and was also run
  manually (raw result in EVIDENCE). Never silently dropped.
- Every frame carries the red band "SIMULATED - NOT A PHYSICAL ROBOT -
  REPLAYED TRACE ONLY" and source_trace_sha256=
  fa5fc598748094b1c5d86cd7b11c336c18359487aceabe824ee858a48c0e44c3.
  Nothing is presented as a physical robot (test_no_physical_robot_claim).

## Fail-direction behaviour shown explicitly (the asymmetry)

From the actual app probes in trace.json (fail_probes.status=RUN):
- Core UNAVAILABLE (scenario B): HTTP 200, adapter_invocations=1,
  secure_core.status=unavailable, decision/sequence/audit_record=null,
  command_state=ACKNOWLEDGED, stop_latched=True.
  => STOP proceeds UNSIGNED with the latch retained.
- Core REJECTING (scenario C, SecureCoreRejected REPLAY_REJECTED):
  HTTP 503, adapter_invocations=0, secure_core.status=rejected,
  decision=REPLAY_REJECTED, command_state=UNKNOWN,
  observed_state=UNKNOWN, stop_latched=True.
  => STOP is blocked with state UNKNOWN, latch retained.

## EVIDENCE

- command: .venv/bin/python -m viz.animation.render --repo . --out viz/animation/output
  toolchain: Python 3.11.15, cargo 1.99.1, rustc 1.99.1,
  ffmpeg 9.0.1 (at /Users/quberon1/.hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffmpeg)
  host: Darwin Quberon1.local 24.3.0 arm64
  UTC: 2026-11-06T11:30:44Z (session start) through gate runs same day
  raw output: viz/animation/output/manifest.json,
  viz/animation/output/trace.json,
  viz/animation/output/evidence/full-with-rust.log,
  viz/animation/output/evidence/full-without-rust.log,
  viz/animation/output/evidence/fail-direction.log
- ffmpeg-absent manual run: PATH=/usr/bin:/bin render ->
  {'status': 'SKIPPED', 'reason': 'ffmpeg not found on PATH', 'tool': None}
- Copper hashes: task outputs sha256
  249509dc1dd8890886210406a1d5bee1787d6a896165acdcec7aac606506361d
  (original == replay), comparison command=STOP authorized=true.

## TESTS (both modes)

- Node gate: .venv/bin/python -m pytest viz/animation/tests -q
  -> 10 passed (raw in full-suite logs; standalone run 10 passed, 1 warning)
- Full suite with Rust: .venv/bin/python -m pytest -q
  -> 221 passed, 2 warnings in 40.37s, EXIT:0
  (viz/animation/output/evidence/full-with-rust.log)
- Full suite with Rust removed from PATH:
  env PATH="$PWD/.venv/bin:/usr/bin:/bin" .venv/bin/python -m pytest -q
  -> 221 passed, 2 warnings in 39.86s, EXIT:0
  (viz/animation/output/evidence/full-without-rust.log; note the
  previously built target/debug CLI still existed on this host, so
  Rust-binary tests ran rather than skipped — PATH removal only)
- Both fail-direction tests + animation asymmetry test:
  tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not PASSED
  tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter PASSED
  viz/animation/tests/test_animation.py::test_fail_direction_asymmetry PASSED
  (viz/animation/output/evidence/fail-direction.log)
- import app.main creating zero files: run in a fresh mktemp dir ->
  "import ok", ls -A | wc -l = 0

## CHANGED

viz/animation/** (trace.py, render.py, __init__.py, README.md,
tests/test_animation.py, output/**) and this file only.

## STILL NOT TRUE

- This animation is replayed SIMULATED evidence only. It is not a
  physical robot, shows no physical actuator, and supports no
  physical-safety, certification, latency, real-time, or
  regulatory-compliance claim.
- The Copper spike remains a single-iteration, mock-clock, simulated
  three-task graph; byte-identical replay proves replay determinism
  of that spike, nothing about hardware behaviour.
- The fleet-sim trace is a logical-time simulation: no real transport,
  persistence/restart, Byzantine replicas, clock trust, or sensor
  truth is demonstrated.
- The core-rejecting probe uses the upstream test-suite's stub core
  raising SecureCoreRejected; a real reachable Rust core rejecting for
  each specific code (replay/expiry/scope) is covered upstream in
  tests/test_secure_core.py, not re-proven by this animation.
- The animated SVG timing (1 s/frame) is a display choice, not a
  measured system latency.
- No claim that ffmpeg will exist in CI: there the MP4 step will be
  recorded SKIPPED in manifest.json by design.

## NEEDS A HUMAN DECISION

- None blocking. Tier 1: PR opened for automatic merge once the gate
  passes and CI is green; not self-merged.
