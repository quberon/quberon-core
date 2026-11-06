import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RENDER = ROOT / "viz" / "evidence" / "render.py"


def load_render():
    spec = importlib.util.spec_from_file_location("viz_render", RENDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def viz():
    return load_render()


@pytest.fixture(scope="module")
def outputs(viz, tmp_path_factory):
    out = tmp_path_factory.mktemp("svg")
    # Fixed commit/utc: rendering must not depend on wall clock.
    return viz.render_all(ROOT, out, commit="c" * 40, utc="2000-01-01T00:00:00Z"), out


EXPECTED = {
    "fleet-timeline.svg",
    "loadtest-percentiles.svg",
    "adversarial-summary.svg",
    "adversarial-postmerge.svg",
    "adversarial-hand.svg",
    "qip-traceability.svg",
}


def test_all_figures_rendered(outputs):
    rendered, _ = outputs
    assert EXPECTED <= set(rendered), sorted(set(rendered))


def test_every_svg_embeds_provenance_and_band(outputs):
    rendered, _ = outputs
    for name, svg in sorted(rendered.items()):
        assert svg.startswith('<?xml version="1.0" encoding="UTF-8"?>'), name
        assert "source:" in svg and "sha256:" in svg, name
        assert "git_commit: " + "c" * 40 in svg, name
        assert "utc: 2000-01-01T00:00:00Z" in svg, name
        assert any(band in svg for band in
                   ("MEASURED-ON-HOST", "SIMULATED", "SYNTHETIC", "NOT TESTED")), name
    # Band assignment is deliberate, not decorative.
    assert "SIMULATED" in rendered["fleet-timeline.svg"]
    assert "MEASURED-ON-HOST" in rendered["loadtest-percentiles.svg"]
    assert "SYNTHETIC" in rendered["adversarial-summary.svg"]
    assert "NOT TESTED" in rendered["qip-traceability.svg"]


def test_embedded_source_sha_matches_committed_file(viz, outputs):
    rendered, _ = outputs
    cases = {
        "fleet-timeline.svg": ["fleet-sim/run.py", "fleet-sim/fleet_sim.py"],
        "loadtest-percentiles.svg": [f"loadtest/results/attempt{i}.json" for i in (1, 2, 3)],
        "adversarial-summary.svg": ["research/adversarial/results/summary.json"],
        "qip-traceability.svg": ["docs/specs/intervention-profile/QIP-v0.1.md"],
    }
    for name, relpaths in cases.items():
        for rel in relpaths:
            digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            assert f"source: {rel}  sha256: {digest}" in rendered[name], (name, rel)


def test_running_twice_is_byte_identical(viz, tmp_path):
    a = viz.render_all(ROOT, tmp_path / "a", commit="c" * 40, utc="2000-01-01T00:00:00Z")
    b = viz.render_all(ROOT, tmp_path / "b", commit="c" * 40, utc="2000-01-01T00:00:00Z")
    assert set(a) == set(b)
    for name in sorted(a):
        assert a[name] == b[name], name
        on_disk_a = (tmp_path / "a" / name).read_bytes()
        on_disk_b = (tmp_path / "b" / name).read_bytes()
        assert hashlib.sha256(on_disk_a).hexdigest() == hashlib.sha256(on_disk_b).hexdigest(), name


def test_default_git_provenance_is_also_deterministic(viz, tmp_path):
    # No explicit commit/utc: provenance comes from HEAD, not wall clock.
    a = viz.render_all(ROOT, tmp_path / "a")
    b = viz.render_all(ROOT, tmp_path / "b")
    for name in sorted(a):
        assert a[name] == b[name], name


def test_fleet_trace_and_digest_match_run_py(viz, outputs):
    rendered, _ = outputs
    svg = rendered["fleet-timeline.svg"]
    spec = importlib.util.spec_from_file_location("fleet_sim_check", ROOT / "fleet-sim" / "fleet_sim.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    sim = mod.scripted_scenario()
    assert f"trace_sha256: {sim.trace_digest()}" in svg
    for line in sim.trace:
        assert line in svg
    assert "observed_verdict(robot-a): CONFLICTED" in svg


def test_loadtest_shows_all_three_attempts_and_source_numbers(viz, outputs):
    rendered, _ = outputs
    svg = rendered["loadtest-percentiles.svg"]
    data = [json.loads((ROOT / f"loadtest/results/attempt{i}.json").read_text()) for i in (1, 2, 3)]
    scenarios = [r["scenario"] for r in data[0]["results"]]
    for scen in scenarios:
        assert scen in svg
    for attempt in ("attempt1", "attempt2", "attempt3"):
        assert attempt in svg  # per-scenario markers exist for each attempt colour
    # Attempt-1 median/p95/p99 numbers are printed verbatim in the figure.
    for r in data[0]["results"]:
        st = r["stats"]
        label = f"a1 med {st['median_ms']:.3f} p95 {st['p95_ms']:.3f} p99 {st['p99_ms']:.3f}"
        assert label in svg, label


def test_adversarial_classes_violations_and_escape_counts(viz, outputs):
    rendered, _ = outputs
    svg = rendered["adversarial-summary.svg"]
    d = json.loads((ROOT / "research/adversarial/results/summary.json").read_text())
    from collections import Counter
    esc = Counter(e["class"] for e in d["escapes"])
    for cls, v in d["by_class"].items():
        assert cls in svg
        assert f"viol={v['violations']} escapes={esc.get(cls, 0)}" in svg, cls
    assert "escapes listed: 300" in svg
    assert "viol=200" in svg and "viol=100" in svg  # the two non-zero classes stay visible


def test_adversarial_all_summary_files_rendered(viz):
    # Every *summary*.json in the committed results dir gets a figure.
    files = sorted((ROOT / "research/adversarial/results").glob("*summary*.json"))
    assert len(files) == 3
    for p in files:
        svg = viz.render_adversarial_file(p, f"research/adversarial/results/{p.name}",
                                          "c" * 40, "2000-01-01T00:00:00Z")
        assert p.name.replace(".json", "") in svg or "Adversarial" in svg


def test_qip_grid_marks_all_18_unimplemented_as_gaps(viz, outputs):
    rendered, _ = outputs
    svg = rendered["qip-traceability.svg"]
    rows = viz.parse_qip(ROOT / "docs/specs/intervention-profile/QIP-v0.1.md")
    gaps = [r for r in rows if "UNIMPLEMENTED" in r[2]]
    assert len(rows) == 34
    assert len(gaps) == 18, len(gaps)
    assert "UNIMPLEMENTED gaps: 18" in svg
    assert svg.count("GAP - UNIMPLEMENTED (NOT TESTED)") == 18
    for req, _cls, trace in rows:
        assert req in svg
        if "UNIMPLEMENTED" in trace:
            # The row itself carries the marker, not just a summary count.
            i = svg.index(req)
            assert "GAP - UNIMPLEMENTED" in svg[i:i + 2000], req


def test_figure_changes_when_evidence_changes(viz, tmp_path):
    # Copy the smallest source (QIP) into a shadow repo layout is heavy;
    # instead mutate a rendered input directly through the file renderer.
    src = ROOT / "research/adversarial/results/hand-summary.json"
    d = json.loads(src.read_text())
    d["by_class"]["benign-control"]["violations"] = 7
    fake = tmp_path / "hand-summary.json"
    fake.write_text(json.dumps(d, sort_keys=True))
    svg = viz.render_adversarial_file(fake, "research/adversarial/results/hand-summary.json",
                                      "c" * 40, "2000-01-01T00:00:00Z")
    assert "viol=7" in svg
    original_sha = hashlib.sha256(src.read_bytes()).hexdigest()
    assert original_sha not in svg  # provenance follows the file actually read


def test_no_invented_numbers_in_loadtest_labels(viz, outputs):
    rendered, _ = outputs
    svg = rendered["loadtest-percentiles.svg"]
    # Every printed a1 med/p95/p99 triple must exist in attempt1.json.
    d = json.loads((ROOT / "loadtest/results/attempt1.json").read_text())
    triples = {(f"{r['stats']['median_ms']:.3f}", f"{r['stats']['p95_ms']:.3f}",
                f"{r['stats']['p99_ms']:.3f}") for r in d["results"]}
    found = re.findall(r"a1 med ([\d.]+) p95 ([\d.]+) p99 ([\d.]+)", svg)
    assert len(found) == len(d["results"])
    assert set(found) == triples
