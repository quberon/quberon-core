# F3 STOP-under-load harness (loadtest/)

Local, simulated harness for QIP-R3 (QIP-v0.1.md Section 6):
R3.1/R3.2 were UNIMPLEMENTED ("no load/priority test in N4") and
TRACEABILITY.md R3 noted: "No end-to-end load, deadline, starvation,
network partition, or physical stop-time test."

Run:

    .venv/bin/python -m loadtest.run --samples 30 --out loadtest-results.json
    .venv/bin/python -m pytest loadtest/ -q

Method and claim scope are in harness.py's docstring and in
progress/F3-stop-load.md. In short: real HTTP against the simulated
app on 127.0.0.1, fresh DB per scenario, background planner/status/
task/CPU load, perf_counter_ns around each STOP, nearest-rank
p95/p99, jitter = mean absolute successive difference.

This is Mac/local simulation evidence only. It is not Pi evidence,
not hardware evidence, not a real-time guarantee, and not a physical
stop-time claim (QIP-R3.3). Secure-core "accepted"/"rejecting" runs
use stubs (no Rust subprocess, no signing claim); "unavailable" is
the real secure_core=None path (unsigned STOP, R-IMM-1).
