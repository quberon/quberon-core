"""CLI: run the F3 STOP-under-load harness and emit JSON + a markdown table.

Usage: .venv/bin/python -m loadtest.run [--samples 30] [--out results.json]
Local simulated evidence only; see loadtest/harness.py docstring.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time

from loadtest.harness import run_all


def fmt(stats):
    return (f"n={stats['n']} median={stats['median_ms']:.2f}ms "
            f"p95={stats['p95_ms']:.2f}ms p99={stats['p99_ms']:.2f}ms "
            f"max={stats['max_ms']:.2f}ms jitter={stats['jitter_ms']:.2f}ms "
            f"mean={stats['mean_ms']:.2f}ms min={stats['min_ms']:.2f}ms")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=30)
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results = run_all(samples=args.samples)
    payload = {
        "started_utc": started,
        "host": f"{platform.system()} {platform.release()} {platform.machine()}",
        "python": sys.version.split()[0],
        "method": ("real HTTP (uvicorn 127.0.0.1, fresh app+DB per scenario); "
                   "perf_counter_ns around POST /stop; background planner/status/"
                   "task/CPU load running during sampling; STOP sequential except "
                   "concurrent_stops; percentiles nearest-rank; jitter = mean "
                   "absolute successive difference"),
        "claim_scope": ("Mac/local SIMULATION ONLY (SimulatedRobotAdapter, fake "
                        "secure-core stubs where noted). Not Pi, not hardware, "
                        "not a real-time or physical stop-time claim."),
        "results": results,
    }
    text = json.dumps(payload, indent=2)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
    print(f"# F3 STOP under load -- {started} -- {payload['host']} -- python {payload['python']}")
    for r in results:
        print(f"{r['scenario']:24s} core={r['core']:14s} {fmt(r['stats'])} "
              f"outcomes={r['outcomes']} adapter_calls={r['adapter_stop_calls']} "
              f"load={r['load_counters']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
