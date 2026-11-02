"""Display adapters. Physical Waveshare driving is intentionally not enabled
until panel identity, wiring and SPI are verified by a human."""
from pathlib import Path
from PIL import Image, ImageDraw


def render_mock_display(path: str, ssid: str, url: str, wifi_qr: str, url_qr: str) -> str:
    img = Image.new("1", (800, 480), 1)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 799, 70), fill=0)
    d.text((20, 20), "QUBERON DEMO - SIMULATED ROBOT", fill=1)
    d.text((20, 90), "NOT AN EMERGENCY STOP", fill=0)
    d.text((20, 120), "1. Join Quberon Wi-Fi", fill=0)
    d.text((420, 120), "2. Open robot controls", fill=0)
    for qr_path, x in ((wifi_qr, 30), (url_qr, 430)):
        if Path(qr_path).exists():
            qr = Image.open(qr_path).convert("1").resize((280, 280))
            img.paste(qr, (x, 150))
    d.text((20, 445), f"SSID: {ssid}   URL: {url}", fill=0)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


class MockDisplay:
    mode = "MOCK"

    def show_onboarding(self, **kwargs) -> str:
        return render_mock_display(**kwargs)
