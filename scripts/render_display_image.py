#!/usr/bin/env python3
"""Render the 800x480 e-ink image: one large control QR + safety text."""
import os
import qrcode
from qrcode.constants import ERROR_CORRECT_Q
from PIL import Image, ImageDraw

URL = os.environ.get("CONTROL_URL", "https://10.99.0.1:8443/robots/quberon-demo-001")
OUT = os.environ.get("OUT", "artifacts/display-control-qr.png")

qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=4, box_size=8)
qr.add_data(URL); qr.make(fit=True)
qr_img = qr.make_image(fill_color="black", back_color="white").convert("1")

img = Image.new("1", (800, 480), 1)
d = ImageDraw.Draw(img)
d.rectangle((0, 0, 799, 64), fill=0)
d.text((18, 24), "QUBERON DEMO - SIMULATED ROBOT", fill=1)
img.paste(qr_img, (24, 84))
d.text((440, 110), "NOT AN EMERGENCY STOP", fill=0)
d.text((440, 150), "Scan to open", fill=0)
d.text((440, 175), "robot controls.", fill=0)
d.text((440, 215), "Log in to", fill=0)
d.text((440, 240), "request STOP.", fill=0)
d.text((440, 300), "Static image:", fill=0)
d.text((440, 325), "status shown", fill=0)
d.text((440, 350), "on phone only.", fill=0)
d.text((24, 452), URL, fill=0)
img.save(OUT)
print(f"wrote {OUT} size={img.size} url={URL}")
