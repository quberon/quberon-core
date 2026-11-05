# Isaac Sim-compatible simulation bridge

Status: **the versioned bridge contract, deterministic local transport, fail-closed adapter, and tests are implemented. Isaac Sim itself is not installed or run in this repository.**

Isaac Sim should run on a separately supported GPU host. The web application and Raspberry Pi remain free of Isaac SDK dependencies.

## Contract

`adapters/isaac_sim.py` defines `quberon.isaac-sim.v1` request/response dataclasses and an `IsaacBridgeTransport` protocol. A request binds:

- simulator, robot, and scene IDs;
- command ID and monotonic sequence;
- issued and expiry timestamps;
- an allow-listed command (`STOP` only in this increment).

An acknowledgement is accepted only when the response matches protocol, command, sequence, and scene; reports `applied=true`; and reports observed state `ISAAC_SIM_STOPPED`. Timeouts, exceptions, mismatches, stale messages, replays, wrong scenes, and unobserved results return `UNKNOWN`.

## Deterministic development transport

`DeterministicIsaacTransport` provides a dependency-free controller for tests and local development. It rejects wrong simulator/robot/scene identifiers, stale/future commands, sequence replay, and commands other than STOP. Exact command-ID retries return the recorded response.

```python
from adapters.isaac_sim import DeterministicIsaacTransport, IsaacSimBridgeAdapter

transport = DeterministicIsaacTransport(
    simulator_id="isaac-host-1",
    robot_id="quberon-demo-001",
    scene_id="warehouse-a",
)
adapter = IsaacSimBridgeAdapter(
    transport,
    simulator_id="isaac-host-1",
    robot_id="quberon-demo-001",
    scene_id="warehouse-a",
)
result = adapter.stop("command-id")
```

The bridge adapter intentionally refuses task and reset commands. It is not selected by the production app yet; `SimulatedRobotAdapter` remains the only enabled runtime adapter.

## Isaac host implementation requirements

A future Isaac extension/service should implement `IsaacBridgeTransport.exchange` over an authenticated channel and translate only the versioned JSON contract. It must keep controller updates running while latched, measure simulated motion, and respond only after STOP has been applied and zero-motion state observed. It must never evaluate code or accept arbitrary USD/ROS commands from the request.

This bridge is simulation-only. It is not a physical emergency-stop integration or manufacturer safety architecture.
