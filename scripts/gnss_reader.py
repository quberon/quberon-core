#!/usr/bin/env python3
"""Passive Here+/u-blox NMEA reader -> atomic JSON status file.

Read-only: opens the by-id serial device, parses GGA/RMC/GSV, writes
~/.local/share/quberon-robot-interface/gnss-status.json once per second.
Never transmits anything to the receiver and never logs raw streams.
Coordinates appear only when the receiver itself reports a fix.
"""
import json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from adapters.gnss import GnssStatus, parse_sentence  # noqa: E402

DEVICE = os.environ.get("GNSS_DEVICE", "/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_GNSS_receiver-if00")
OUT = Path(os.path.expanduser(os.environ.get("GNSS_STATUS", "~/.local/share/quberon-robot-interface/gnss-status.json")))


def main() -> int:
    status = GnssStatus(state="NO_DATA")
    last_rx = 0.0
    last_write = 0.0
    buf = b""
    fd = None
    while True:
        try:
            if fd is None:
                fd = os.open(DEVICE, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
                status.state = "NO_DATA"
            import select
            r, _, _ = select.select([fd], [], [], 1.0)
            if r:
                try:
                    chunk = os.read(fd, 8192)
                except BlockingIOError:
                    chunk = b""
                if chunk:
                    buf += chunk
                    last_rx = time.time()
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        if len(line) > 120:
                            continue
                        try:
                            text = line.decode("ascii", errors="ignore")
                        except Exception:
                            continue
                        if text.startswith("$"):
                            parse_sentence(text, status)
        except FileNotFoundError:
            status = GnssStatus(state="NO_DEVICE")
            fd = None
            time.sleep(5)
        except OSError:
            try:
                if fd is not None:
                    os.close(fd)
            except OSError:
                pass
            fd = None
            time.sleep(2)

        now = time.time()
        if fd is not None and last_rx and now - last_rx > 5 and status.state not in ("NO_DEVICE",):
            status.state = "NO_DATA"
        if now - last_write >= 1.0:
            last_write = now
            status.age_seconds = round(now - last_rx, 1) if last_rx else None
            payload = {
                "state": status.state,
                "fix_type": status.fix_type,
                "satellites_used": status.satellites,
                "satellites_in_view": status.satellites_in_view,
                "hdop": status.accuracy_m,
                "latitude": status.latitude,
                "longitude": status.longitude,
                "utc": status.utc,
                "age_seconds": status.age_seconds,
                "received_at_epoch": round(last_rx, 1) if last_rx else None,
            }
            OUT.parent.mkdir(parents=True, exist_ok=True)
            tmp = OUT.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload))
            os.replace(tmp, OUT)


if __name__ == "__main__":
    raise SystemExit(main())
