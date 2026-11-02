#!/usr/bin/env python3
import argparse, os
import qrcode
from qrcode.constants import ERROR_CORRECT_Q


def wifi_payload(ssid: str, password: str) -> str:
    def esc(v: str) -> str:
        return v.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:").replace('"', '\\"')
    return f"WIFI:T:WPA;S:{esc(ssid)};P:{esc(password)};;"


def make(payload: str, path: str):
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=4, box_size=10)
    qr.add_data(payload); qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(path)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ssid", default=os.environ.get("AP_SSID", "Quberon-Demo"))
    p.add_argument("--url", default=os.environ.get("CONTROL_URL", "https://10.99.0.1:8443/robots/quberon-demo-001"))
    p.add_argument("--outdir", default="artifacts")
    p.add_argument("--wifi-password-env", default="AP_PASSWORD")
    a = p.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    pw = os.environ.get(a.wifi_password_env, "")
    if not pw:
        raise SystemExit(f"Set {a.wifi_password_env}; the PSK is deliberately printed in the Wi-Fi QR only, not in source")
    make(wifi_payload(a.ssid, pw), os.path.join(a.outdir, "wifi-qr.png"))
    make(a.url, os.path.join(a.outdir, "control-url-qr.png"))
    print("generated wifi-qr.png and control-url-qr.png")
