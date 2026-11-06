"""Tests for the truth-map generator.

The generator's only evidence sources are QIP-v0.1.md section 11 and
CLAIM-TO-EVIDENCE.md. These tests pin the counts observed in those
committed sources at this commit, and fail if a gap is ever rendered
as anything other than a gap.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from viz.truthmap.generate import (
    COMPONENTS,
    STATUS_TRACE,
    STATUS_UNSUPPORTED,
    build,
    check_vocabulary,
    parse_qip_table,
    render_svg,
    summarise,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATED = REPO_ROOT / "docs/assets/architecture-truth-map.svg"
HAND_DRAWN = REPO_ROOT / "docs/assets/architecture.svg"


@pytest.fixture(scope="module")
def built():
    return build(REPO_ROOT)


def test_section11_table_parses_to_34_rows(built):
    _svg, data = built
    assert len(data["requirements"]) == 34
    traced = [r for r in data["requirements"] if r["status"] == STATUS_TRACE]
    unsupported = [r for r in data["requirements"] if r["status"] == STATUS_UNSUPPORTED]
    assert len(traced) == 16
    assert len(unsupported) == 18


def test_every_traced_row_names_a_real_test_id(built):
    _svg, data = built
    for row in data["requirements"]:
        if row["status"] == STATUS_TRACE:
            assert row["test_ids"], row
            assert not row["source_cell"].startswith("UNIMPLEMENTED")


def test_gap_components_have_no_traced_requirement(built):
    _svg, data = built
    by_id = {c["id"]: c for c in data["components"]}
    # Observed in QIP section 11 at this commit: R3, R10, R11 have zero traces.
    for cid in ("R3", "R10", "R11"):
        assert by_id[cid]["status"] == "gap", by_id[cid]
        assert by_id[cid]["traced"] == 0
    for cid in ("R4", "R6"):
        assert by_id[cid]["status"] == "trace_present", by_id[cid]
    for cid in ("R1", "R2", "R5", "R7", "R8", "R9"):
        assert by_id[cid]["status"] == "partial", by_id[cid]


def test_svg_is_well_formed_and_covers_all_components_and_requirements(built):
    svg, data = built
    ET.fromstring(svg)
    for cid, _title in COMPONENTS:
        assert f'data-component="{cid}"' in svg
    for row in data["requirements"]:
        assert row["requirement"] in svg


def test_gap_components_render_as_gaps_in_svg(built):
    svg, _data = built
    for cid in ("R3", "R10", "R11"):
        assert f'data-component="{cid}" data-status="gap"' in svg
    assert svg.count('data-status="gap"') == 3
    assert "GAP — not built or not tested" in svg


def test_legend_states_gap_meaning_plainly(built):
    svg, _data = built
    assert "A gap means not built or not tested." in svg
    assert "not a QIP class, conformance, certification, or physical-safety claim" in svg


def test_no_certification_or_class_claim_in_svg(built):
    svg, _data = built
    assert "NO CERTIFICATION CLAIM" in svg
    # The map must not claim any QIP class is satisfied.
    assert not re.search(r"Class (OBSERVE|INTERVENE|AUTHORIZE|EVIDENCE) (is )?(claimed|satisfied|achieved)", svg)


def test_unimplemented_requirement_fails_closed_to_gap():
    synthetic = (
        "## 11. Traceability\n\n"
        "| Requirement | Lowest class | W4-N4 test ID or UNIMPLEMENTED |\n"
        "|---|---|---|\n"
        "| QIP-R3.1 | INTERVENE | UNIMPLEMENTED (no test) |\n"
    )
    rows = parse_qip_table(synthetic)
    assert rows[0]["status"] == STATUS_UNSUPPORTED
    comps = {c["id"]: c for c in summarise(rows)}
    assert comps["R3"]["status"] == "gap"
    svg = render_svg([comps["R3"]])
    assert 'data-status="gap"' in svg


def test_missing_section11_is_an_error_not_a_default_pass():
    with pytest.raises(ValueError):
        parse_qip_table("# no traceability table here")


def test_unknown_status_vocabulary_is_refused():
    with pytest.raises(ValueError):
        check_vocabulary("this file defines nothing")


def test_generated_file_on_disk_matches_generator(built):
    svg, _data = built
    assert GENERATED.exists(), "run: python3 -m viz.truthmap.generate"
    assert GENERATED.read_text(encoding="utf-8") == svg


def test_hand_drawn_diagram_is_kept_and_distinguishable():
    # Supersede condition not met: the generated map covers QIP R1-R11 only,
    # while the hand-drawn diagram shows system layout (Phone UI, Pi, e-ink)
    # that QIP section 11 / CLAIM-TO-EVIDENCE cannot colour. Both are kept.
    assert HAND_DRAWN.exists()
    assert GENERATED.exists()
    assert HAND_DRAWN.read_bytes() != GENERATED.read_bytes()
    hand = HAND_DRAWN.read_text(encoding="utf-8")
    for label in ("Phone UI", "Raspberry Pi", "E-ink"):
        assert label in hand
    generated = GENERATED.read_text(encoding="utf-8")
    assert "(generated)" in generated
    assert "architecture.svg (not generated)" in generated
