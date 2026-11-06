"""Render the replayed trace as SVG frames + animated SVG, and MP4 iff
ffmpeg is present (otherwise the manifest records video SKIPPED).

Usage:
  python -m viz.animation.render [--repo .] [--out viz/animation/output]
Every frame carries the SIMULATED band and the source trace sha256.
Nothing is presented as a physical robot.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from viz.animation.trace import STAGES, build_trace  # noqa: E402

W, H = 960, 540
SCENARIO_LABEL = {
    "authorized_stop": "A - AUTHORIZED STOP (Copper replay + fleet latch)",
    "core_unavailable": "B - CORE UNAVAILABLE: STOP proceeds UNSIGNED, latch retained",
    "core_rejecting": "C - CORE REJECTING: STOP blocked, state UNKNOWN, latch retained",
    "fail_direction": "FAIL-DIRECTION PROBES SKIPPED",
}


def _wrap(text, n=88):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines[:4]


def frame_svg(event, idx, total, sha):
    active = STAGES.index(event["stage"]) if event["stage"] in STAGES else -1
    boxes = []
    for i, stage in enumerate(STAGES):
        x = 40 + i * 225
        fill = "#dc2626" if i == active else "#1e293b"
        stroke = "#fbbf24" if i == active else "#475569"
        boxes.append(
            f'<rect x="{x}" y="150" width="200" height="70" rx="10" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="3"/>'
            f'<text x="{x + 100}" y="180" fill="#fff" font-size="17" '
            f'text-anchor="middle" font-family="monospace">{stage.upper()}</text>'
            f'<text x="{x + 100}" y="205" fill="#cbd5e1" font-size="12" '
            f'text-anchor="middle" font-family="monospace">'
            f'{"ACTIVE" if i == active else ("done" if i < active else "pending")}</text>')
        if i < 3:
            boxes.append(f'<text x="{x + 212}" y="192" fill="#fbbf24" font-size="22" '
                         f'font-family="monospace">&gt;</text>')
    detail = "".join(
        f'<text x="40" y="{300 + j * 26}" fill="#e2e8f0" font-size="16" '
        f'font-family="monospace">{html.escape(line)}</text>'
        for j, line in enumerate(_wrap(event["detail"])))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" fill="#0f172a"/>
<rect width="{W}" height="52" fill="#7f1d1d"/>
<text x="{W // 2}" y="34" fill="#fff" font-size="20" font-weight="bold" text-anchor="middle" font-family="monospace">SIMULATED - NOT A PHYSICAL ROBOT - REPLAYED TRACE ONLY</text>
<text x="40" y="92" fill="#fbbf24" font-size="18" font-family="monospace">{html.escape(SCENARIO_LABEL.get(event["scenario"], event["scenario"]))}</text>
<text x="40" y="122" fill="#fff" font-size="19" font-family="monospace">{html.escape(event["title"])}</text>
{''.join(boxes)}
{detail}
<text x="40" y="440" fill="#94a3b8" font-size="13" font-family="monospace">frame {idx + 1}/{total}  scenario={html.escape(event["scenario"])}  stage={html.escape(event["stage"])}</text>
<text x="40" y="468" fill="#94a3b8" font-size="13" font-family="monospace">source_trace_sha256={sha}</text>
<text x="40" y="496" fill="#94a3b8" font-size="13" font-family="monospace">evidence: Copper deterministic replay (byte-identical) + fleet-sim trace + app fail-direction probes</text>
</svg>
'''


def animated_svg(frames, sha):
    n = len(frames)
    dur = n  # 1s per frame
    groups, css = [], []
    for i, svg in enumerate(frames):
        inner = svg.split("\n", 1)[1].rsplit("</svg>", 1)[0]
        groups.append(f'<g class="f{i}">{inner}</g>')
        css.append(f".f{i}{{opacity:0;animation:viz {dur}s linear infinite;"
                   f"animation-delay:{i}s}}")
    css.append(f"@keyframes viz{{0%{{opacity:1}}{100 / n:.4f}%{{opacity:1}}"
               f"{100 / n + 0.01:.4f}%{{opacity:0}}100%{{opacity:0}}}}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}"><style>{"".join(css)}</style>'
            f'<rect width="{W}" height="{H}" fill="#0f172a"/>'
            + "".join(groups)
            + f'<desc>SIMULATED replayed trace source_trace_sha256={sha}</desc></svg>\n')


def _png_frames(out: Path, trace):
    """PNG frames for ffmpeg. Returns (ok, reason)."""
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:
        return False, f"Pillow unavailable: {type(exc).__name__}"
    png_dir = out / "png"
    png_dir.mkdir(exist_ok=True)
    for i, ev in enumerate(trace["events"]):
        img = Image.new("RGB", (W, H), "#0f172a")
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 52], fill="#7f1d1d")
        d.text((20, 18), "SIMULATED - NOT A PHYSICAL ROBOT - REPLAYED TRACE ONLY", fill="white")
        d.text((40, 70), SCENARIO_LABEL.get(ev["scenario"], ev["scenario"])[:80], fill="#fbbf24")
        d.text((40, 100), ev["title"][:80], fill="white")
        for j, stage in enumerate(STAGES):
            x = 40 + j * 225
            fill = "#dc2626" if stage == ev["stage"] else "#1e293b"
            d.rectangle([x, 150, x + 200, 220], fill=fill)
            d.text((x + 12, 178), stage.upper(), fill="white")
        for j, line in enumerate(_wrap(ev["detail"])):
            d.text((40, 290 + j * 24), line, fill="#e2e8f0")
        d.text((40, 440), f"frame {i + 1}/{len(trace['events'])} scenario={ev['scenario']} stage={ev['stage']}", fill="#94a3b8")
        d.text((40, 468), f"source_trace_sha256={trace['source_trace_sha256']}", fill="#94a3b8")
        img.save(png_dir / f"frame-{i:03d}.png")
    return True, "ok"


def render(repo, out) -> dict:
    repo, out = Path(repo).resolve(), Path(out)
    trace = build_trace(repo)
    sha = trace["source_trace_sha256"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "trace.json").write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n")

    frames_dir = out / "frames"
    frames_dir.mkdir(exist_ok=True)
    svgs = [frame_svg(ev, i, len(trace["events"]), sha)
            for i, ev in enumerate(trace["events"])]
    for i, svg in enumerate(svgs):
        (frames_dir / f"frame-{i:03d}.svg").write_text(svg)
    (out / "stop-path-animation.svg").write_text(animated_svg(svgs, sha))

    # Video: ONLY if ffmpeg is present; otherwise record SKIPPED, never drop.
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        video = {"status": "SKIPPED", "reason": "ffmpeg not found on PATH",
                 "tool": None}
    else:
        ok, reason = _png_frames(out, trace)
        if not ok:
            video = {"status": "SKIPPED", "reason": reason, "tool": ffmpeg}
        else:
            mp4 = out / "stop-path-animation.mp4"
            proc = subprocess.run(
                [ffmpeg, "-y", "-framerate", "1", "-i", str(out / "png" / "frame-%03d.png"),
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mp4)],
                capture_output=True, text=True)
            if proc.returncode == 0 and mp4.exists() and mp4.stat().st_size > 0:
                video = {"status": "encoded", "tool": ffmpeg, "file": mp4.name,
                         "bytes": mp4.stat().st_size}
            else:
                video = {"status": "SKIPPED",
                         "reason": f"ffmpeg exit={proc.returncode}: {proc.stderr[-400:]}",
                         "tool": ffmpeg}
    manifest = {
        "kind": "quberon-viz-stop-path-animation/v1",
        "simulated": True,
        "physical_robot": False,
        "source_trace_sha256": sha,
        "copper_task_outputs_sha256": trace["copper"]["original_task_outputs_sha256"],
        "copper_byte_identical": trace["copper"]["task_outputs_byte_identical"],
        "fleet_trace_digest": trace["fleet"]["trace_sha256_digest"],
        "fail_probes_status": trace["fail_probes"].get("status"),
        "frames": [f"frames/frame-{i:03d}.svg" for i in range(len(svgs))],
        "animated_svg": "stop-path-animation.svg",
        "video": video,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default="viz/animation/output")
    a = ap.parse_args(argv)
    manifest = render(a.repo, a.out)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
