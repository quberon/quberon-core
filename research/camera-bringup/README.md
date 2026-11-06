# Camera bring-up harness

Code-only harness. No physical hardware is exercised by its tests.

It enumerates video devices (`/dev/video*`, enriched with name/driver from
`/sys/class/video4linux` when present), probes resolution, frame rate,
capture latency and dropped frames through an injected device interface,
and writes a capture manifest recording device, driver, settings,
per-frame UTC + monotonic timestamps, sha256 of each frame, and the UTC
window. Frame files are pixel bytes only: EXIF and location/GPS metadata
are stripped on write and their values never enter the manifest.

## Run

No camera (expected on most hosts):

    python3 research/camera-bringup/harness.py --output-dir /tmp/cam-out

Prints `NO DEVICE: ...`, writes `/tmp/cam-out/manifest.json` with
`"status": "NO_DEVICE"`, and exits 0.

Deterministic synthetic capture (labelled `"synthetic": true`):

    python3 research/camera-bringup/harness.py --synthetic --frames 5 --output-dir /tmp/cam-out

On a host where devices are enumerated but no capture backend is injected,
status is `UNSUPPORTED_BACKEND` -- this stdlib harness does not claim real
OS capture, latency, or camera qualification.

## Test

    python -m pytest research/camera-bringup/tests -q
