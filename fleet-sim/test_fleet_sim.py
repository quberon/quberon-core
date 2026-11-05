"""Deterministic fleet-latch coherence tests (Wave5 F5). Stdlib + pytest only.
Run: .venv/bin/python -m pytest fleet-sim/test_fleet_sim.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fleet_sim import FleetSim, Observation, ResetEvent, StopEvent, merge_latch, LatchState, scripted_scenario

T = "robot-a"


def fleet(ids=("n1", "n2", "n3")):
    return FleetSim(list(ids))


# --- THE invariant: local STOP never waits ---------------------------------

def test_stop_applies_in_total_partition_with_no_leader_and_zero_network():
    sim = fleet()
    sim.partition([["n1"], ["n2"], ["n3"]])  # total partition, no leader elected
    before = sim.network_calls
    assert sim.local_stop("n2", StopEvent("e1", T)) == "LATCHED"
    assert sim.network_calls == before == 0          # STOP consumed no network
    assert sim.nodes["n2"].latch[T].latched is True
    assert sim.motion_permitted("n2", T) is False
    # peers honestly do not know yet; divergence is visible, not papered over
    assert T not in sim.nodes["n1"].latch


def test_stop_does_not_wait_for_authority_outcome():
    # No authority argument exists on the STOP path by design; an unavailable
    # authority can only affect reset (below), never the latch itself.
    sim = fleet(("n1",))
    assert sim.local_stop("n1", StopEvent("e1", T)) == "LATCHED"


# --- duplicates / conflicts / staleness (QIP R4) ----------------------------

def test_duplicate_stop_returns_original_and_never_reinvokes_adapter():
    sim = fleet(("n1",))
    assert sim.local_stop("n1", StopEvent("e1", T)) == "LATCHED"
    assert sim.local_stop("n1", StopEvent("e1", T)) == "LATCHED"
    assert sim.nodes["n1"].adapter_invocations == 1


def test_reused_id_with_different_content_is_conflict_not_second_stop():
    sim = fleet(("n1",))
    sim.local_stop("n1", StopEvent("e1", T, content="STOP"))
    assert sim.local_stop("n1", StopEvent("e1", T, content="STOP-OTHER-TARGET")) == "CONFLICT_REJECTED"
    assert sim.nodes["n1"].adapter_invocations == 1


def test_distinct_stop_while_latched_does_not_reinvoke_adapter():
    sim = fleet(("n1",))
    sim.local_stop("n1", StopEvent("e1", T))
    assert sim.local_stop("n1", StopEvent("e2", T)) == "LATCHED_ALREADY"
    assert sim.nodes["n1"].adapter_invocations == 1


def test_delayed_pre_reset_stop_arriving_after_reset_is_stale():
    sim = fleet(("n1",))
    sim.local_stop("n1", StopEvent("e1", T))
    assert sim.reset("n1", ResetEvent("r1", T, clears_epoch=1)) == "RESET_APPLIED"
    # unseen STOP issued at epoch 0, delivered only now
    assert sim.local_stop("n1", StopEvent("e-old", T, issued_at_epoch=0)) == "STALE_REJECTED"
    assert sim.motion_permitted("n1", T) is True


# --- reset authorisation (QIP R5.2/R7.3, R-IMM-1) ----------------------------

def test_reset_requires_accepted_authority_and_unavailable_differs_from_refusal():
    sim = fleet(("n1",))
    sim.local_stop("n1", StopEvent("e1", T))
    assert sim.reset("n1", ResetEvent("r1", T, 1, authority="unavailable")) == "RESET_UNAVAILABLE_FAIL_CLOSED"
    assert sim.nodes["n1"].latch[T].latched is True
    assert sim.reset("n1", ResetEvent("r2", T, 1, authority="refused")) == "RESET_REFUSED_FAIL_CLOSED"
    assert sim.nodes["n1"].latch[T].latched is True
    assert sim.reset("n1", ResetEvent("r3", T, 1, authority="accepted")) == "RESET_APPLIED"
    assert sim.motion_permitted("n1", T) is True  # reset permits consideration; it starts no motion


def test_stale_reset_cannot_clear_a_newer_stop():
    sim = fleet(("n1",))
    sim.local_stop("n1", StopEvent("e1", T))
    sim.reset("n1", ResetEvent("r1", T, clears_epoch=1))
    sim.local_stop("n1", StopEvent("e2", T, issued_at_epoch=1))  # epoch 2
    assert sim.nodes["n1"].latch[T].epoch == 2
    # replayed/new reset authorised only against epoch 1
    assert sim.reset("n1", ResetEvent("r2", T, clears_epoch=1)) == "STALE_RESET_REJECTED"
    assert sim.nodes["n1"].latch[T].latched is True


def test_duplicate_reset_is_idempotent():
    sim = fleet(("n1",))
    sim.local_stop("n1", StopEvent("e1", T))
    assert sim.reset("n1", ResetEvent("r1", T, 1)) == "RESET_APPLIED"
    assert sim.reset("n1", ResetEvent("r1", T, 1)) == "RESET_APPLIED"


# --- partitions & heal convergence -------------------------------------------

def test_partition_stop_converges_latched_on_heal():
    sim = fleet()
    sim.partition([["n1"], ["n2", "n3"]])
    sim.local_stop("n1", StopEvent("e1", T))
    sim.gossip_round()
    assert T not in sim.nodes["n3"].latch  # partition respected
    sim.heal(); sim.gossip_round()
    assert all(n.latch[T].latched for n in sim.nodes.values())
    assert len({n.latch[T].origin for n in sim.nodes.values()}) == 1


def test_concurrent_stops_in_two_partitions_coalesce_to_one_epoch():
    sim = fleet()
    sim.partition([["n1"], ["n3"]])
    sim.local_stop("n1", StopEvent("e1", T))
    sim.local_stop("n3", StopEvent("e2", T))
    sim.heal(); sim.gossip_round()
    states = [n.latch[T] for n in sim.nodes.values()]
    assert all(s.latched and s.epoch == 1 for s in states)
    assert len({s.origin for s in states}) == 1  # deterministic tie-break


def test_authorised_reset_propagates_and_concurrent_new_stop_wins():
    sim = fleet()
    sim.partition([["n1"], ["n2"]])
    sim.local_stop("n1", StopEvent("e1", T)); sim.local_stop("n2", StopEvent("e1", T))
    # n1 side resets epoch1; n2 side (not seeing it) issues a fresh STOP at epoch1 knowledge
    assert sim.reset("n1", ResetEvent("r1", T, clears_epoch=1)) == "RESET_APPLIED"
    assert sim.local_stop("n2", StopEvent("e2", T, issued_at_epoch=1)) == "LATCHED_ALREADY"
    sim.heal(); sim.gossip_round()
    # reset of epoch1 supersedes lagging latched epoch1 (new STOP would be epoch2)
    assert all(not n.latch[T].latched for n in sim.nodes.values())


def test_reset_then_new_stop_before_heal_new_stop_survives_merge():
    sim = fleet(("n1", "n2"))
    sim.local_stop("n1", StopEvent("e1", T)); sim.local_stop("n2", StopEvent("e1", T))
    sim.partition([["n1"], ["n2"]])
    sim.reset("n1", ResetEvent("r1", T, clears_epoch=1))
    sim.local_stop("n1", StopEvent("e2", T, issued_at_epoch=1))  # epoch 2 on n1
    sim.heal(); sim.gossip_round()
    assert all(n.latch[T].latched and n.latch[T].epoch == 2 for n in sim.nodes.values())


def test_merge_is_commutative_and_idempotent():
    a = LatchState(True, 2, 1, "e2"); b = LatchState(False, 2, 2, "e1")
    assert merge_latch(a, b).key() == merge_latch(b, a).key()
    assert merge_latch(a, a).key() == a.key()


# --- stale leader ---------------------------------------------------------------

def test_stale_leader_cannot_authorise_reset_but_can_still_stop():
    sim = fleet()
    assert sim.elect_leader("n1", term=1) == "LEADER"
    assert sim.elect_leader("n2", term=2) == "LEADER"
    assert sim.elect_leader("n1", term=1) == "STALE_TERM"  # old leader deposed
    sim.local_stop("n1", StopEvent("e1", T)); sim.local_stop("n2", StopEvent("e1", T))
    assert sim.reset("n2", ResetEvent("r1", T, 1), via_leader="n1", leader_term=1) == "STALE_LEADER_REJECTED"
    assert sim.nodes["n2"].latch[T].latched is True
    # leadership is irrelevant to STOP: deposed leader's node still latches instantly
    sim2 = fleet()
    sim2.elect_leader("n1", 1); sim2.elect_leader("n2", 2)
    assert sim2.local_stop("n1", StopEvent("e9", T)) == "LATCHED"


# --- conflicting observed states (QIP R6) ---------------------------------------

def test_conflicting_observations_are_conflicted_never_stopped_and_never_unlatch():
    sim = fleet()
    sim.local_stop("n1", StopEvent("e1", T))
    sim.observe("n1", Observation(T, "STOPPED", "sensor-1"))
    sim.observe("n2", Observation(T, "MOVING", "sensor-2"))
    assert sim.observed_verdict(T) == "CONFLICTED"
    assert sim.nodes["n1"].latch[T].latched is True       # observation does not clear latch
    assert sim.motion_permitted("n1", T) is False


def test_ack_like_latch_is_not_an_observation():
    sim = fleet(("n1",))
    sim.local_stop("n1", StopEvent("e1", T))
    assert sim.observed_verdict(T) == "UNKNOWN"  # latched != observed stopped (R6.2/R6.3)


# --- determinism ------------------------------------------------------------------

def test_scripted_scenario_is_deterministic_and_converged():
    a, b = scripted_scenario(), scripted_scenario()
    assert a.trace == b.trace
    assert a.trace_digest() == b.trace_digest()
    # after authorised reset + gossip, all replicas agree cleared, epoch 1
    assert all(not n.latch[T].latched and n.latch[T].epoch == 1 for n in a.nodes.values())
    assert a.observed_verdict(T) == "CONFLICTED"
