"""Generate the architecture TRUTH MAP (SVG) from committed evidence sources.

Sources (only):
  1. docs/specs/intervention-profile/QIP-v0.1.md section 11 traceability table
     - a row is TRACE_PRESENT_NO_CLASS_CLAIM iff its cell names an N4 test ID
       and does not start with UNIMPLEMENTED
     - a row is UNSUPPORTED_EXPLICIT iff its cell starts with UNIMPLEMENTED
  2. docs/assurance/CLAIM-TO-EVIDENCE.md status vocabulary
     - the statuses above must be defined there; generation fails otherwise

Status is NOT derived from intent, roadmap text, or running any test here.
A trace in QIP section 11 is, per CLAIM-TO-EVIDENCE.md, not a QIP class,
conformance, certification, or safety claim.

Component status:
  trace_present  every requirement in the component is traced
  partial        some traced, some UNIMPLEMENTED
  gap            no traced requirement -- not built or not tested

Regenerate (from repo root):
  python3 -m viz.truthmap.generate
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Component titles are the QIP outline topics (QIP-v0.1.md sections 4-10);
# only the *status* comes from the section 11 table, never from titles.
COMPONENTS = [
    ("R1", "Intervention request identity and target scope"),
    ("R2", "Authentication and authorisation boundary"),
    ("R3", "Stop priority and independence"),
    ("R4", "Idempotency, duplicates, staleness"),
    ("R5", "Latching and restart/reset separation"),
    ("R6", "Command result versus observed state"),
    ("R7", "Unavailability versus reachable refusal"),
    ("R8", "Evidence, timestamps, replay bounds, custody"),
    ("R9", "Human and machine intervention inputs"),
    ("R10", "Adapter capability and manufacturer-interface mapping"),
    ("R11", "Verification, lifecycle, and conformance evidence"),
]

ROW_RE = re.compile(
    r"^\|\s*(QIP-R(\d+)\.(\d+))\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$",
    re.MULTILINE,
)
TEST_ID_RE = re.compile(r"QIP-[A-Z]+-\d+")

STATUS_TRACE = "TRACE_PRESENT_NO_CLASS_CLAIM"
STATUS_UNSUPPORTED = "UNSUPPORTED_EXPLICIT"

# status -> (fill, stroke, label)
STYLE = {
    "trace_present": ("#dcfce7", "#15803d", "TRACE PRESENT (all requirements)"),
    "partial": ("#fef9c3", "#a16207", "PARTIAL (some requirements are gaps)"),
    "gap": ("#f1f5f9", "#64748b", "GAP"),
}


def parse_qip_table(qip_text: str) -> list[dict]:
    """Parse the section 11 table. Fail loudly if the table is not found."""
    if "## 11." not in qip_text:
        raise ValueError("QIP section 11 heading not found")
    section11 = qip_text.split("## 11.", 1)[1]
    rows = []
    for req, major, minor, lowest_class, cell in ROW_RE.findall(section11):
        cell = cell.strip()
        if cell.startswith("UNIMPLEMENTED"):
            status, test_ids = STATUS_UNSUPPORTED, []
        else:
            test_ids = TEST_ID_RE.findall(cell)
            if not test_ids:
                raise ValueError(f"{req}: trace cell names no test ID: {cell!r}")
            status = STATUS_TRACE
        rows.append(
            {
                "requirement": req,
                "component": f"R{major}",
                "lowest_class": lowest_class.strip(),
                "status": status,
                "test_ids": test_ids,
                "source_cell": cell,
            }
        )
    if not rows:
        raise ValueError("QIP section 11 table parsed to zero rows")
    return rows


def check_vocabulary(claim_text: str) -> None:
    for status in (STATUS_TRACE, STATUS_UNSUPPORTED):
        if status not in claim_text:
            raise ValueError(
                f"status {status} not defined in CLAIM-TO-EVIDENCE.md; refusing to invent vocabulary"
            )


def summarise(rows: list[dict]) -> list[dict]:
    components = []
    for cid, title in COMPONENTS:
        own = [r for r in rows if r["component"] == cid]
        traced = [r for r in own if r["status"] == STATUS_TRACE]
        if own and len(traced) == len(own):
            status = "trace_present"
        elif traced:
            status = "partial"
        else:
            status = "gap"
        components.append(
            {
                "id": cid,
                "title": title,
                "status": status,
                "traced": len(traced),
                "total": len(own),
                "requirements": own,
            }
        )
    return components


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_svg(components: list[dict]) -> str:
    width, margin = 1240, 30
    box_w, box_h, gap_x, gap_y, cols = 386, 168, 11, 14, 3
    header_h, legend_h = 118, 118
    rows_n = (len(components) + cols - 1) // cols
    height = header_h + rows_n * (box_h + gap_y) + legend_h + margin
    out = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Segoe UI, Helvetica, Arial, sans-serif">'
    )
    out.append(
        "<defs><pattern id=\"gapHatch\" width=\"8\" height=\"8\" patternTransform=\"rotate(45)\" "
        'patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#f1f5f9"/>'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="#cbd5e1" stroke-width="2"/></pattern></defs>'
    )
    out.append(f'<rect width="{width}" height="{height}" fill="#ffffff"/>')
    out.append(
        f'<text x="{margin}" y="38" font-size="25" font-weight="700" fill="#0f172a">'
        "Quberon Architecture — TRUTH MAP (generated)</text>"
    )
    out.append(
        f'<text x="{margin}" y="62" font-size="13" font-weight="700" fill="#b91c1c">'
        "SIMULATION ONLY · STOP AUTHORIZATION ONLY · NO PHYSICAL CONTROL · "
        "NOT A SAFETY-RATED E-STOP · NO CERTIFICATION CLAIM</text>"
    )
    traced_total = sum(c["traced"] for c in components)
    total = sum(c["total"] for c in components)
    out.append(
        f'<text x="{margin}" y="84" font-size="12.5" fill="#334155">'
        f"Source: QIP-v0.1.md section 11 traceability table ({traced_total}/{total} requirements traced to an N4 test ID, "
        f"{total - traced_total} UNIMPLEMENTED) + CLAIM-TO-EVIDENCE.md status vocabulary. "
        "Status is derived from those committed sources, not from intent and not from re-running tests here.</text>"
    )
    out.append(
        f'<text x="{margin}" y="102" font-size="12.5" fill="#334155">'
        "Hand-drawn system diagram retained separately: docs/assets/architecture.svg (not generated). "
        "This generated map covers QIP R1–R11 only.</text>"
    )

    for i, comp in enumerate(components):
        x = margin + (i % cols) * (box_w + gap_x)
        y = header_h + (i // cols) * (box_h + gap_y)
        fill, stroke, _label = STYLE[comp["status"]]
        shown_fill = 'url(#gapHatch)' if comp["status"] == "gap" else fill
        dash = ' stroke-dasharray="7 5"' if comp["status"] == "gap" else ""
        out.append(
            f'<g data-component="{comp["id"]}" data-status="{comp["status"]}">'
            f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="10" '
            f'fill="{shown_fill}" stroke="{stroke}" stroke-width="2"{dash}/>'
        )
        # Wrap long titles onto a second line instead of overflowing the box.
        title_words = comp["title"].split()
        title_lines, current = [], ""
        for word in title_words:
            if len(current) + len(word) + 1 > 46 and current:
                title_lines.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        if current:
            title_lines.append(current)
        for j, tline in enumerate(title_lines[:2]):
            out.append(
                f'<text x="{x + 14}" y="{y + 26 + j * 15}" font-size="13.5" font-weight="700" fill="#0f172a">'
                f'{"{} — ".format(comp["id"]) if j == 0 else ""}{_esc(tline)}</text>'
            )
        title_block = 15 * len(title_lines[:2])
        if comp["status"] == "gap":
            badge = "GAP — not built or not tested"
        elif comp["status"] == "partial":
            badge = f'PARTIAL — {comp["traced"]}/{comp["total"]} traced, rest are gaps'
        else:
            badge = f'TRACE PRESENT — {comp["traced"]}/{comp["total"]} traced (no class claim)'
        out.append(
            f'<text x="{x + 14}" y="{y + 46 + title_block - 15}" font-size="11.5" font-weight="700" fill="{stroke}">{badge}</text>'
        )
        ly = y + 66 + title_block - 15
        for req in comp["requirements"]:
            if req["status"] == STATUS_TRACE:
                marker, colour, detail = "●", "#15803d", ",".join(req["test_ids"])
            else:
                marker, colour, detail = "○ GAP", "#b91c1c", "UNIMPLEMENTED"
            out.append(
                f'<text x="{x + 14}" y="{ly}" font-size="11" fill="{colour}">'
                f'{marker} {req["requirement"]} ({_esc(req["lowest_class"])}) — {_esc(detail)}</text>'
            )
            ly += 15
        out.append("</g>")

    ly = header_h + rows_n * (box_h + gap_y) + 8
    out.append(
        f'<rect x="{margin}" y="{ly}" width="{width - 2 * margin}" height="96" rx="10" fill="#fef2f2" stroke="#fca5a5"/>'
    )
    legend = [
        "LEGEND — read plainly:",
        "Green TRACE PRESENT: QIP section 11 traces every requirement of this component to an N4 test ID (TRACE_PRESENT_NO_CLASS_CLAIM).",
        "Amber PARTIAL: some requirements are traced; the ○ GAP requirements are UNIMPLEMENTED (UNSUPPORTED_EXPLICIT).",
        "Hatched GAP: no requirement of this component has a passing traced test. A gap means not built or not tested.",
        "A trace is not a QIP class, conformance, certification, or physical-safety claim (CLAIM-TO-EVIDENCE.md; QIP R11.2). No QIP class is claimed in v0.1.",
    ]
    for j, line in enumerate(legend):
        weight = "700" if j == 0 else "400"
        out.append(
            f'<text x="{margin + 14}" y="{ly + 20 + j * 16}" font-size="12" font-weight="{weight}" fill="#991b1b">{_esc(line)}</text>'
        )
    out.append("</svg>")
    svg = "\n".join(out) + "\n"
    ET.fromstring(svg)  # refuse to emit malformed XML
    return svg


def build(repo_root: Path) -> tuple[str, dict]:
    qip_text = (repo_root / "docs/specs/intervention-profile/QIP-v0.1.md").read_text(encoding="utf-8")
    claim_text = (repo_root / "docs/assurance/CLAIM-TO-EVIDENCE.md").read_text(encoding="utf-8")
    check_vocabulary(claim_text)
    rows = parse_qip_table(qip_text)
    components = summarise(rows)
    known = {cid for cid, _ in COMPONENTS}
    unknown = sorted({r["component"] for r in rows} - known)
    if unknown:
        raise ValueError(f"QIP table has components with no title mapping: {unknown}")
    missing = [cid for cid, _ in COMPONENTS if not any(r["component"] == cid for r in rows)]
    if missing:
        raise ValueError(f"QIP table has no rows for components: {missing}")
    return render_svg(components), {"components": components, "requirements": rows}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, default=None, help="default: <repo-root>/docs/assets/architecture-truth-map.svg")
    parser.add_argument("--json-output", type=Path, default=None, help="optional machine-readable status dump")
    args = parser.parse_args(argv)
    svg, data = build(args.repo_root)
    output = args.output or (args.repo_root / "docs/assets/architecture-truth-map.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    if args.json_output:
        args.json_output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    counts = {}
    for comp in data["components"]:
        counts[comp["status"]] = counts.get(comp["status"], 0) + 1
    print(f"wrote {output} components={len(data['components'])} status_counts={counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
