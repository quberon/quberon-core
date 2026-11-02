#!/usr/bin/env python3
"""Render the 800x480 LIVE status image for the e-ink display.

Honesty rules: e-ink cannot blink. The LIVE dot alternates filled/hollow on
each scheduled refresh (300 s), next to the exact 'Updated' timestamp and the
GNSS age, so a frozen display is obvious. GPS coordinates are shown only when
the receiver reports them; otherwise the real state (NO FIX etc.) is shown.
"""
import json, os, time
from datetime import datetime, timezone
from pathlib import Path
import qrcode
from qrcode.constants import ERROR_CORRECT_Q
from PIL import Image, ImageDraw, ImageFont

URL = os.environ.get("CONTROL_URL", "https://10.99.0.1:8443/robots/quberon-demo-001")
STATUS = Path(os.path.expanduser(os.environ.get("GNSS_STATUS", "~/.local/share/quberon-robot-interface/gnss-status.json")))
TOGGLE = Path(os.path.expanduser("~/.local/share/quberon-robot-interface/live-toggle"))
OUT = os.environ.get("OUT", str(Path.home() / "quberon-robot-interface" / "artifacts" / "display-live.png"))

BOLD = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
REG = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font(size, bold=False):
    for p in BOLD if bold else REG:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def next_toggle() -> bool:
    val = False
    try:
        val = TOGGLE.read_text().strip() != "1"
    except OSError:
        val = True
    TOGGLE.parent.mkdir(parents=True, exist_ok=True)
    TOGGLE.write_text("1" if val else "0")
    return val


def main() -> int:
    try:
        gnss = json.loads(STATUS.read_text())
    except Exception:
        gnss = {"state": "NO_DEVICE", "satellites_used": None, "latitude": None, "longitude": None, "age_seconds": None, "utc": None}
    live_on = next_toggle()
    now_local = datetime.now().strftime("%H:%M:%S")
    age = gnss.get("age_seconds")

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=4, box_size=6)
    qr.add_data(URL); qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("1")

    img = Image.new("1", (800, 480), 1)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 799, 72), fill=0)
    d.text((400, 36), "QUBERON DEMO ROBOT", fill=1, font=font(36, True), anchor="mm")

    # Robot icon (simple line robot), left
    d.rectangle((40, 110, 190, 220), outline=0, width=4)          # head
    d.line((115, 110, 115, 82), fill=0, width=4)                    # antenna
    if live_on:
        d.ellipse((104, 66, 126, 88), fill=0)
    else:
        d.ellipse((104, 66, 126, 88), outline=0, width=3)
    d.ellipse((72, 148, 92, 168), fill=0)                           # eyes
    d.ellipse((138, 148, 158, 168), fill=0)
    d.line((78, 196, 152, 196), fill=0, width=4)                    # mouth
    d.rectangle((55, 224, 175, 330), outline=0, width=4)          # body
    d.line((55, 250, 22, 292), fill=0, width=4)                     # arms
    d.line((175, 250, 208, 292), fill=0, width=4)
    d.line((88, 330, 80, 372), fill=0, width=4)                     # legs
    d.line((142, 330, 150, 372), fill=0, width=4)

    # LIVE sign
    if live_on:
        d.ellipse((232, 122, 268, 158), fill=0)
    else:
        d.ellipse((232, 122, 268, 158), outline=0, width=4)
    d.text((280, 140), "LIVE", fill=0, font=font(40, True), anchor="lm")
    d.text((232, 176), f"Updated {now_local}", fill=0, font=font(24))
    d.text((232, 206), "(dot alternates each update)", fill=0, font=font(17))

    # GNSS block
    d.line((232, 244, 540, 244), fill=0, width=3)
    d.text((232, 258), "GPS - Here+ (u-blox)", fill=0, font=font(26, True))
    state = gnss.get("state", "NO_DEVICE")
    d.text((232, 292), f"Status: {state}", fill=0, font=font(26, True))
    sats = gnss.get("satellites_used")
    view = gnss.get("satellites_in_view")
    d.text((232, 326), f"Satellites used: {sats if sats is not None else '-'}  in view: {view if view is not None else '-'}", fill=0, font=font(21))
    if gnss.get("latitude") is not None and gnss.get("longitude") is not None:
        d.text((232, 356), f"Lat: {gnss['latitude']:.6f}", fill=0, font=font(27, True))
        d.text((232, 390), f"Lon: {gnss['longitude']:.6f}", fill=0, font=font(27, True))
    else:
        d.text((232, 356), "No coordinates yet", fill=0, font=font(24, True))
        d.text((232, 388), "(needs sky view for first fix)", fill=0, font=font(19))
    d.text((232, 424), f"GNSS data age: {age if age is not None else '-'} s", fill=0, font=font(19))

    # QR + access text right side
    img.paste(qr_img, (566, 92))
    d.text((232 - 232 + 640, 470), "", fill=0)  # no-op keeps layout clear
    d.text((580, 330), "ACCESS AND", fill=0, font=font(26, True))
    d.text((580, 362), "CONTROL", fill=0, font=font(26, True))
    d.text((580, 398), "Scan QR, join", fill=0, font=font(19))
    d.text((580, 420), "Quberon-Demo Wi-Fi", fill=0, font=font(19))
    d.text((580, 446), "SIMULATED - NOT AN EMERGENCY STOP", fill=0, font=font(13, True))

    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"wrote {OUT} live_on={live_on} gnss={state} sats={sats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
