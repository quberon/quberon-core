#!/bin/sh
# One-time display environment on the Pi (system site packages provide
# spidev + gpiozero from Raspberry Pi OS; the venv adds Pillow + qrcode).
set -eu
cd "$HOME/quberon-robot-interface"
python3 -m venv --system-site-packages .venv-display
.venv-display/bin/pip install --disable-pip-version-check "Pillow==11.0.0" "qrcode==8.2"
.venv-display/bin/python -c "import PIL, qrcode, spidev, gpiozero; print('display env ok')"
