#!/bin/sh
# One LIVE display update cycle: render fresh status image, then one bounded refresh.
set -eu
cd "$HOME/quberon-robot-interface"
.venv-display/bin/python scripts/render_live_display.py
timeout 90 .venv-display/bin/python scripts/show_qr_display.py artifacts/display-live.png
