# Isaac Sim integration — PLANNED (not implemented, Isaac Sim not run)

Status: **design only. Isaac Sim has not been installed or run for this project.**

Isaac Sim's official requirements target Windows/Linux GPU systems (supported ARM builds on NVIDIA DGX Spark); macOS/Apple Silicon and Raspberry Pi are not listed supported targets. Plan a separate supported simulator host; do not install Isaac Sim on the demo Mac or Pi.

## Planned architecture

```
phone button / experimental voice or gesture input
  -> authenticated intervention API on Pi
  -> deterministic persistent STOP service
  -> selected adapter
       current: SimulatedRobotAdapter
       future:  authenticated bridge to a separate Isaac Sim host
  -> acknowledgement + observed simulation state + audit event
```

## Bridge requirements (for later implementation)

- Messages identify simulator instance, robot, scene/session, command ID, expiry and sequence. Authenticate the bridge; bind commands to the selected simulated robot; reject stale/replayed/wrong-scene messages; never accept arbitrary executable code in a message.
- An acknowledgement must follow the receiving controller **applying** the command and **observing** the relevant simulated state. HTTP 200, a frozen viewer, or a paused timeline does not prove simulated dynamics stopped.
- Connection loss/timeout means `UNKNOWN` or inhibited task acceptance — never a "stopped" claim.
- Reset is a separate explicit authorized action, never automatic. Stopping a simulator is not a physical emergency-stop integration; a physical humanoid adapter needs manufacturer-specific safety architecture and supervised engineering. Do not invent Isaac SDK calls; pin the Isaac version first.

## Acceptance scenarios (later)

Normal command/ack, wrong robot, stale/replay, bridge disconnect, repeated STOP, reset authorization, scene reload, ongoing controller updates while latched, telemetry showing actual motion state. Until then the honest sentence is: "contract planned; Isaac Sim not run."
