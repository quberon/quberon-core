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

    # --- Manufacturer-mapping declaration (QIP-R10.2) ---------------------
    # QIP-R10.2 is a MUST NOT: an implementation MUST NOT claim a mapping
    # to a manufacturer stop, status, or reset interface unless that
    # interface has been observed in manufacturer-provided material
    # recorded with its source.
    #
    # Neutral declaration shape (this suite's vocabulary, not a vendor's):
    #   {
    #     "mapping_claimed": bool,          # explicit; missing is invalid
    #     "mappings": [                     # [] iff mapping_claimed is False
    #       {"kind": "stop" | "status" | "reset",
    #        "manufacturer_interface": "<non-empty name/id>",
    #        "source": "<non-empty recorded source reference>"}
    #     ]
    #   }
    # Extra keys are allowed (e.g. a "basis" explanation).
    #
    # Default raises NotImplementedError and the matching capability is
    # False: silence is NOT a non-claim. An adapter that does not expose
    # an explicit declaration is NOT TESTED on R10.2, never passed.
    def manufacturer_mapping_declaration(self) -> Dict[str, Any]:
        raise NotImplementedError

    # Capability disclosure: adapters report what this run can exercise.
    # A False capability is a NOT TESTED gap in the report, never a pass.
    def capabilities(self) -> Dict[str, bool]:
        return {
            "persistence_failure_injectable": False,
            "secure_core_refusal_injectable": False,
            "manufacturer_mapping_declared": False,
        }


def validate_manufacturer_mapping_declaration(declaration) -> list:
    """Return a list of QIP-R10.2 declaration errors ([] means well-formed).

    This checks only the *shape of the claim*: an explicit non-claim, or
    claimed mappings each carrying a kind, a manufacturer interface and
    a recorded source reference. It cannot and does not verify that a
    cited source is genuinely manufacturer-provided, current, or
    applicable to a given firmware -- that provenance check is outside
    any runtime conformance suite and remains explicitly untestable
    here (see conformance/README.md NOT TESTED).
    """
    errors = []
    if not isinstance(declaration, dict):
        return ["declaration is not a dict"]
    if not isinstance(declaration.get("mapping_claimed"), bool):
        errors.append("mapping_claimed must be an explicit bool")
    mappings = declaration.get("mappings")
    if not isinstance(mappings, list):
        errors.append("mappings must be a list")
        return errors
    claimed = declaration.get("mapping_claimed")
    if claimed is False and mappings:
        errors.append("mapping_claimed is False but mappings is non-empty")
    if claimed is True and not mappings:
        errors.append("mapping_claimed is True but mappings is empty")
    for i, m in enumerate(mappings):
        if not isinstance(m, dict):
            errors.append(f"mappings[{i}] is not a dict")
            continue
        if m.get("kind") not in ("stop", "status", "reset"):
            errors.append(f"mappings[{i}].kind must be stop, status or reset")
        for field in ("manufacturer_interface", "source"):
            if not isinstance(m.get(field), str) or not m[field].strip():
                errors.append(f"mappings[{i}].{field} must be a non-empty string")
    return errors
