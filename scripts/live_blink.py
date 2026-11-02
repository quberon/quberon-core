#!/usr/bin/env python3
"""Blink a small LIVE badge on the 7.5" V2 e-ink via PARTIAL refresh only.

Design constraints (panel care):
- The static base image (QR view) is drawn with ONE full refresh, outside this loop.
- This process uses epd.init_part() + display_Partial() on a small 176x48 px
  badge region, toggling every 1.0 s. No full refreshes inside the loop except
  a rebase every 180 toggles (~3 min) to clear partial-refresh ghosting; that
  rebase pauses blinking for a few seconds.
- Stop the service to stop blinking; a final full refresh restores the base.
"""
import json, os, sys, time
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/waveshare-lib"))
from waveshare_epd import epd7in5_V2, epdconfig  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

BASE = Path(os.path.expanduser("~/quberon-robot-interface/artifacts/display-control-qr.png"))
# Badge region (x must be multiples of 8): right of the QR, above ACCESS text.
X0, Y0, X1, Y1 = 560, 88, 736, 136
REBASE_EVERY = 180

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GNSS_STATUS = Path(os.path.expanduser("~/.local/share/quberon-robot-interface/gnss-status.json"))


def _font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except Exception:
        return ImageFont.load_default()


def dynamic_base() -> Image.Image:
    """Static QR view + current GPS line (refreshed at start and each rebase)."""
    img = Image.open(BASE).convert("1")
    d = ImageDraw.Draw(img)
    try:
        g = json.loads(GNSS_STATUS.read_text())
    except Exception:
        g = {"state": "NO_DEVICE", "satellites_used": None, "latitude": None, "longitude": None, "age_seconds": None}
    d.rectangle((16, 424, 372, 478), fill=1)
    if g.get("latitude") is not None and g.get("longitude") is not None:
        d.text((20, 430), f"GPS: {g['latitude']:.6f}, {g['longitude']:.6f}", fill=0, font=_font(19))
        d.text((20, 456), f"{g.get('state')} - sats {g.get('satellites_used')} - age {g.get('age_seconds')}s", fill=0, font=_font(15))
    else:
        d.text((20, 430), f"GPS: {g.get('state', 'NO_DEVICE')} - sats {g.get('satellites_used')}", fill=0, font=_font(20))
        d.text((20, 456), "No coordinates (needs sky view)", fill=0, font=_font(15))
    return img


def badge(on: bool, base_img: Image.Image) -> Image.Image:
    img = Image.new("1", (800, 480), 1)
    img.paste(base_img, (0, 0))
    d = ImageDraw.Draw(img)
    try:
        fnt = ImageFont.truetype(FONT, 26)
    except Exception:
        fnt = ImageFont.load_default()
    if on:
        d.rectangle((X0, Y0, X1 - 1, Y1 - 1), fill=0)
        d.ellipse((X0 + 10, Y0 + 14, X0 + 30, Y0 + 34), fill=1)
        d.text((X0 + 40, Y0 + 10), "LIVE", fill=1, font=fnt)
    else:
        d.rectangle((X0, Y0, X1 - 1, Y1 - 1), fill=1, outline=0, width=2)
        d.ellipse((X0 + 10, Y0 + 14, X0 + 30, Y0 + 34), outline=0, width=2)
        d.text((X0 + 40, Y0 + 10), "LIVE", fill=0, font=fnt)
    return img


def main() -> int:
    epd = epd7in5_V2.EPD()
    base = dynamic_base()
    if epd.init() != 0:
        return 1
    epd.display(epd.getbuffer(base))
    if epd.init_part() != 0:
        return 1
    on = True
    cycles = 0
    try:
        while True:
            start = time.time()
            epd.display_Partial(epd.getbuffer(badge(on, base)), 0, 0, 800, 480)
            on = not on
            cycles += 1
            if cycles >= REBASE_EVERY:
                cycles = 0
                base = dynamic_base()
                if epd.init() == 0:
                    epd.display(epd.getbuffer(base))
                epd.init_part()
            elapsed = time.time() - start
            time.sleep(max(0.0, 1.0 - elapsed))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if epd.init() == 0:
                epd.display(epd.getbuffer(base))
            epd.sleep()
        finally:
            epdconfig.module_exit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
