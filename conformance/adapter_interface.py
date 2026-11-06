"""Implementation-neutral adapter interface for QIP conformance (Wave 4 N4).

An adapter under test is any system that can be driven through the small
neutral surface below. Field names here are THIS suite's vocabulary, not a
vendor's: an adapter implementation translates its own API (HTTP, gRPC,
vendor SDK, simulator, ...) into these neutral operations and results.

Neutral result vocabulary (adapters MUST map into this, not invent synonyms):
  status_code        int, HTTP-like outcome class of the operation
  command_state      "ACKNOWLEDGED" | "UNKNOWN" | "REJECTED" | other adapter
                     string preserved verbatim if it cannot be mapped
  observed_state     adapter-reported observed state, kept SEPARATE from
                     command_state (QIP-STATE)
  stop_latched       bool, the intervention latch, kept SEPARATE from
                     observed_state (QIP-LATCH)
  command_id         stable id of the recorded command/event, if any
  duplicate          bool, True iff this was an exact idempotent replay
  secure_core_status "accepted" | "unavailable" | "rejected" | None

Roles are neutral: "anonymous" (no credentials), "viewer" (read-only),
"operator" (may request intervention), "admin" (may reset the latch).
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class NeutralResult:
    status_code: int
    body: Dict[str, Any] = field(default_factory=dict)

    @property
    def command_state(self) -> Optional[str]:
        return self.body.get("command_state")

    @property
    def observed_state(self) -> Optional[str]:
        return self.body.get("observed_state")

    @property
    def stop_latched(self) -> Optional[bool]:
        v = self.body.get("stop_latched")
        if v is None:
            v = self.body.get("current_stop_latched")
        return v

    @property
    def command_id(self) -> Optional[str]:
        return self.body.get("command_id") or self.body.get("event_id")

    @property
    def duplicate(self) -> bool:
        return bool(self.body.get("duplicate"))

    @property
    def secure_core_status(self) -> Optional[str]:
        sc = self.body.get("secure_core")
        return sc.get("status") if isinstance(sc, dict) else None


QIP_CLASSES = ("OBSERVE", "INTERVENE", "AUTHORIZE", "EVIDENCE")


def validate_class_claim(claim):
    """Shape-check a QIP-R11.1 class-claim artifact; return error strings.

    A claim satisfying this validator has only the required *form*: it
    names a class, a profile version, exact test identifiers, and a
    non-empty raw-output text mentioning each identifier. This does NOT
    verify that the raw output is genuine or unedited, that the named
    tests passed on the claimed version, or that the implementation
    satisfies every MUST of the named (cumulative) class. A summary
    paraphrase cannot be reliably distinguished from raw output by
    shape alone, so a passing shape check must never be rounded up to
    a trace for QIP-R11.1.
    """
    if not isinstance(claim, dict):
        return ["class claim is not an explicit mapping"]
    errors = []
    if claim.get("claimed_class") not in QIP_CLASSES:
        errors.append("claimed_class does not name a QIP class")
    version = claim.get("profile_version")
    if not isinstance(version, str) or not version.strip():
        errors.append("profile_version is missing or empty")
    test_ids = claim.get("test_ids")
    if (not isinstance(test_ids, list) or not test_ids
            or any(not isinstance(t, str) or not t.strip() for t in test_ids)
            or len(set(test_ids)) != len(test_ids)):
        errors.append("test_ids is not a non-empty list of distinct identifiers")
        test_ids = []
    raw = claim.get("raw_output")
    if not isinstance(raw, str) or not raw.strip():
        errors.append("raw_output is missing or empty (a summary does not satisfy QIP-R11.1)")
    else:
        for tid in test_ids:
            if tid not in raw:
                errors.append(f"raw_output does not mention {tid}")
    return errors


class AdapterUnderTest:
    """Neutral surface every adapter implementation must provide.

    Subclasses translate each method to the system under test. Methods must
    not hide failures: transport/adapter errors surface as a NeutralResult
    with command_state "UNKNOWN" or a non-2xx status_code, never as success.
    """

    robot_id: str = ""

    def status(self, role: str) -> NeutralResult:
        raise NotImplementedError

    def status_for_robot(self, role: str, robot_id: str) -> NeutralResult:
        raise NotImplementedError

    def stop(self, role: str, idempotency_key: str, note: str = "conformance stop",
             csrf: bool = True) -> NeutralResult:
        raise NotImplementedError

    def stop_for_robot(self, role: str, robot_id: str, idempotency_key: str) -> NeutralResult:
        raise NotImplementedError

    def reset_latch(self, role: str, confirm: str = "RESET_SIMULATION") -> NeutralResult:
        raise NotImplementedError

    def submit_task(self, role: str, action: str) -> NeutralResult:
        raise NotImplementedError

    def submit_proposal(self, role: str, text: str) -> NeutralResult:
        raise NotImplementedError

    def intervene(self, role: str, kind: str, event_id: str,
                  evidence_text: str = "", timestamp: str = "") -> NeutralResult:
        raise NotImplementedError

    def events(self, role: str) -> NeutralResult:
        raise NotImplementedError

    # --- Class-claim artifact (QIP-R11.1) --------------------------------
    # A class claim is a documentary artifact, not adapter runtime
    # behaviour. An adapter/system that exposes one returns it here,
    # sourced from the claimant (claim document/record), NOT hardcoded
    # in the adapter: an adapter-invented claim or non-claim is not
    # evidence. Expected shape when a claim exists:
    #   {"claimed_class": one of QIP_CLASSES, "profile_version": str,
    #    "test_ids": [exact test identifiers], "raw_output": str}
    # Returning None means no claim artifact is exposed through this
    # surface; the suite then reports QIP-R11.1 NOT TESTED, never a pass.
    def class_claim(self):
        return None

    # --- Implementation-neutral fault injection (QIP-DEG-03) -------------
    # These are the injection points the original interface lacked. They
    # name STATES, not mechanisms: how an adapter puts its system into the
    # state is its own business (fault-injection hook, stub authority,
    # broken backend, ...). The suite only observes the neutral results
    # afterwards, exactly as for non-injected operations.
    #
    # Contract: call before the operation under test, on a fresh adapter.
    # After injection the state must persist for the rest of that adapter's
    # life (no auto-recovery inside the test). An adapter that cannot
    # inject a state MUST leave the corresponding capability False and
    # MUST raise NotImplementedError here; the suite then reports that
    # state NOT TESTED (skip), never a pass.
    def inject_persistence_failure(self) -> None:
        """Put the system in its persistence-degraded state.

        Expected neutral semantics afterwards are the adapter's own
        degraded contract; for quberon-core: persistence is reported
        not-ok, the latch is retained, and stop/task/reset are refused
        with a non-2xx (503) result rather than claimed durable.
        """
        raise NotImplementedError

    def inject_secure_core_refusal(self) -> None:
        """Make the authorising authority REACHABLE but REFUSING.

        This is distinct from unavailability (QIP-DEG-01/R-IMM-2): the
        authority is contacted and returns a negative decision. Expected
        neutral semantics afterwards (QIP-R7.4): the intervention is not
        invoked, the latch is retained, command/observed state are
        UNKNOWN, and secure_core_status is "rejected" -- never
        "unavailable" and never "accepted".
        """
        raise NotImplementedError

    # Capability disclosure: adapters report what this run can exercise.
    # A False capability is a NOT TESTED gap in the report, never a pass.
    def capabilities(self) -> Dict[str, bool]:
        return {
            "persistence_failure_injectable": False,
            "secure_core_refusal_injectable": False,
            "class_claim_available": False,
        }
