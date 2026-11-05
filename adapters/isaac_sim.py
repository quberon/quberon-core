"""Isaac Sim-compatible bridge contract with a deterministic local transport.

No Isaac SDK is imported. A supported Isaac Sim host can implement the same
request/response JSON contract. This adapter remains simulation-only and never
controls physical hardware.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Protocol

from adapters.robot_sim import AdapterResult


@dataclass(frozen=True)
class IsaacBridgeRequest:
    protocol_version: str
    simulator_id: str
    robot_id: str
    scene_id: str
    command_id: str
    sequence: int
    command: str
    issued_at: str
    expires_at: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class IsaacBridgeResponse:
    protocol_version: str
    command_id: str
    sequence: int
    applied: bool
    observed_state: str
    scene_id: str
    detail: str


class IsaacBridgeTransport(Protocol):
    def exchange(self, request: IsaacBridgeRequest) -> IsaacBridgeResponse: ...


class DeterministicIsaacTransport:
    """In-memory bridge controller for tests and development without Isaac."""

    def __init__(self, simulator_id: str, robot_id: str, scene_id: str):
        self.simulator_id = simulator_id
        self.robot_id = robot_id
        self.scene_id = scene_id
        self.last_sequence = 0
        self.responses: Dict[str, IsaacBridgeResponse] = {}
        self.observed_state = "ISAAC_SIM_STOPPED"

    def exchange(self, request: IsaacBridgeRequest) -> IsaacBridgeResponse:
        if request.command_id in self.responses:
            return self.responses[request.command_id]
        now = datetime.now(timezone.utc)
        try:
            issued = datetime.fromisoformat(request.issued_at.replace("Z", "+00:00"))
            expires = datetime.fromisoformat(request.expires_at.replace("Z", "+00:00"))
        except ValueError:
            return self._reject(request, "invalid timestamp")
        if request.protocol_version != "quberon.isaac-sim.v1":
            return self._reject(request, "unsupported protocol")
        if request.simulator_id != self.simulator_id or request.robot_id != self.robot_id:
            return self._reject(request, "simulator or robot mismatch")
        if request.scene_id != self.scene_id:
            return self._reject(request, "scene mismatch")
        if issued > now or expires <= now:
            return self._reject(request, "stale or future command")
        if request.sequence <= self.last_sequence:
            return self._reject(request, "sequence replay")
        if request.command != "STOP":
            return self._reject(request, "command not allow-listed")
        self.last_sequence = request.sequence
        self.observed_state = "ISAAC_SIM_STOPPED"
        response = IsaacBridgeResponse(request.protocol_version, request.command_id, request.sequence, True, self.observed_state, self.scene_id, "STOP applied and simulated zero-motion state observed")
        self.responses[request.command_id] = response
        return response

    def _reject(self, request: IsaacBridgeRequest, detail: str) -> IsaacBridgeResponse:
        response = IsaacBridgeResponse(request.protocol_version, request.command_id, request.sequence, False, "UNKNOWN", self.scene_id, detail)
        self.responses[request.command_id] = response
        return response


class IsaacSimBridgeAdapter:
    mode = "ISAAC_SIM_BRIDGE"

    def __init__(self, transport: IsaacBridgeTransport, simulator_id: str, robot_id: str, scene_id: str):
        self.transport = transport
        self.simulator_id = simulator_id
        self.robot_id = robot_id
        self.scene_id = scene_id
        self.sequence = 0

    def stop(self, command_id: Optional[str] = None) -> AdapterResult:
        from datetime import timedelta
        import secrets

        self.sequence += 1
        now = datetime.now(timezone.utc)
        request = IsaacBridgeRequest(
            protocol_version="quberon.isaac-sim.v1",
            simulator_id=self.simulator_id,
            robot_id=self.robot_id,
            scene_id=self.scene_id,
            command_id=command_id or secrets.token_urlsafe(16),
            sequence=self.sequence,
            command="STOP",
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=5)).isoformat(),
        )
        try:
            response = self.transport.exchange(request)
        except Exception as exc:
            return AdapterResult("UNKNOWN", "UNKNOWN", f"Isaac bridge unavailable: {type(exc).__name__}")
        if (
            response.protocol_version != request.protocol_version
            or response.command_id != request.command_id
            or response.sequence != request.sequence
            or response.scene_id != request.scene_id
            or not response.applied
            or response.observed_state != "ISAAC_SIM_STOPPED"
        ):
            return AdapterResult("UNKNOWN", "UNKNOWN", f"Isaac bridge STOP not confirmed: {response.detail}")
        return AdapterResult("ACKNOWLEDGED", response.observed_state, response.detail)

    def simulated_task(self, action: str) -> AdapterResult:
        return AdapterResult("UNKNOWN", "UNKNOWN", "Isaac bridge task commands are intentionally not enabled")

    def reset_simulation(self) -> AdapterResult:
        return AdapterResult("UNKNOWN", "UNKNOWN", "Isaac bridge reset is intentionally not enabled")
