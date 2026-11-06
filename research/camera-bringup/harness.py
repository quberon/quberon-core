"""Camera bring-up harness (code only, no physical hardware exercised).

Enumerates video devices, probes resolution / frame rate / capture latency /
dropped frames through a small device interface, and writes a capture
manifest. Real hosts with no camera report NO DEVICE cleanly (exit 0).

Stdlib only. It does not import or modify anything in app/, integrations/
or adapters/. Real OS capture is deliberately not claimed: without an
injected opener/backend, enumerated devices are reported as
UNSUPPORTED_BACKEND. Deterministic synthetic capture is available via
FakeCamera / ``--synthetic`` and is always labelled synthetic.

Metadata: frame files contain pixel bytes only. EXIF / location / GPS (and
similar) metadata supplied by a device is stripped on write -- neither frame
files nor the manifest carry its values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

SCHEMA_VERSION = 1
STATUS_NO_DEVICE = "NO_DEVICE"
STATUS_COMPLETED = "COMPLETED"
STATUS_UNSUPPORTED = "UNSUPPORTED_BACKEND"
STATUS_ERROR = "ERROR"

_STRIPPED_TOKENS = ("exif", "gps", "location", "geo", "latitude", "longitude",
                    "lat", "lon", "lng", "altitude", "make", "model")


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def strip_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return metadata with EXIF/location-like keys removed (values dropped)."""
    if not metadata:
        return {}
    out = {}
    for k, v in metadata.items():
        lk = str(k).lower()
        if any(tok in lk for tok in _STRIPPED_TOKENS):
            continue
        out[str(k)] = v
    return out


@dataclass(frozen=True)
class DeviceInfo:
    path: str
    name: str = "unknown"
    driver: str = "unknown"
    index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "name": self.name, "driver": self.driver,
                "index": self.index}


@dataclass(frozen=True)
class CaptureSettings:
    width: int = 640
    height: int = 480
    fps: float = 30.0
    frames: int = 10

    def validate(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width/height must be positive")
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if self.frames <= 0:
            raise ValueError("frames must be positive")

    def to_dict(self) -> Dict[str, Any]:
        return {"width": self.width, "height": self.height, "fps": self.fps,
                "frames": self.frames}


@dataclass
class Frame:
    data: bytes
    width: int
    height: int
    sequence: Optional[int] = None
    timestamp_monotonic_ns: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class FakeClock:
    """Deterministic monotonic + UTC clock shared by harness and FakeCamera."""

    def __init__(self, start_ns: int = 1_000_000_000,
                 start_utc: Optional[datetime] = None):
        self._ns = start_ns
        self._utc = start_utc or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def monotonic_ns(self) -> int:
        return self._ns

    def advance_ns(self, delta: int) -> None:
        self._ns += int(delta)
        # UTC advances with monotonic in this deterministic clock.
        from datetime import timedelta
        self._utc = self._utc + timedelta(microseconds=int(delta) // 1000)

    def utc_now(self) -> datetime:
        return self._utc


class FakeCamera:
    """Deterministic synthetic camera. Never touches hardware."""

    def __init__(self, info: Optional[DeviceInfo] = None, clock: Optional[FakeClock] = None,
                 sequences: Optional[Sequence[int]] = None,
                 latency_ns: int = 2_000_000,
                 include_metadata: bool = True):
        self.info = info or DeviceInfo(path="synthetic://camera-0", name="FakeCamera",
                                       driver="synthetic", index=0)
        self._clock = clock
        self._sequences = list(sequences) if sequences is not None else None
        self._latency_ns = latency_ns
        self._include_metadata = include_metadata
        self._settings: Optional[CaptureSettings] = None
        self._pos = 0

    def open(self, settings: CaptureSettings) -> None:
        settings.validate()
        self._settings = settings

    def read_frame(self) -> Frame:
        if self._settings is None:
            raise RuntimeError("FakeCamera.read_frame before open")
        seq = self._sequences[self._pos] if self._sequences is not None else self._pos
        self._pos += 1
        if self._clock is not None:
            self._clock.advance_ns(self._latency_ns)
            ts = self._clock.monotonic_ns()
        else:
            ts = time.monotonic_ns()
        w, h = self._settings.width, self._settings.height
        # 1 byte/pixel grayscale pattern, pixel bytes only.
        data = bytes(((seq * 31 + i) % 256) for i in range(w * h))
        meta = {}
        if self._include_metadata:
            meta = {"EXIF": {"Make": "synthetic"}, "GPSLatitude": 0.0,
                    "location": "synthetic-location", "frame_counter": seq}
        return Frame(data=data, width=w, height=h, sequence=seq,
                     timestamp_monotonic_ns=ts, metadata=meta)

    def close(self) -> None:
        self._settings = None


def _driver_from_sysfs(sysfs_entry: Path) -> str:
    driver_link = sysfs_entry / "device" / "driver"
    try:
        if not driver_link.exists():
            return "unknown"
        return Path(driver_link).resolve().name or "unknown"
    except Exception:
        return "unknown"


def enumerate_devices(dev_dir: Path = Path("/dev"),
                      sysfs_dir: Path = Path("/sys/class/video4linux")) -> List[DeviceInfo]:
    """Enumerate /dev/video* nodes, enriched from sysfs when present.

    Injectable roots make this testable with no host camera. Missing roots
    yield [] (NO DEVICE), never an exception.
    """
    devices: List[DeviceInfo] = []
    try:
        nodes = sorted(Path(dev_dir).glob("video*"))
    except Exception:
        return []
    for node in nodes:
        m = re.search(r"(\d+)$", node.name)
        if not m:
            continue
        idx = int(m.group(1))
        name, driver = "unknown", "unknown"
        entry = Path(sysfs_dir) / node.name
        try:
            name_file = entry / "name"
            if name_file.is_file():
                name = name_file.read_text(errors="replace").strip() or "unknown"
            if entry.exists():
                driver = _driver_from_sysfs(entry)
        except Exception:
            pass
        devices.append(DeviceInfo(path=str(node), name=name, driver=driver, index=idx))
    return devices


class _SystemDevice:
    """An enumerated OS node with no stdlib capture backend in this harness."""

    def __init__(self, info: DeviceInfo):
        self.info = info

    def open(self, settings: CaptureSettings) -> None:
        raise RuntimeError("no capture backend available in stdlib harness for %s" % self.info.path)

    def read_frame(self) -> Frame:  # pragma: no cover
        raise RuntimeError("device not open")

    def close(self) -> None:
        pass


def _latency_stats(values_ms: List[float]) -> Dict[str, Any]:
    if not values_ms:
        return {"count": 0, "mean_ms": None, "min_ms": None, "max_ms": None}
    return {"count": len(values_ms), "mean_ms": sum(values_ms) / len(values_ms),
            "min_ms": min(values_ms), "max_ms": max(values_ms)}


def run_capture(devices: Sequence[DeviceInfo],
                opener: Optional[Callable[[DeviceInfo], Any]] = None,
                settings: Optional[CaptureSettings] = None,
                output_dir: Optional[Path] = None,
                synthetic: bool = False,
                monotonic_ns: Callable[[], int] = time.monotonic_ns,
                utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> Dict[str, Any]:
    """Probe the first device and write manifest (+pixel-only frames).

    Returns the manifest dict. NO DEVICE / UNSUPPORTED / ERROR are data,
    not exceptions (except invalid settings, which raise ValueError).
    """
    settings = settings or CaptureSettings()
    settings.validate()
    started = utc_now()
    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS_NO_DEVICE,
        "reason": None,
        "synthetic": bool(synthetic),
        "qualification_claim": "NONE - code-only harness; no physical camera qualified",
        "utc_window": {"started_at": _iso(started), "ended_at": None},
        "devices": [d.to_dict() for d in devices],
        "device": None, "driver": None,
        "settings": settings.to_dict(),
        "probe": None,
        "frames": [],
        "metadata_handling": "stripped_on_write: frame files are pixel bytes only; "
                             "EXIF/location/GPS metadata values are excluded from manifest",
    }

    def finish() -> Dict[str, Any]:
        manifest["utc_window"]["ended_at"] = _iso(utc_now())
        if output_dir is not None:
            write_manifest(manifest, Path(output_dir))
        return manifest

    if not devices:
        manifest["reason"] = "no video devices enumerated on this host"
        return finish()

    chosen = devices[0]
    manifest["device"] = chosen.to_dict()
    manifest["driver"] = chosen.driver
    device = None
    try:
        device = opener(chosen) if opener is not None else _SystemDevice(chosen)
        device.open(settings)
    except Exception as exc:
        manifest["status"] = STATUS_UNSUPPORTED if opener is None else STATUS_ERROR
        manifest["reason"] = "%s: %s" % (type(exc).__name__, exc)
        if device is not None:
            try:
                device.close()
            except Exception:
                pass
        return finish()

    frames_meta: List[Dict[str, Any]] = []
    latencies: List[float] = []
    seqs: List[int] = []
    timestamps: List[int] = []
    resolutions = set()
    try:
        frames_dir = Path(output_dir) / "frames" if output_dir is not None else None
        if frames_dir is not None:
            frames_dir.mkdir(parents=True, exist_ok=True)
        for i in range(settings.frames):
            t0 = monotonic_ns()
            frame = device.read_frame()
            t1 = monotonic_ns()
            if not frame.data:
                raise RuntimeError("device returned an empty frame")
            latencies.append((t1 - t0) / 1e6)
            ts_ns = frame.timestamp_monotonic_ns if frame.timestamp_monotonic_ns is not None else t1
            timestamps.append(ts_ns)
            if frame.sequence is not None:
                seqs.append(frame.sequence)
            resolutions.add((frame.width, frame.height))
            # strip_metadata is applied and its (non-sensitive) result is
            # intentionally not persisted except harmless kept keys; frame
            # files get pixel bytes only.
            _kept = {k: v for k, v in strip_metadata(frame.metadata).items()
                     if k == "frame_counter"}
            rel = None
            if frames_dir is not None:
                fname = "frame-%06d.raw" % i
                (frames_dir / fname).write_bytes(frame.data)
                rel = "frames/" + fname
            frames_meta.append({
                "index": i, "sequence": frame.sequence,
                "timestamp_utc": _iso(utc_now()), "timestamp_monotonic_ns": int(ts_ns),
                "width": frame.width, "height": frame.height,
                "byte_length": len(frame.data),
                "sha256": hashlib.sha256(frame.data).hexdigest(),
                "file": rel,
                "kept_metadata": _kept,
            })
    except Exception as exc:
        manifest["status"] = STATUS_ERROR
        manifest["reason"] = "%s: %s" % (type(exc).__name__, exc)
        manifest["frames"] = frames_meta
        try:
            device.close()
        except Exception:
            pass
        return finish()

    try:
        device.close()
    except Exception:
        pass

    dropped = 0
    if len(seqs) >= 2:
        dropped = sum(max(0, b - a - 1) for a, b in zip(seqs, seqs[1:]))
    measured_fps = None
    if len(timestamps) >= 2 and timestamps[-1] > timestamps[0]:
        measured_fps = (len(timestamps) - 1) / ((timestamps[-1] - timestamps[0]) / 1e9)
    manifest["frames"] = frames_meta
    manifest["probe"] = {
        "resolution": ({"width": sorted(resolutions)[0][0], "height": sorted(resolutions)[0][1]}
                       if resolutions else {"width": None, "height": None}),
        "resolutions_observed": [{"width": w, "height": h} for w, h in sorted(resolutions)],
        "resolution_matches_requested": resolutions == {(settings.width, settings.height)},
        "requested_fps": settings.fps,
        "measured_fps": measured_fps,
        "capture_latency_ms": _latency_stats(latencies),
        "captured_frames": len(frames_meta),
        "dropped_frames": dropped,
        "expected_frames_by_sequence": (seqs[-1] - seqs[0] + 1) if len(seqs) >= 2 else len(frames_meta),
    }
    manifest["status"] = STATUS_COMPLETED
    return finish()


def write_manifest(manifest: Dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "manifest.json"
    tmp = output_dir / ".manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Camera bring-up harness (no hardware required)")
    p.add_argument("--output-dir", default="camera-bringup-output")
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--fps", type=float, default=30.0)
    p.add_argument("--frames", type=int, default=10)
    p.add_argument("--synthetic", action="store_true", help="use deterministic FakeCamera")
    p.add_argument("--device", default=None, help="only consider this device path")
    args = p.parse_args(argv)
    try:
        settings = CaptureSettings(args.width, args.height, args.fps, args.frames)
        settings.validate()
    except ValueError as exc:
        print("ERROR: %s" % exc)
        return 2
    out = Path(args.output_dir)
    if args.synthetic:
        clock = FakeClock()
        cam = FakeCamera(clock=clock)
        manifest = run_capture([cam.info], opener=lambda _info: cam, settings=settings,
                               output_dir=out, synthetic=True,
                               monotonic_ns=clock.monotonic_ns, utc_now=clock.utc_now)
    else:
        devices = enumerate_devices()
        if args.device:
            devices = [d for d in devices if d.path == args.device]
        manifest = run_capture(devices, settings=settings, output_dir=out)
    if manifest["status"] == STATUS_NO_DEVICE:
        print("NO DEVICE: %s" % manifest["reason"])
        print("manifest: %s" % (out / "manifest.json"))
        return 0
    print("%s: device=%s frames=%d manifest=%s" % (
        manifest["status"],
        (manifest.get("device") or {}).get("path"),
        len(manifest.get("frames") or []), out / "manifest.json"))
    return 0 if manifest["status"] in (STATUS_COMPLETED, STATUS_UNSUPPORTED) else 2


if __name__ == "__main__":
    sys.exit(main())
