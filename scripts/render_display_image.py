#!/usr/bin/env python3
"""Render the 800x480 e-ink image: one large control QR + large readable text."""
import os
import qrcode
from qrcode.constants import ERROR_CORRECT_Q
from PIL import Image, ImageDraw, ImageFont

URL = os.environ.get("CONTROL_URL", "https://10.99.0.1:8443/robots/quberon-demo-001")
OUT = os.environ.get("OUT", "artifacts/display-control-qr.png")

FONT_CANDIDATES_BOLD = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def font(size: int, bold: bool = False):
    for path in FONT_CANDIDATES_BOLD if bold else FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=4, box_size=8)
qr.add_data(URL); qr.make(fit=True)
qr_img = qr.make_image(fill_color="black", back_color="white").convert("1")

img = Image.new("1", (800, 480), 1)
d = ImageDraw.Draw(img)

# Header
d.rectangle((0, 0, 799, 72), fill=0)
d.text((400, 36), "QUBERON DEMO ROBOT", fill=1, font=font(36, bold=True), anchor="mm")

# QR, left
img.paste(qr_img, (26, 88))
d.text((190, 434), "10.99.0.1:8443", fill=0, font=font(21, bold=True), anchor="ma")
d.text((190, 458), "/robots/quberon-demo-001", fill=0, font=font(17), anchor="ma")

# Right side, large text
x = 388
d.text((x, 96), "NOT AN", fill=0, font=font(38, bold=True))
d.text((x, 140), "EMERGENCY", fill=0, font=font(38, bold=True))
d.text((x, 184), "STOP", fill=0, font=font(38, bold=True))
d.line((x, 238, 772, 238), fill=0, width=3)
d.text((x, 254), "1. Join Wi-Fi:", fill=0, font=font(27, bold=True))
d.text((x + 24, 290), "Quberon-Demo", fill=0, font=font(27))
d.text((x, 330), "2. Scan the QR code", fill=0, font=font(27, bold=True))
d.text((x, 366), "3. Log in and", fill=0, font=font(27, bold=True))
d.text((x + 24, 402), "request STOP", fill=0, font=font(27, bold=True))

img.save(OUT)
print(f"wrote {OUT} size={img.size} url={URL}")
