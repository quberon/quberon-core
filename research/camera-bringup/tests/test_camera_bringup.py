import ast
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(__file__)
HARNESS_PATH = os.path.join(HERE, "..", "harness.py")
_spec = importlib.util.spec_from_file_location("camera_bringup_harness", HARNESS_PATH)
assert _spec is not None and _spec.loader is not None
h = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = h  # dataclasses on py3.9 need module in sys.modules
_spec.loader.exec_module(h)


def small_settings(**kw):
    base = dict(width=4, height=3, fps=30.0, frames=4)
    base.update(kw)
    return h.CaptureSettings(**base)


def test_no_device_reports_no_device_and_writes_manifest(tmp_path):
    manifest = h.run_capture([], settings=small_settings(), output_dir=tmp_path)
    assert manifest["status"] == "NO_DEVICE"
    assert manifest["device"] is None and manifest["probe"] is None
    assert manifest["frames"] == []
    assert manifest["utc_window"]["started_at"].endswith("Z")
    assert manifest["utc_window"]["ended_at"].endswith("Z")
    on_disk = json.loads((tmp_path / "manifest.json").read_text())
    assert on_disk == manifest


def test_cli_no_device_prints_no_device_not_obscure_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(h, "enumerate_devices", lambda: [])
    rc = h.main(["--output-dir", str(tmp_path / "out")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "NO DEVICE" in out
    assert json.loads((tmp_path / "out" / "manifest.json").read_text())["status"] == "NO_DEVICE"


def test_enumeration_with_sysfs_driver_and_name(tmp_path):
    dev = tmp_path / "dev"; sysfs = tmp_path / "sysfs"
    (sysfs / "video0").mkdir(parents=True); (sysfs / "video2").mkdir(parents=True)
    dev.mkdir()
    (dev / "video2").touch(); (dev / "video0").touch(); (dev / "notavideo").touch()
    (sysfs / "video0" / "name").write_text("Test Cam\n")
    driver_dir = tmp_path / "drivers" / "uvcvideo"; driver_dir.mkdir(parents=True)
    (sysfs / "video0" / "device").mkdir()
    os.symlink(driver_dir, sysfs / "video0" / "device" / "driver")
    devices = h.enumerate_devices(dev_dir=dev, sysfs_dir=sysfs)
    assert [d.index for d in devices] == [0, 2]
    assert devices[0].name == "Test Cam" and devices[0].driver == "uvcvideo"
    assert devices[1].name == "unknown" and devices[1].driver == "unknown"
    assert h.enumerate_devices(dev_dir=tmp_path / "missing", sysfs_dir=sysfs) == []


def test_capture_probe_manifest_hashes_latency_fps_and_drops(tmp_path):
    clock = h.FakeClock()
    cam = h.FakeCamera(clock=clock, sequences=[0, 1, 3, 6])
    m = h.run_capture([cam.info], opener=lambda _i: cam, settings=small_settings(),
                      output_dir=tmp_path, synthetic=True,
                      monotonic_ns=clock.monotonic_ns, utc_now=clock.utc_now)
    assert m["status"] == "COMPLETED" and m["synthetic"] is True
    assert m["device"]["path"] == "synthetic://camera-0"
    assert m["driver"] == "synthetic"
    assert m["settings"] == {"width": 4, "height": 3, "fps": 30.0, "frames": 4}
    probe = m["probe"]
    assert probe["resolution"] == {"width": 4, "height": 3}
    assert probe["resolution_matches_requested"] is True
    assert probe["measured_fps"] == 500.0  # 2 ms deterministic frame interval
    assert probe["capture_latency_ms"] == {"count": 4, "mean_ms": 2.0, "min_ms": 2.0, "max_ms": 2.0}
    assert probe["dropped_frames"] == 3  # missing seq 2, 4, 5
    assert probe["expected_frames_by_sequence"] == 7
    assert probe["captured_frames"] == 4
    assert [f["sequence"] for f in m["frames"]] == [0, 1, 3, 6]
    assert len({f["timestamp_monotonic_ns"] for f in m["frames"]}) == 4
    assert all(f["timestamp_utc"].endswith("Z") for f in m["frames"])
    for f in m["frames"]:
        raw = (tmp_path / f["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == f["sha256"]
        assert len(raw) == f["byte_length"] == 12


def test_exif_and_location_stripped_on_write(tmp_path):
    clock = h.FakeClock()
    cam = h.FakeCamera(clock=clock)
    m = h.run_capture([cam.info], opener=lambda _i: cam, settings=small_settings(frames=2),
                      output_dir=tmp_path, synthetic=True,
                      monotonic_ns=clock.monotonic_ns, utc_now=clock.utc_now)
    text = (tmp_path / "manifest.json").read_text()
    assert "synthetic-location" not in text
    assert '"GPSLatitude"' not in text and '"EXIF":' not in text
    for f in m["frames"]:
        assert "synthetic-location" not in (tmp_path / f["file"]).read_bytes().decode("latin1")
        assert set(f["kept_metadata"]) <= {"frame_counter"}
    assert h.strip_metadata({"EXIF": 1, "GPSLatitude": 2, "location": 3, "frame_counter": 7}) == {"frame_counter": 7}


def test_enumerated_device_without_backend_is_unsupported_not_crash(tmp_path):
    info = h.DeviceInfo(path="/dev/video99", name="x", driver="drv", index=99)
    m = h.run_capture([info], settings=small_settings(), output_dir=tmp_path)
    assert m["status"] == "UNSUPPORTED_BACKEND"
    assert m["driver"] == "drv" and "no capture backend" in m["reason"]
    assert (tmp_path / "manifest.json").exists()


def test_empty_frame_and_invalid_settings_are_clean_errors(tmp_path):
    class Empty:
        info = h.DeviceInfo(path="empty://0", driver="empty")
        def open(self, s): pass
        def read_frame(self): return h.Frame(data=b"", width=1, height=1)
        def close(self): pass
    dev = Empty()
    m = h.run_capture([dev.info], opener=lambda _i: dev, settings=small_settings(frames=1),
                      output_dir=tmp_path)
    assert m["status"] == "ERROR" and "empty frame" in m["reason"]
    try:
        h.CaptureSettings(width=0).validate()
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_no_forbidden_imports():
    tree = ast.parse(open(HARNESS_PATH).read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & {"app", "integrations", "adapters"})
