# Fleet latch coherence — design (Wave5 F5, GRAPH-HARNESS M3 review item G)

Status: simulation design only. No production control-path change, no
settlement/anchoring code, no claim about any physical robot.
Base: 35ee2ae. Sources: docs/specs/GRAPH-HARNESS.md (M3, R-IMM rules in
graph.md), docs/specs/intervention-profile/QIP-v0.1.md (R4/R5/R6/R7).

## 1. The preserved rule (non-negotiable)

    A local STOP applies to the local latch immediately. It never waits
    for consensus, a leader, gossip, a network, a blockchain, or an
    authorising authority.

In fleet_sim.py this is structural, not aspirational: `FleetSim.local_stop`
takes no network/leader/authority argument and increments no network
counter (asserted in tests: total partition + no leader + net delta 0).
Everything fleet-like — gossip, leader terms, authority outcomes — exists
only to (a) propagate an already-applied latch and (b) gate the separate
RESET. If a future production design ever makes STOP wait for any of
those, it violates R-IMM-1/R-IMM-3 and QIP R7.2 regardless of test results
here.

## 2. Model

- Replicas: N instances, each holding per-target `LatchState`
  {latched, epoch, cleared_epoch, origin_event_id}, a seen-event table,
  an adapter-invocation counter, and a *separate* observed-state slot.
- Epoch: latch incarnation number. STOP on an unlatched replica bumps
  epoch and latches; STOP while latched is effect-free. An authorised
  reset clears only the exact epoch it was authorised against
  (compare-and-swap), leaving epoch unchanged; the next STOP bumps it.
  This single rule makes stale resets and stale STOPs decidable locally.
- Identity: events carry (event_id, content_hash). Seen-sets persist
  across resets — that is what makes delayed duplicates detectable.
- Merge (anti-entropy join): higher epoch wins; at equal epoch a reset
  that cleared that epoch supersedes a lagging latched copy (a genuinely
  newer STOP would have a higher epoch, so nothing newer is hidden);
  origins tie-break lexicographically. The join is commutative,
  idempotent and associative by construction and is tested as such.
  Gossip runs in sorted pairwise order inside partition groups only.
- Leadership: monotonic terms, fleet-scoped. A leader coordinates
  resets/gossip only. A stale-term leader's reset is rejected; a stale
  leader's local STOP is still a STOP (leadership is not on that path).
- Observation: STOPPED / MOVING / UNKNOWN per replica, never merged into
  the latch. Conflicting concrete observations yield the explicit
  verdict CONFLICTED — never "stopped" by fiat (QIP R6.1–R6.3).

## 3. Semantics per case

Partitions. A STOP in any partition (including a singleton minority)
latches locally at once. Peers diverge visibly (`target not in latch`)
until heal; on heal, gossip converges them. Divergence is a reported
state, not an error to hide.

Duplicate STOP. Same id + same content: original outcome returned,
adapter not re-invoked (adapter fires only on unlatched→latched
transition). Same id + different content: CONFLICT_REJECTED, latch
unchanged (QIP R4.1/R4.2). Distinct STOP while latched: LATCHED_ALREADY.

Reset authorisation. Reset is a distinct action (QIP R5.2). Authority
outcomes accepted / refused / unavailable are three different results;
refused and unavailable both fail closed (latch retained) but are
reported distinctly (R-IMM-2, QIP R7.1/R7.3). Reset never starts motion:
it only makes `motion_permitted` re-evaluable. Stale reset (clears_epoch
≠ current epoch after a newer STOP): STALE_RESET_REJECTED. Duplicate
reset: original outcome, idempotent.

Stale leader. Term must strictly increase. Stale leader cannot route a
reset (STALE_LEADER_REJECTED); see §1 for why it can still STOP.

Stale STOP. An unseen STOP issued before a reset (issued_at_epoch <
cleared_epoch) arriving after that reset: STALE_REJECTED, no re-latch
(QIP R4.3). A *seen* duplicate after reset returns its original outcome
instead — also no re-latch, by the seen-table check ordering.

Conflicting observed states. Latch, acknowledgement and observation
stay three different things. CONFLICTED observation does not clear a
latch, does not latch an unlatched replica, and is never summarised as
stopped. Missing observation is UNKNOWN, including right after a
successful local STOP (latched ≠ observed-stopped).

## 4. Determinism

Logical ordering only: sorted node ids, sorted targets, sorted event
ids, no wall clock, no randomness, no network. `scripted_scenario()`
run twice must produce identical traces and identical SHA-256 trace
digests; the test asserts both.

## 5. What this does NOT do

- No production code is touched; nothing under app/, integrations/,
  crates/, conformance/ changes. fleet-sim/ imports nothing from them.
- No settlement, anchoring, EURC, or blockchain code (R-IMM-3); none is
  needed for coherence and none may sit on a control path.
- No real network transport, persistence, restart, clock trust, or
  Byzantine behaviour is simulated — see FAILURE-TABLE.md NOT-COVERED
  rows. Passing these tests is not QIP conformance and not evidence
  about physical stopping (QIP R11.2).

## 6. Run

    .venv/bin/python -m pytest fleet-sim/test_fleet_sim.py -q
    .venv/bin/python fleet-sim/run.py
