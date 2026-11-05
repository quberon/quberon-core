# Fleet latch coherence simulation (Wave5 F5)

Design + deterministic simulation of multi-instance latch coherence
for GRAPH-HARNESS M3 review item G. Simulation only; no production
control-path, settlement, or blockchain code.

Preserved rule: a local STOP never waits for consensus, a leader,
gossip, a network, or an authority. See DESIGN.md §1.

    python3 fleet-sim/run.py
    .venv/bin/python -m pytest fleet-sim/test_fleet_sim.py -q

Files: DESIGN.md (model + semantics), fleet_sim.py (kernel),
test_fleet_sim.py (deterministic tests), run.py (scripted trace),
FAILURE-TABLE.md (scenario outcomes + explicit NOT-COVERED gaps).
