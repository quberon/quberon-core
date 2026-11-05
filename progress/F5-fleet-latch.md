# Progress - F5-fleet-latch

Owner: F5 alone. Scope: fleet-sim/** and this file only. No production
control-path changes, no settlement code.
Base at start: 35ee2aef6f7a2fcf17e51de40678aee97ba0b350 (branch wave5/f5)
Read first: docs/specs/GRAPH-HARNESS.md (M3 item G), QIP-v0.1 R4/R5/R6/R7,
graph.md R-IMM-1..R-IMM-5.

## Verdict: PASS (attempt 1 of 3)

Design + deterministic simulation of multi-instance latch coherence:
partitions, duplicate STOP, reset authorisation, stale leader,
conflicting observed states. Preserved rule, structural in code:
FleetSim.local_stop takes no network/leader/authority argument and
consumes zero network calls; gossip/leader/authority only propagate the
latch and gate the separate reset.

## Raw evidence

fleet-sim only (system python3, stdlib-only code):
  python3 -m pytest fleet-sim/test_fleet_sim.py -q
  ..................                                                       [100%]
  18 passed in 0.03s

scripted scenario (run twice, identical digest):
  python3 fleet-sim/run.py
  PARTITION groups=[['n1', 'n2'], ['n3']]
  STOP LATCHED node=n1 event=e1 epoch=1 net=0
  STOP LATCHED node=n3 event=e2 epoch=1 net=0
  STOP_DUPLICATE node=n1 event=e1 outcome=LATCHED
  GOSSIP net_calls=1
  HEAL
  GOSSIP net_calls=4
  RESET RESET_APPLIED node=n2 event=r1 clears=1
  GOSSIP net_calls=7
  OBSERVE node=n1 target=robot-a value=STOPPED src=sensor-1
  OBSERVE node=n2 target=robot-a value=MOVING src=sensor-2
  snapshot={'n1': {'robot-a': {'latched': False, 'epoch': 1, 'cleared_epoch': 1, 'origin': 'e1'}}, 'n2': {'robot-a': {'latched': False, 'epoch': 1, 'cleared_epoch': 1, 'origin': 'e1'}}, 'n3': {'robot-a': {'latched': False, 'epoch': 1, 'cleared_epoch': 1, 'origin': 'e1'}}}
  observed_verdict=CONFLICTED
  trace_sha256=bc00d02757b140236eff8687b4934a3cb373aee72759281b1f87087d13e79eb0
  (second run: same trace_sha256)

Full suite (make setup built Rust core, then make test):
  .venv/bin/python -m pytest -q
  161 passed, 1 skipped, 2 warnings in 34.39s

Scope check before commit: git status shows only fleet-sim/** and
progress/F5-fleet-latch.md as new paths; no app/, integrations/,
crates/, conformance/, graph.md, checks.md, progress.md edits.

## Outputs

fleet-sim/{README.md,DESIGN.md,FAILURE-TABLE.md,fleet_sim.py,
test_fleet_sim.py,run.py}; progress/F5-fleet-latch.md (this file).

## Limits

Simulated replicas only: no real transport, persistence/restart,
Byzantine replicas, clock trust, election safety under split-brain, or
physical observation — all listed as NOT-COVERED in
fleet-sim/FAILURE-TABLE.md. Not QIP conformance, not physical-safety
evidence (QIP R11.2).
