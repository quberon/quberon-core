"""Simulated robot adapter. This is the only enabled adapter.

It deliberately has no GPIO, serial, network-command or vendor API path.
"""
from dataclasses import dataclass


@dataclass
class AdapterResult:
    command_state: str
    observed_state: str
    detail: str


class SimulatedRobotAdapter:
    mode = "SIMULATION"

    def __init__(self, fail: bool = False):
        self.fail = fail

    def stop(self) -> AdapterResult:
        if self.fail:
            return AdapterResult("UNKNOWN", "UNKNOWN", "Simulated adapter unavailable; stop not confirmed")
        return AdapterResult("ACKNOWLEDGED", "SIMULATED_STOPPED", "Simulator recorded STOP request")

    def simulated_task(self, action: str) -> AdapterResult:
        if self.fail:
            return AdapterResult("UNKNOWN", "UNKNOWN", "Simulated adapter unavailable; task not confirmed")
        return AdapterResult("ACKNOWLEDGED", "SIMULATED_TASK_ACTIVE", f"Simulator accepted {action}")

    def reset_simulation(self) -> AdapterResult:
        if self.fail:
            return AdapterResult("UNKNOWN", "UNKNOWN", "Simulated adapter unavailable; reset not confirmed")
        return AdapterResult("ACKNOWLEDGED", "SIMULATED_IDLE", "Simulation latch cleared; no task started")
