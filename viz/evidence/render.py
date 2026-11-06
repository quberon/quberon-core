#!/usr/bin/env python3
"""Deterministic renderer: committed evidence -> SVG figures.

No figure is hand-authored and none invents a number: every value is
read from the cited source file at render time. Every SVG embeds the
source path(s), source sha256, git commit, a UTC timestamp and an
evidence band (MEASURED-ON-HOST, SIMULATED, SYNTHETIC or NOT TESTED).

Determinism: no wall clock, no randomness, no dict-order dependence.
The embedded UTC is the committer date of the git commit that the
figure is rendered at (converted to UTC), not the time of rendering,
so running the renderer twice at the same commit on the same evidence
produces byte-identical output. If git is unavailable, commit and UTC
are the literal string "unknown" (also deterministic).

Usage:
    python3 viz/evidence/render.py [--repo-root .] [--out viz/evidence]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
from collections import Counter
from datetime import timezone
from pathlib import Path
from xml.sax.saxutils import escape

BANDS = ("MEASURED-ON-HOST", "SIMULATED", "SYNTHETIC", "NOT TESTED")
BAND_COLORS = {
    "MEASURED-ON-HOST": "#1a7f37",
    "SIMULATED": "#0969da",
    "SYNTHETIC": "#8250df",
    "NOT TESTED": "#cf222e",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def git_info(repo_root: Path):
    """Return (commit, utc) from HEAD, or ("unknown", "unknown")."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "log", "-1", "--format=%H%n%cI"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip().splitlines()
        commit, iso = out[0].strip(), out[1].strip()
        from datetime import datetime
        dt = datetime.fromisoformat(iso)
        utc = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return commit, utc
    except Exception:
        return "unknown", "unknown"


def _text(x, y, s, size=11, fill="#1f2328", anchor="start", weight="normal",
          family="monospace"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" '
            f'font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{escape(str(s))}</text>')


def svg_open(title, band, sources, commit, utc, width, extra_note=None):
    """Header shared by all figures. sources: list of (relpath, sha256).

    Height of the provenance block grows with the number of sources;
    returns (lines, y) where y is the first free content row.
    """
    if band not in BANDS:
        raise ValueError(f"unknown evidence band: {band}")
    prov_lines = 2 + len(sources) + (1 if extra_note else 0)
    header_h = 34 + 18 * prov_lines + 10
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="HEIGHT_PLACEHOLDER" viewBox="0 0 {width} HEIGHT_PLACEHOLDER">',
        f'<metadata>title={escape(title)}; band={band}; '
        + "; ".join(f"source={p} sha256={h}" for p, h in sources)
        + f'; git_commit={commit}; utc={utc}</metadata>',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        _text(10, 22, title, size=15, weight="bold", family="sans-serif"),
        # Evidence band: a filled pill, impossible to miss.
        f'<rect x="{width-190}" y="6" width="180" height="20" rx="4" '
        f'fill="{BAND_COLORS[band]}"/>',
        _text(width - 100, 20, band, size=11, fill="#ffffff", anchor="middle",
              weight="bold", family="sans-serif"),
    ]
    y = 42
    for p, h in sources:
        lines.append(_text(10, y, f"source: {p}  sha256: {h}", size=9))
        y += 14
    lines.append(_text(10, y, f"git_commit: {commit}  utc: {utc}", size=9))
    y += 14
    if extra_note:
        lines.append(_text(10, y, extra_note, size=9, fill="#57606a"))
        y += 14
    lines.append(f'<line x1="10" y1="{y}" x2="{width-10}" y2="{y}" '
                 f'stroke="#d0d7de"/>')
    return lines, y + 16, header_h


def svg_close(lines, height):
    lines.append("</svg>")
    out = "\n".join(lines) + "\n"
    return out.replace("HEIGHT_PLACEHOLDER", str(int(height)))


def fmt(v):
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


# ---------------------------------------------------------------- fleet
def render_fleet(repo_root, commit, utc):
    fleet_dir = Path(repo_root) / "fleet-sim"
    spec = importlib.util.spec_from_file_location(
        "viz_fleet_sim", fleet_dir / "fleet_sim.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    sim = mod.scripted_scenario()
    trace = list(sim.trace)
    trace_sha = sim.trace_digest()
    snapshot = json.dumps(sim.snapshot(), sort_keys=True)
    verdict = sim.observed_verdict("robot-a")
    sources = [
        ("fleet-sim/run.py", sha256_file(fleet_dir / "run.py")),
        ("fleet-sim/fleet_sim.py", sha256_file(fleet_dir / "fleet_sim.py")),
    ]
    kind_colors = {"PARTITION": "#8250df", "STOP": "#cf222e",
                   "STOP_DUPLICATE": "#bf8700", "GOSSIP": "#0969da",
                   "HEAL": "#1a7f37", "RESET": "#bf8700",
                   "OBSERVE": "#57606a", "LEADER": "#0969da"}
    row_h, width = 18, 980
    lines, y, _ = svg_open(
        "Fleet-sim scenario trace (SIMULATED, deterministic)", "SIMULATED",
        sources, commit, utc, width,
        extra_note=f"trace_sha256: {trace_sha}  observed_verdict(robot-a): {verdict}")
    top = y
    lines.append(_text(10, y, "step", size=9, fill="#57606a"))
    lines.append(_text(60, y, "event (verbatim trace line from fleet-sim/run.py output)", size=9, fill="#57606a"))
    y += 8
    for i, line in enumerate(trace):
        y += row_h
        kind = line.split(" ", 1)[0]
        color = kind_colors.get(kind, "#1f2328")
        lines.append(f'<rect x="10" y="{y-11:.1f}" width="980" height="16" '
                     f'fill="{"#f6f8fa" if i % 2 else "#ffffff"}"/>')
        lines.append(f'<circle cx="18" cy="{y-3:.1f}" r="4" fill="{color}"/>')
        lines.append(_text(34, y, f"{i}", size=10))
        lines.append(_text(60, y, line, size=10))
        lines.append(_text(900, y, kind, size=9, fill=color, anchor="end"))
    y += 24
    lines.append(_text(10, y, f"snapshot (sorted JSON): {snapshot}", size=8))
    y += 14
    lines.append(_text(10, y, "Simulation only: no production control path, no network, "
                              "no physical stop-time claim.", size=9, fill="#57606a"))
    return svg_close(lines, y + 12), trace_sha


# ------------------------------------------------------------- loadtest
def render_loadtest(repo_root, commit, utc):
    paths = [Path(repo_root) / f"loadtest/results/attempt{i}.json"
             for i in (1, 2, 3)]
    data = [json.loads(p.read_text()) for p in paths]
    sources = [(f"loadtest/results/attempt{i}.json", sha256_file(p))
               for i, p in enumerate(paths, 1)]
    # Scenario order is taken from the first file; all attempts must agree.
    scenarios = [r["scenario"] for r in data[0]["results"]]
    for d in data[1:]:
        if [r["scenario"] for r in d["results"]] != scenarios:
            raise ValueError("loadtest attempts disagree on scenario order")
    width, left, right = 1060, 210, 90
    plot_w = width - left - right
    all_vals = [r["stats"][k] for d in data for r in d["results"]
                for k in ("median_ms", "p95_ms", "p99_ms")]
    lo, hi = math.log10(min(all_vals) * 0.9), math.log10(max(all_vals) * 1.1)

    def X(v):
        return left + (math.log10(v) - lo) / (hi - lo) * plot_w

    lines, y, _ = svg_open(
        "Loadtest percentiles per scenario - all 3 attempts (ms, log scale)",
        "MEASURED-ON-HOST", sources, commit, utc, width,
        extra_note="Measured on host via real HTTP to the simulated app; NOT a "
                   "physical/real-time stop-time claim. Source claim_scope is in each JSON.")
    # Legend
    markers = [("median", "circle"), ("p95", "rect"), ("p99", "diamond")]
    lx = left
    for label, _s in markers:
        lines.append(_text(lx, y, f"marker shape: {label}", size=9, fill="#57606a"))
        lx += 150
    for a in range(3):
        lines.append(_text(lx, y, f"attempt{a+1} colour", size=9,
                           fill=["#cf222e", "#0969da", "#1a7f37"][a]))
        lx += 130
    y += 6
    for tick in (1, 2, 5, 10, 20, 50, 100, 200):
        x = X(tick)
        lines.append(f'<line x1="{x:.1f}" y1="{y}" x2="{x:.1f}" y2="{y + len(scenarios)*34}" stroke="#eaeef2"/>')
        lines.append(_text(x, y - 2, f"{tick}", size=8, fill="#57606a", anchor="middle"))
    attempt_colors = ["#cf222e", "#0969da", "#1a7f37"]
    for si, scen in enumerate(scenarios):
        cy = y + 18 + si * 34
        lines.append(_text(10, cy + 3, scen, size=10))
        for ai, d in enumerate(data):
            r = next(r for r in d["results"] if r["scenario"] == scen)
            st, c = r["stats"], attempt_colors[ai]
            yy = cy - 8 + ai * 8
            lines.append(f'<line x1="{X(st["median_ms"]):.1f}" y1="{yy:.1f}" '
                         f'x2="{X(st["p99_ms"]):.1f}" y2="{yy:.1f}" stroke="{c}" stroke-width="1.5"/>')
            lines.append(f'<circle cx="{X(st["median_ms"]):.1f}" cy="{yy:.1f}" r="3.5" fill="{c}"/>')
            lines.append(f'<rect x="{X(st["p95_ms"])-3:.1f}" y="{yy-3:.1f}" width="6" height="6" fill="{c}"/>')
            x99 = X(st["p99_ms"])
            lines.append(f'<path d="M {x99:.1f} {yy-4:.1f} L {x99+4:.1f} {yy:.1f} L {x99:.1f} {yy+4:.1f} L {x99-4:.1f} {yy:.1f} Z" fill="{c}"/>')
        # Numeric labels for attempt1 (others readable from spread of markers)
        r0 = data[0]["results"][si]["stats"]
        lines.append(_text(width - right + 6, cy + 3,
                           f"a1 med {fmt(r0['median_ms'])} p95 {fmt(r0['p95_ms'])} p99 {fmt(r0['p99_ms'])}",
                           size=8, fill="#57606a"))
    y = y + 18 + len(scenarios) * 34 + 10
    lines.append(_text(10, y, "All three attempts are plotted per scenario; the spread "
                              "between attempts is the point - no single run is selected.", size=9, fill="#57606a"))
    return svg_close(lines, y + 14)


# ----------------------------------------------------------- adversarial
def render_adversarial_file(path, rel, commit, utc):
    d = json.loads(Path(path).read_text())
    by_class = d.get("by_class", {})
    escapes = d.get("escapes", [])
    esc_by_class = Counter(e.get("class", "?") for e in escapes)
    classes = sorted(by_class)
    width, left = 1060, 260
    bar_max = max([by_class[c].get("violations", 0) for c in classes] + [1])
    lines, y, _ = svg_open(
        f"Adversarial defect classes and escapes - {Path(rel).name}",
        "SYNTHETIC", [(rel, sha256_file(path))], commit, utc, width,
        extra_note=f"total_results: {d.get('total_results', 'n/a')}  escapes listed: {len(escapes)}  "
                   f"s0_violations: {d.get('s0_violations', 'n/a')}  "
                   "(template corpus, same-author validator: weak evidence, see source repo evidence)")
    lines.append(_text(left, y, f"bar: invariant violations per class (max {bar_max})", size=9, fill="#57606a"))
    y += 6
    for c in classes:
        v = by_class[c]
        y += 20
        viol = v.get("violations", 0)
        w = (width - left - 330) * viol / bar_max if bar_max else 0
        lines.append(_text(10, y, c, size=10))
        lines.append(f'<rect x="{left}" y="{y-10:.1f}" width="{w:.1f}" height="12" '
                     f'fill="{"#cf222e" if viol else "#d0d7de"}"/>')
        lines.append(_text(left + w + 6, y,
                           f"viol={viol} escapes={esc_by_class.get(c, 0)} "
                           f"cases={v.get('cases')} accepted_in_error={v.get('accepted_in_error')} "
                           f"rejected={v.get('rejected')} worst={v.get('worst')}", size=9))
    y += 22
    lines.append(_text(10, y, "Escape counts are counted here from this file's escapes[] "
                              "list by class; violations/accepted_in_error are read from by_class.", size=9, fill="#57606a"))
    return svg_close(lines, y + 14)


# ------------------------------------------------------------------ QIP
_QIP_ROW = re.compile(r"^\|\s*(QIP-R[\d.]+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")

def parse_qip(path):
    rows, in_s11 = [], False
    for line in Path(path).read_text().splitlines():
        if line.startswith("## 11."):
            in_s11 = True
            continue
        if in_s11 and line.startswith("## "):
            break
        if in_s11:
            m = _QIP_ROW.match(line)
            if m:
                rows.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
    return rows


def render_qip(repo_root, commit, utc):
    rel = "docs/specs/intervention-profile/QIP-v0.1.md"
    path = Path(repo_root) / rel
    rows = parse_qip(path)
    if not rows:
        raise ValueError("no QIP section-11 rows parsed")
    gaps = [r for r in rows if "UNIMPLEMENTED" in r[2]]
    width = 1060
    lines, y, _ = svg_open(
        "QIP section-11 traceability grid (traced IDs are traces, not pass claims)",
        "NOT TESTED", [(rel, sha256_file(path))], commit, utc, width,
        extra_note=f"requirements: {len(rows)}  UNIMPLEMENTED gaps: {len(gaps)}  "
                   f"traced: {len(rows)-len(gaps)}")
    cols = [(10, "Requirement"), (140, "Lowest class"), (300, "W4-N4 test ID or UNIMPLEMENTED"), (880, "Status")]
    for x, label in cols:
        lines.append(_text(x, y, label, size=9, fill="#57606a", weight="bold"))
    y += 6
    for req, cls, trace in rows:
        y += 17
        is_gap = "UNIMPLEMENTED" in trace
        bg = "#ffebe9" if is_gap else "#f6f8fa"
        lines.append(f'<rect x="6" y="{y-11:.1f}" width="{width-12}" height="15" fill="{bg}"/>')
        lines.append(_text(10, y, req, size=9, weight="bold" if is_gap else "normal"))
        lines.append(_text(140, y, cls, size=9))
        lines.append(_text(300, y, trace[:95], size=8))
        lines.append(_text(880, y, "GAP - UNIMPLEMENTED (NOT TESTED)" if is_gap else "TRACED",
                           size=9, fill="#cf222e" if is_gap else "#1a7f37",
                           weight="bold" if is_gap else "normal"))
    y += 22
    lines.append(_text(10, y, f"All {len(gaps)} UNIMPLEMENTED requirements are marked GAP above; "
                              "no QIP conformance class is claimed.", size=9, fill="#57606a"))
    return svg_close(lines, y + 14), rows, gaps


# ----------------------------------------------------------------- main
def render_all(repo_root, out_dir, commit=None, utc=None):
    repo_root, out_dir = Path(repo_root), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if commit is None or utc is None:
        gc, gu = git_info(repo_root)
        commit = gc if commit is None else commit
        utc = gu if utc is None else utc
    outputs = {}
    fleet_svg, _ = render_fleet(repo_root, commit, utc)
    outputs["fleet-timeline.svg"] = fleet_svg
    outputs["loadtest-percentiles.svg"] = render_loadtest(repo_root, commit, utc)
    results_dir = repo_root / "research/adversarial/results"
    for p in sorted(results_dir.glob("*summary*.json")):
        rel = f"research/adversarial/results/{p.name}"
        stem = p.stem.replace("-summary", "").replace("summary", "summary")
        name = f"adversarial-{stem}.svg" if stem else "adversarial-summary.svg"
        outputs[name] = render_adversarial_file(p, rel, commit, utc)
    qip_svg, _, _ = render_qip(repo_root, commit, utc)
    outputs["qip-traceability.svg"] = qip_svg
    for name in sorted(outputs):
        (out_dir / name).write_bytes(outputs[name].encode("utf-8"))
    return outputs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out", default="viz/evidence")
    ap.add_argument("--commit", default=None)
    ap.add_argument("--utc", default=None)
    a = ap.parse_args(argv)
    outputs = render_all(a.repo_root, a.out, a.commit, a.utc)
    for name in sorted(outputs):
        data = outputs[name].encode()
        print(f"{name} sha256={sha256_bytes(data)} bytes={len(data)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
