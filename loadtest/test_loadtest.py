"""Determinism tests for the F3 harness (not timing-equality tests).

Timing values on a shared OS are never asserted equal across runs.
What is deterministic, and asserted here, is: the statistics function
on fixed input, scenario outcome classification, sample counts,
adapter invocation counts, and fail-direction behaviour (R-IMM-1/2).
"""
import tempfile

from loadtest.harness import Scenario, run_scenario, summarize


def test_summarize_known_input_exact_and_repeatable():
    data = [10.0, 20.0, 30.0, 40.0]
    # sorted same; median=(20+30)/2; nearest-rank p95/p99 -> max;
    # jitter = mean(|20-10|,|30-20|,|40-30|) = 10
    expected = {"n": 4, "min_ms": 10.0, "median_ms": 25.0, "mean_ms": 25.0,
                "p95_ms": 40.0, "p99_ms": 40.0, "max_ms": 40.0, "jitter_ms": 10.0}
    assert summarize(data) == expected
    assert summarize(data) == summarize(list(data))  # repeat call identical
    assert summarize([5.0]) == {"n": 1, "min_ms": 5.0, "median_ms": 5.0,
                                "mean_ms": 5.0, "p95_ms": 5.0, "p99_ms": 5.0,
                                "max_ms": 5.0, "jitter_ms": 0.0}


def test_summarize_percentile_nearest_rank():
    vals = [float(i) for i in range(1, 101)]  # 1..100
    s = summarize(vals)
    assert s["median_ms"] == 50.5 and s["p95_ms"] == 95.0
    assert s["p99_ms"] == 99.0 and s["max_ms"] == 100.0 and s["n"] == 100


def _run(scn):
    with tempfile.TemporaryDirectory() as td:
        return run_scenario(scn, td)


def test_small_run_outcomes_deterministic_across_two_fresh_runs():
    a = _run(Scenario("baseline_accepted_stub", samples=3))
    b = _run(Scenario("baseline_accepted_stub", samples=3))
    assert a["outcomes"] == b["outcomes"] == {"200/ACKNOWLEDGED/accepted": 3}
    assert a["stats"]["n"] == b["stats"]["n"] == 3
    assert a["adapter_stop_calls"] == b["adapter_stop_calls"] == 3
    # timings themselves are NOT claimed deterministic
    assert set(a["stats"]) == {"n", "min_ms", "median_ms", "mean_ms",
                               "p95_ms", "p99_ms", "max_ms", "jitter_ms"}


def test_rejecting_core_never_calls_adapter():
    r = _run(Scenario("core_rejecting", core="rejecting", samples=3))
    assert r["outcomes"] == {"503/UNKNOWN/rejected": 3}
    assert r["adapter_stop_calls"] == 0
    assert r["stats"]["n"] == 3


def test_unavailable_core_stop_proceeds_unsigned():
    r = _run(Scenario("core_unavailable", core="unavailable", samples=3))
    assert r["outcomes"] == {"200/ACKNOWLEDGED/unavailable": 3}
    assert r["adapter_stop_calls"] == 3


def test_slow_adapter_outcome_and_count_not_timing():
    r = _run(Scenario("slow_adapter", adapter_delay_s=0.02, samples=3))
    assert r["outcomes"] == {"200/ACKNOWLEDGED/accepted": 3}
    assert r["adapter_stop_calls"] == 3
    # sanity only (delay is injected, so median cannot be near zero);
    # this is a harness-wiring check, not a latency claim.
    assert r["stats"]["median_ms"] >= 10.0
