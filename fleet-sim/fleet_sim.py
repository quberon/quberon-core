"""Deterministic multi-instance latch-coherence simulation (Wave5 F5).

SIMULATION ONLY. No production control path, no network, no blockchain,
no settlement. Pure stdlib, logical time, sorted deterministic delivery.

Core invariant (graph.md R-IMM-1/R-IMM-3, QIP R5/R7):
    A local STOP applies to the local latch IMMEDIATELY. It never waits
    for consensus, a leader, gossip, a network, or an authority.
Leadership / gossip / authority exist only for (a) propagating the
already-applied latch and (b) the separate, permission-gated RESET.

Vocabulary kept distinct per QIP R6: latched (retained state) is not
acknowledged, and neither is observed state (STOPPED/MOVING/UNKNOWN).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

# ---------------------------------------------------------------- events

@dataclass(frozen=True)
class StopEvent:
    event_id: str
    target: str
    content: str = "STOP"          # payload whose hash defines identity content
    issued_at_epoch: int = 0       # latch epoch the issuer had observed

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(f"{self.target}|{self.content}".encode()).hexdigest()[:16]


@dataclass(frozen=True)
class ResetEvent:
    event_id: str
    target: str
    clears_epoch: int              # CAS: only clears exactly this latch epoch
    authority: str = "accepted"    # accepted | refused | unavailable (distinct, R7)


@dataclass(frozen=True)
class Observation:
    target: str
    value: str                     # STOPPED | MOVING | UNKNOWN
    source: str


# ---------------------------------------------------------------- state

@dataclass
class LatchState:
    latched: bool = False
    epoch: int = 0                 # current/last latch incarnation
    cleared_epoch: int = 0         # highest epoch cleared by authorised reset
    origin: str = ""               # event_id that created current epoch

    def key(self):
        return (self.epoch, self.cleared_epoch, self.latched, self.origin)

    def copy(self) -> "LatchState":
        return LatchState(self.latched, self.epoch, self.cleared_epoch, self.origin)


def merge_latch(a: LatchState, b: LatchState) -> LatchState:
    """Deterministic, commutative, idempotent anti-entropy join.

    Higher epoch wins. At equal epoch, a reset that cleared that epoch
    supersedes a lagging latched copy of the *same* epoch (a new STOP
    would have bumped the epoch, so this tie cannot hide a newer STOP).
    Origin is tie-broken lexicographically for byte-identical results.
    """
    if a.epoch != b.epoch:
        return (a if a.epoch > b.epoch else b).copy()
    # same epoch
    a_cleared = a.cleared_epoch >= a.epoch and not a.latched
    b_cleared = b.cleared_epoch >= b.epoch and not b.latched
    if a_cleared != b_cleared:
        return (a if a_cleared else b).copy()
    if a.latched != b.latched:  # defensive; latched dominates unexplained divergence
        return (a if a.latched else b).copy()
    winner = a if a.origin <= b.origin else b
    out = winner.copy()
    out.cleared_epoch = max(a.cleared_epoch, b.cleared_epoch)
    return out


@dataclass
class Node:
    node_id: str
    latch: dict = field(default_factory=dict)        # target -> LatchState
    seen: dict = field(default_factory=dict)         # event_id -> (content_hash, outcome)
    adapter_invocations: int = 0                     # transitions unlatched->latched only
    observed: dict = field(default_factory=dict)     # target -> value


# ---------------------------------------------------------------- fleet

class FleetSim:
    def __init__(self, node_ids):
        self.nodes = {n: Node(n) for n in sorted(node_ids)}
        self.groups = [frozenset(self.nodes)]        # one partition group = healed
        self.leader_id = None
        self.leader_term = 0
        self.network_calls = 0                       # gossip/leader traffic only
        self.trace: list[str] = []

    # -- topology ---------------------------------------------------------
    def partition(self, groups):
        self.groups = [frozenset(g) for g in groups]
        self._log(f"PARTITION groups={sorted(sorted(g) for g in self.groups)}")

    def heal(self):
        self.groups = [frozenset(self.nodes)]
        self._log("HEAL")

    def _reachable(self, a, b):
        return any(a in g and b in g for g in self.groups)

    def elect_leader(self, node_id, term):
        if term <= self.leader_term:
            self._log(f"LEADER_REJECTED_STALE node={node_id} term={term} current={self.leader_term}")
            return "STALE_TERM"
        self.leader_id, self.leader_term = node_id, term
        self._log(f"LEADER node={node_id} term={term}")
        return "LEADER"

    # -- STOP: local, unconditional, zero network -------------------------
    def local_stop(self, node_id, ev: StopEvent) -> str:
        """Apply STOP locally. Deliberately takes no network/leader/authority
        argument and performs no network call: consensus cannot gate STOP."""
        node = self.nodes[node_id]
        prior = node.seen.get(ev.event_id)
        if prior is not None:
            if prior[0] != ev.content_hash:
                self._log(f"STOP_CONFLICT node={node_id} event={ev.event_id}")
                return "CONFLICT_REJECTED"
            self._log(f"STOP_DUPLICATE node={node_id} event={ev.event_id} outcome={prior[1]}")
            return prior[1]  # QIP R4.1: original outcome, no re-invocation
        st = node.latch.setdefault(ev.target, LatchState())
        if ev.issued_at_epoch < st.cleared_epoch:
            outcome = "STALE_REJECTED"               # QIP R4.3: superseded by reset
            node.seen[ev.event_id] = (ev.content_hash, outcome)
            self._log(f"STOP_STALE node={node_id} event={ev.event_id} epoch={st.epoch}")
            return outcome
        if st.latched:
            outcome = "LATCHED_ALREADY"
        else:
            st.epoch += 1
            st.latched = True
            st.origin = ev.event_id
            node.adapter_invocations += 1
            outcome = "LATCHED"
        node.seen[ev.event_id] = (ev.content_hash, outcome)
        self._log(f"STOP {outcome} node={node_id} event={ev.event_id} epoch={st.epoch} net=0")
        return outcome

    # -- RESET: distinct, authorised, permission-gated (fail closed) -------
    def reset(self, node_id, ev: ResetEvent, via_leader=None, leader_term=None) -> str:
        node = self.nodes[node_id]
        prior = node.seen.get(ev.event_id)
        if prior is not None:
            return prior[1]
        if via_leader is not None and (via_leader != self.leader_id or (leader_term or 0) < self.leader_term):
            outcome = "STALE_LEADER_REJECTED"        # stale leader cannot authorise reset
        elif ev.authority == "unavailable":
            outcome = "RESET_UNAVAILABLE_FAIL_CLOSED"  # R-IMM-1/R7.3: distinct from refusal
        elif ev.authority != "accepted":
            outcome = "RESET_REFUSED_FAIL_CLOSED"
        else:
            st = node.latch.setdefault(ev.target, LatchState())
            if st.latched and ev.clears_epoch == st.epoch:
                st.latched = False
                st.cleared_epoch = st.epoch
                outcome = "RESET_APPLIED"            # clears latch only; permits no motion itself
            elif not st.latched and ev.clears_epoch <= st.cleared_epoch and ev.clears_epoch:
                outcome = "RESET_ALREADY_CLEARED"
            else:
                outcome = "STALE_RESET_REJECTED"     # a newer STOP superseded this reset
        digest = hashlib.sha256(f"reset|{ev.target}|{ev.clears_epoch}|{ev.authority}".encode()).hexdigest()[:16]
        node.seen[ev.event_id] = (digest, outcome)
        self._log(f"RESET {outcome} node={node_id} event={ev.event_id} clears={ev.clears_epoch}")
        return outcome

    # -- gossip: propagation only, never on the STOP path ------------------
    def gossip_round(self):
        """One sorted pairwise anti-entropy round inside partition groups."""
        for a_id in sorted(self.nodes):
            for b_id in sorted(self.nodes):
                if a_id >= b_id or not self._reachable(a_id, b_id):
                    continue
                self.network_calls += 1
                a, b = self.nodes[a_id], self.nodes[b_id]
                for target in sorted(set(a.latch) | set(b.latch)):
                    merged = merge_latch(a.latch.get(target, LatchState()),
                                         b.latch.get(target, LatchState()))
                    a.latch[target], b.latch[target] = merged.copy(), merged.copy()
                # seen-sets union (deterministic outcome preference: first sorted)
                for k in sorted(set(a.seen) | set(b.seen)):
                    v = a.seen.get(k) or b.seen.get(k)
                    a.seen[k] = b.seen[k] = v
        self._log(f"GOSSIP net_calls={self.network_calls}")

    # -- observation: separate from latch/ack (QIP R6) ---------------------
    def observe(self, node_id, obs: Observation):
        self.nodes[node_id].observed[obs.target] = obs.value
        self._log(f"OBSERVE node={node_id} target={obs.target} value={obs.value} src={obs.source}")

    def observed_verdict(self, target) -> str:
        vals = {n.observed.get(target, "UNKNOWN") for n in self.nodes.values()}
        concrete = vals - {"UNKNOWN"}
        if len(concrete) > 1:
            return "CONFLICTED"      # never resolved into "stopped" by fiat
        return concrete.pop() if concrete else "UNKNOWN"

    def motion_permitted(self, node_id, target) -> bool:
        """Local latch alone gates local motion; observation never unlatches."""
        st = self.nodes[node_id].latch.get(target)
        return not (st and st.latched)

    # -- trace --------------------------------------------------------------
    def _log(self, line):
        self.trace.append(line)

    def snapshot(self) -> dict:
        return {nid: {t: vars(s) for t, s in sorted(n.latch.items())}
                for nid, n in sorted(self.nodes.items())}

    def trace_digest(self) -> str:
        blob = "\n".join(self.trace) + "\n" + json.dumps(self.snapshot(), sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()


def scripted_scenario():
    """Fixed scenario used by the determinism test and run.py."""
    sim = FleetSim(["n1", "n2", "n3"])
    sim.partition([["n1", "n2"], ["n3"]])
    sim.local_stop("n1", StopEvent("e1", "robot-a"))
    sim.local_stop("n3", StopEvent("e2", "robot-a"))
    sim.local_stop("n1", StopEvent("e1", "robot-a"))
    sim.gossip_round()
    sim.heal()
    sim.gossip_round()
    sim.reset("n2", ResetEvent("r1", "robot-a", clears_epoch=1))
    sim.gossip_round()
    sim.observe("n1", Observation("robot-a", "STOPPED", "sensor-1"))
    sim.observe("n2", Observation("robot-a", "MOVING", "sensor-2"))
    return sim
