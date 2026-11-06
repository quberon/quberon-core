NODE: cam-1-bringup-harness
TIER: 1
BRANCH: node/cam-1-bringup-harness
COMMITS: 03b3df7 feat(camera): add bring-up harness (cam-1); plus this progress commit (see git log on this branch)
STATUS: complete
CHANGED:
- research/camera-bringup/harness.py (stdlib-only enumeration, probe, manifest, FakeCamera/FakeClock, CLI)
- research/camera-bringup/tests/test_camera_bringup.py (8 tests)
- research/camera-bringup/README.md
- research/camera-bringup/evidence/{node-tests.log,full-with-rust.log,full-without-rust.log,cli-no-device.log,cli-synthetic.log,utc.txt}
- progress/cam-1-bringup-harness.md (this file)
No files in app/, integrations/ or adapters/ were imported or modified (AST test asserts this).

EVIDENCE:
- command: .venv/bin/python -m pytest research/camera-bringup/tests -q
  toolchain: Python 3.11.15 (.venv, requirements.txt), pytest 8.3.4; also checked system Python 3.9.6
  host: Darwin Quberon1.local 24.3.0 arm64 (see research/camera-bringup/evidence/utc.txt)
  UTC: 2026-11-06T12:43:48Z
  raw output path: research/camera-bringup/evidence/node-tests.log
  raw output: "8 passed in 0.02s", exit 0
- command: .venv/bin/python research/camera-bringup/harness.py --output-dir /tmp/cam-out-evidence
  raw output path: research/camera-bringup/evidence/cli-no-device.log
  raw output: "NO DEVICE: no video devices enumerated on this host", exit 0, manifest status NO_DEVICE appended to log
- command: .venv/bin/python research/camera-bringup/harness.py --synthetic --frames 3 --width 4 --height 3 --output-dir /tmp/cam-out-syn-evidence
  raw output path: research/camera-bringup/evidence/cli-synthetic.log
  raw output: "COMPLETED: device=synthetic://camera-0 frames=3", exit 0

TESTS (both modes):
- With Rust on PATH: .venv/bin/python -m pytest -q -> 207 passed, 12 skipped, exit 0. Raw: research/camera-bringup/evidence/full-with-rust.log
- With Rust removed from PATH (PATH=.venv/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin, cargo not found): .venv/bin/python -m pytest -q -> 207 passed, 12 skipped, exit 0. Raw: research/camera-bringup/evidence/full-without-rust.log
- Node only: python -m pytest research/camera-bringup/tests -q -> 8 passed, exit 0 (3.11; also passes under system python3.9 pytest invocation earlier in session: 8 passed)
- import app.main creating zero files: run in empty tmp dir with PYTHONPATH=repo -> "imported", find found 0 files. Observed in terminal, not committed as a log file.
- Fail-direction tests in the universal gate (ops/gate.sh): ops/gate.sh is not present in this repo (ls ops: No such file or directory), so that portion was run only via the modes above and is left for the scheduler's gate to execute. My own fail-direction checks: enumerated device without backend -> UNSUPPORTED_BACKEND (test), empty frame -> ERROR (test), invalid settings -> ValueError/CLI exit 2 path (test), NO DEVICE -> exit 0 (test).

STILL NOT TRUE:
- No physical camera, sensor, driver, resolution, frame rate, latency, or dropped-frame behaviour has been observed or qualified; all capture results are deterministic synthetic (FakeCamera) or NO_DEVICE/UNSUPPORTED_BACKEND.
- Real OS capture (V4L2/AVFoundation) is NOT implemented: enumerated devices without an injected backend report UNSUPPORTED_BACKEND, not captured frames.
- No certification, physical-safety, latency, or regulatory-compliance claim is supported by this repository or this harness.
- ops/gate.sh was not found in this checkout, so its fail-direction tests were not executed locally.

NEEDS A HUMAN DECISION:
- Whether a real capture backend (e.g. V4L2 ioctl / AVFoundation bridge) should be added in a later node, and on which target OS/hardware. This node deliberately makes no hardware claim.
