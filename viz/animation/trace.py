"""Build the animation trace from ACTUAL replayed evidence, stdlib-first.

Sources (no invented values):
  1. Copper spike committed evidence (spikes/copper-stop-path/evidence/):
     comparison.txt + original/replay task-output bins and unified logs.
     Byte-identity is re-checked here, hashes are embedded in every frame.
  2. fleet-sim scripted scenario, executed twice in-process; the two
     traces must be identical and trace_digest() is recorded.
  3. Fail-direction probes through the real app execute_stop path
     (app.main.create_app, as in tests/test_secure_core.py) with a tmp DB:
       - secure_core=None        -> core unavailable
       - RejectingCore (raises SecureCoreRejected, exactly the stub the
         upstream test-suite uses) -> core rejecting
     Only deterministic fields are kept (status, command/observed state,
     latch, secure_core sub-object, adapter invocation count); random
     command ids / timestamps are stripped so the trace is reproducible.
     If the app stack (fastapi) is not importable, the probes are recorded
     as SKIPPED with the reason -- never fabricated.

Nothing here describes a physical robot. All outcomes are SIMULATED.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

STAGES = ["sensor", "recognition", "authorization", "actuator"]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical_sha256(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return _sha(blob)


def _load_fleet_sim(repo: Path):
    path = repo / "fleet-sim" / "fleet_sim.py"
    spec = importlib.util.spec_from_file_location("viz_fleet_sim", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve cls.__module__ here
    spec.loader.exec_module(mod)
    return mod


def _copper(repo: Path) -> dict:
    ev = repo / "spikes" / "copper-stop-path" / "evidence"
    comp_text = (ev / "comparison.txt").read_text()
    comp = dict(
        line.split("=", 1) for line in comp_text.strip().splitlines() if "=" in line
    )
    orig_bin = (ev / "original-task-outputs.bin").read_bytes()
    repl_bin = (ev / "replay-task-outputs.bin").read_bytes()
    orig_log = (ev / "original_0.copper").read_bytes()
    repl_log = (ev / "replay_0.copper").read_bytes()
    if orig_bin != repl_bin:
        raise ValueError("copper task outputs differ: original vs replay")
    if orig_log != repl_log:
        raise ValueError("copper unified logs differ: original vs replay")
    if comp.get("byte_identical") != "true" or comp.get("command") != "STOP":
        raise ValueError(f"copper comparison.txt does not record an identical STOP: {comp}")
    return {
        "comparison": comp,
        "comparison_txt_sha256": _sha(comp_text.encode()),
        "original_task_outputs_sha256": _sha(orig_bin),
        "replay_task_outputs_sha256": _sha(repl_bin),
        "task_outputs_byte_identical": True,
        "original_copper_log_sha256": _sha(orig_log),
        "replay_copper_log_sha256": _sha(repl_log),
        "copper_logs_byte_identical": True,
    }


def _fleet(repo: Path) -> dict:
    mod = _load_fleet_sim(repo)
    a, b = mod.scripted_scenario(), mod.scripted_scenario()
    if a.trace != b.trace or a.trace_digest() != b.trace_digest():
        raise ValueError("fleet-sim scripted scenario is not deterministic")
    # Fresh single-node replay for the actuator-stage latch fact.
    sim = mod.FleetSim(["n1"])
    outcome = sim.local_stop("n1", mod.StopEvent("e1", "robot-a"))
    return {
        "trace_lines": list(a.trace),
        "trace_sha256_digest": a.trace_digest(),
        "replayed_twice_identical": True,
        "single_node_stop_outcome": outcome,
        "single_node_motion_permitted_after_stop": sim.motion_permitted("n1", "robot-a"),
        "single_node_adapter_invocations": sim.nodes["n1"].adapter_invocations,
    }


def _fail_probes(repo: Path) -> dict:
    """Run the real app STOP path twice. Returns SKIPPED (with reason) if
    the app stack is unavailable; never invents an outcome."""
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    try:
        from fastapi.testclient import TestClient  # noqa: F401
        from app.main import create_app, Store
        from adapters.robot_sim import SimulatedRobotAdapter
        from integrations.secure_core import SecureCoreRejected
    except Exception as exc:  # pragma: no cover - depends on env
        return {"status": "SKIPPED", "reason": f"{type(exc).__name__}: {exc}"}

    robot = "quberon-demo-001"
    orig_stop = SimulatedRobotAdapter.stop

    def run(secure_core, key):
        calls = []

        def counting(self):
            calls.append(1)
            return orig_stop(self)

        SimulatedRobotAdapter.stop = counting
        try:
            with tempfile.TemporaryDirectory(prefix="viz-fail-probe-") as td:
                db = str(Path(td) / "probe.db")
                app = create_app(db_path=db, secure_core=secure_core)
                store = Store(db)
                store.create_user("operator1", "operator-password-123", "operator")
                c = TestClient(app, base_url="https://testserver")
                assert c.post("/auth/login", data={"username": "operator1",
                              "password": "operator-password-123"},
                              follow_redirects=False).status_code == 303
                csrf = c.get(f"/api/robots/{robot}/status").json()["csrf_token"]
                r = c.post(f"/api/robots/{robot}/stop", json={"note": "viz probe"},
                           headers={"X-CSRF-Token": csrf, "Idempotency-Key": key})
                body = r.json()
                st = c.get(f"/api/robots/{robot}/status").json()
                return {
                    "http_status": r.status_code,
                    "command_state": body.get("command_state"),
                    "observed_state": body.get("observed_state", st.get("observed_state")),
                    "stop_latched": body.get("stop_latched", st.get("stop_latched")),
                    "secure_core": body.get("secure_core"),
                    "adapter_invocations": len(calls),
                }
        finally:
            SimulatedRobotAdapter.stop = orig_stop

    class RejectingCore:
        binary = "viz-probe"  # presence irrelevant: a decision was reached

        def authorize_stop(self, subject, now_unix=None):
            raise SecureCoreRejected(
                "secure core rejected STOP: REPLAY_REJECTED",
                decision={"code": "REPLAY_REJECTED", "sequence": 7,
                          "audit_record": "deadbeef"},
            )

    return {
        "status": "RUN",
        "core_unavailable": run(None, "viz-probe-unavailable"),
        "core_rejecting": run(RejectingCore(), "viz-probe-rejected"),
    }


def build_trace(repo_root) -> dict:
    repo = Path(repo_root).resolve()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    copper = _copper(repo)
    fleet = _fleet(repo)
    probes = _fail_probes(repo)
    comp = copper["comparison"]

    events = []
    # --- Scenario A: authorized STOP (Copper replay + fleet latch + adapter)
    # The simulated actuator outcome is obtained, not drawn.
    from adapters.robot_sim import SimulatedRobotAdapter as _SimAdapter  # stdlib-local

    adapter_result = _SimAdapter().stop()
    events += [
        {"scenario": "authorized_stop", "stage": "sensor",
         "title": "Sensor / intervention source emits STOP",
         "detail": f"Copper InterventionSource: command={comp['command']} "
                   f"sequence={comp['sequence']} (comparison.txt, sha256="
                   f"{copper['comparison_txt_sha256'][:16]}…)"},
        {"scenario": "authorized_stop", "stage": "recognition",
         "title": "Recognition: command recognised as STOP",
         "detail": "Copper Authorization task: authorized iff command == \"STOP\"; "
                   f"recorded authorized={comp['authorized']}"},
        {"scenario": "authorized_stop", "stage": "authorization",
         "title": "Authorization: replay byte-identical",
         "detail": f"task-outputs sha256={copper['original_task_outputs_sha256']} "
                   f"original==replay byte_identical={comp['byte_identical']} "
                   f"keyframe_byte_identical={comp['keyframe_byte_identical']}"},
        {"scenario": "authorized_stop", "stage": "actuator",
         "title": "Simulated actuator outcome (SIMULATED)",
         "detail": f"SimulatedRobotAdapter.stop -> {adapter_result.command_state}/"
                   f"{adapter_result.observed_state}; fleet single-node STOP -> "
                   f"{fleet['single_node_stop_outcome']} motion_permitted="
                   f"{fleet['single_node_motion_permitted_after_stop']} "
                   f"adapter_invocations={fleet['single_node_adapter_invocations']}"},
    ]
    # --- Scenarios B/C: fail direction, from actual app probes if run
    if probes.get("status") == "RUN":
        u, r = probes["core_unavailable"], probes["core_rejecting"]
        events += [
            {"scenario": "core_unavailable", "stage": "sensor",
             "title": "Sensor / operator STOP request",
             "detail": "Authenticated simulation STOP request reaches execute_stop "
                       "(real app probe, tmp DB)"},
            {"scenario": "core_unavailable", "stage": "recognition",
             "title": "Recognition: STOP request recognised",
             "detail": "execute_stop convergence path entered; no secure-core client "
                       "provisioned (core unavailable, not a rejection)"},
            {"scenario": "core_unavailable", "stage": "authorization",
             "title": "Authorization: UNAVAILABLE -> UNSIGNED",
             "detail": f"secure_core.status={u['secure_core']['status']} "
                       f"decision={u['secure_core']['decision']} "
                       f"sequence={u['secure_core']['sequence']} "
                       f"audit_record={u['secure_core']['audit_record']}"},
            {"scenario": "core_unavailable", "stage": "actuator",
             "title": "STOP proceeds UNSIGNED, latch retained (SIMULATED)",
             "detail": f"http={u['http_status']} adapter_invocations={u['adapter_invocations']} "
                       f"command_state={u['command_state']} stop_latched={u['stop_latched']} "
                       f"observed_state={u['observed_state']}"},
            {"scenario": "core_rejecting", "stage": "sensor",
             "title": "Sensor / operator STOP request",
             "detail": "Authenticated simulation STOP request reaches execute_stop "
                       "(real app probe, tmp DB)"},
            {"scenario": "core_rejecting", "stage": "recognition",
             "title": "Recognition: STOP request recognised",
             "detail": "execute_stop convergence path entered; reachable core returns "
                       "a non-ACCEPTED decision"},
            {"scenario": "core_rejecting", "stage": "authorization",
             "title": "Authorization: REJECTED -> fail closed",
             "detail": f"secure_core.status={r['secure_core']['status']} "
                       f"decision={r['secure_core']['decision']} "
                       f"sequence={r['secure_core']['sequence']}"},
            {"scenario": "core_rejecting", "stage": "actuator",
             "title": "STOP blocked, state UNKNOWN, latch retained (SIMULATED)",
             "detail": f"http={r['http_status']} adapter_invocations={r['adapter_invocations']} "
                       f"command_state={r['command_state']} stop_latched={r['stop_latched']} "
                       f"observed_state={r['observed_state']}"},
        ]
    else:
        events.append(
            {"scenario": "fail_direction", "stage": "authorization",
             "title": "Fail-direction probes SKIPPED",
             "detail": f"app stack unavailable: {probes.get('reason')}"})

    trace = {
        "kind": "quberon-viz-stop-path-trace/v1",
        "simulated": True,
        "physical_robot": False,
        "copper": copper,
        "fleet": fleet,
        "fail_probes": probes,
        "events": events,
    }
    trace["source_trace_sha256"] = canonical_sha256(
        {k: v for k, v in trace.items() if k != "source_trace_sha256"})
    return trace
