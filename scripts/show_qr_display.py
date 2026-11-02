#!/usr/bin/env python3
"""One bounded full-refresh of the control QR on a Waveshare 7.5" V2 (800x480).

Safety properties:
- Runs the official waveshare_epd epd7in5_V2 driver in this process only.
- Parent/caller should run with an external timeout; this script also records a
  refresh timestamp and refuses if the last refresh was <180 s ago.
- Always attempts epd.sleep() + module_exit() in a finally block.
- Simulation-only content; e-ink is never used for live STOP confirmation.
"""
import os, sys, time
from pathlib import Path

LOCK = Path(os.path.expanduser("~/.local/share/quberon-robot-interface/last-display-refresh"))
MIN_INTERVAL_S = 180


def main() -> int:
    image_path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/quberon-robot-interface/artifacts/display-control-qr.png")
    now = time.time()
    if LOCK.exists() and now - float(LOCK.read_text().strip() or 0) < MIN_INTERVAL_S:
        print("REFUSED: last refresh <180s ago (e-ink protection)")
        return 2
    sys.path.insert(0, os.path.expanduser("~/waveshare-lib"))
    from waveshare_epd import epd7in5_V2
    from PIL import Image

    img = Image.open(image_path).convert("1")
    if img.size != (800, 480):
        print(f"REFUSED: image must be 800x480, got {img.size}")
        return 2
    epd = epd7in5_V2.EPD()
    try:
        if epd.init() != 0:
            print("ERROR: epd.init failed")
            return 1
        epd.display(epd.getbuffer(img))
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(str(time.time()))
        print("DISPLAY_REFRESH_DONE")
        return 0
    finally:
        try:
            epd.sleep()
        except Exception as exc:
            print(f"sleep warning: {type(exc).__name__}")
        try:
            from waveshare_epd import epdconfig
            epdconfig.module_exit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
