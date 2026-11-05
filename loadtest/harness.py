"""Local simulated STOP-under-load harness (Wave5 F3).

Mac/local simulation evidence ONLY. This measures the *simulated*
FastAPI app served by uvicorn on 127.0.0.1 with SimulatedRobotAdapter
(and, where noted, an injected adapter delay / fake secure-core stub).
It is not Pi, hardware, network, real-time, or physical stop-time
evidence, and must not be cited as a latency guarantee (QIP-R3.3).

Method (honest isolation limits are stated, not hidden):
- One fresh app + fresh SQLite DB per scenario, real HTTP via uvicorn
  in a thread, authenticated operator session per client.
- Background load (planner / status / task / CPU spin) runs
  continuously while STOP samples are taken.
- STOP samples are taken sequentially (stop_concurrency=1) except in
  the explicit concurrent_stops scenario, so a sample's latency is
  not confounded by other STOPs queueing on Store.lock -- except that
  simulated-task load also takes Store.lock, which is part of what
  the status_task_load scenario is measuring and is reported as such.
- Timing is time.perf_counter_ns() around the HTTP request only.
  It includes uvicorn threadpool scheduling, Python/GIL, SQLite WAL
  writes and Store.lock waits. It cannot isolate "the STOP logic"
  from those; see progress/F3-stop-load.md for the negative-result
  discussion.
"""
from __future__ import annotations

import math
import multiprocessing
import os
import statistics
import threading
import time
from dataclasses import dataclass, field

# Importing app.main must stay inert (it is; create_app does the work).
from adapters.robot_sim import SimulatedRobotAdapter  # noqa: E402
from integrations.secure_core import SecureCoreRejected  # noqa: E402

ROBOT = "quberon-demo-001"


# ---------------------------------------------------------------- stats
def _nearest_rank(sorted_vals, pct):
    if not sorted_vals:
        raise ValueError("no samples")
    idx = math.ceil(pct / 100.0 * len(sorted_vals)) - 1
    return sorted_vals[min(max(idx, 0), len(sorted_vals) - 1)]


def summarize(samples_ms):
    """Deterministic summary. Percentiles: nearest-rank on sorted data.

    jitter_ms = mean absolute successive difference in *sample order*
    (not sorted order); 0.0 for fewer than 2 samples.
    """
    vals = [float(x) for x in samples_ms]
    if not vals:
        raise ValueError("no samples")
    s = sorted(vals)
    jitter = (sum(abs(b - a) for a, b in zip(vals, vals[1:])) / (len(vals) - 1)
              if len(vals) > 1 else 0.0)
    return {
        "n": len(vals),
        "min_ms": s[0],
        "median_ms": statistics.median(s),
        "mean_ms": statistics.fmean(vals),
        "p95_ms": _nearest_rank(s, 95),
        "p99_ms": _nearest_rank(s, 99),
        "max_ms": s[-1],
        "jitter_ms": jitter,
    }


# ---------------------------------------------------------------- fakes
class AcceptedCoreStub:
    """Fake *accepted* secure core: no Rust subprocess, no signing claim."""
    def authorize_stop(self, subject):
        return {"code": "ACCEPTED_SIMULATION_STOP_AUTHORIZATION",
                "sequence": 1, "audit_record": "stub-not-a-real-record"}


class RejectingCoreStub:
    """Reachable-refusal stub (R-IMM-2 / QIP-R7.4): distinct from unavailable."""
    def authorize_stop(self, subject):
        raise SecureCoreRejected(
            "stub reachable refusal",
            decision={"code": "REJECTED_SIMULATION_STUB", "sequence": None,
                      "audit_record": None})


class SlowPlanner:
    name = "slow-sim-planner"

    def __init__(self, delay_s=0.03):
        self.delay_s = delay_s

    def propose(self, robot_id, text):
        time.sleep(self.delay_s)
        return {"summary": "sim", "robot_id": robot_id,
                "requested_action": "SIMULATE_INSPECTION",
                "required_capabilities": ["inspect"], "hazards": [],
                "human_confirmation_required": True, "provider": self.name}


class AdapterProbe:
    """Counts adapter.stop() calls; optionally injects a fixed delay."""
    def __init__(self, delay_s=0.0):
        self.delay_s = delay_s
        self.calls = 0
        self._orig = SimulatedRobotAdapter.stop
        self._lock = threading.Lock()

    def __enter__(self):
        probe = self

        def delayed(self):  # noqa: N805 - replaces unbound original below
            with probe._lock:
                probe.calls += 1
            if probe.delay_s:
                time.sleep(probe.delay_s)
            return probe._orig(self)

        SimulatedRobotAdapter.stop = delayed
        return self

    def __exit__(self, *exc):
        SimulatedRobotAdapter.stop = self._orig
        return False


def _cpu_spin(stop_event):
    x = 0
    while not stop_event.is_set():
        x = (x + 1) % 1_000_003


# ---------------------------------------------------------------- server
@dataclass
class Scenario:
    name: str
    core: str = "accepted_stub"      # accepted_stub | unavailable | rejecting
    planner_workers: int = 0
    status_workers: int = 0
    task_workers: int = 0
    cpu_workers: int = 0
    adapter_delay_s: float = 0.0
    stop_concurrency: int = 1
    samples: int = 30


DEFAULT_SCENARIOS = [
    Scenario("baseline_accepted_stub"),
    Scenario("planner_load", planner_workers=4),
    Scenario("status_task_load", status_workers=3, task_workers=3),
    Scenario("cpu_contention", cpu_workers=0),  # 0 -> resolved to cpu_count at run
    Scenario("slow_adapter", adapter_delay_s=0.100),
    Scenario("core_unavailable", core="unavailable"),
    Scenario("core_rejecting", core="rejecting"),
    Scenario("concurrent_stops", stop_concurrency=8, samples=32),
]


class _Server:
    def __init__(self, tmpdir, core, provider):
        import httpx
        import uvicorn
        from app.main import Store, create_app

        self._httpx = httpx
        db = os.path.join(tmpdir, "load.db")
        core_obj = {"accepted_stub": AcceptedCoreStub(),
                    "unavailable": None,
                    "rejecting": RejectingCoreStub()}[core]
        self.app = create_app(db_path=db, provider=provider, secure_core=core_obj)
        store = Store(db)
        store.create_user("operator1", "operator-password-123", "operator")
        # Free port via a throwaway socket.
        import socket
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        self.port = sock.getsockname()[1]
        sock.close()
        config = uvicorn.Config(self.app, host="127.0.0.1", port=self.port,
                                log_level="error", access_log=False)
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.port}"
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                with httpx.Client(timeout=2) as c:
                    if c.get(self.base + "/healthz").status_code == 200:
                        return
            except Exception:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def close(self):
        self.server.should_exit = True
        self.thread.join(timeout=10)

    def login(self):
        """Return (client, csrf). Cookie is passed as an explicit header:
        the app sets Secure cookies, which an http:// httpx jar would
        withhold; carrying it manually keeps the local transport honest
        and visible rather than silently switching schemes."""
        c = self._httpx.Client(base_url=self.base, timeout=10)
        r = c.post("/auth/login", data={"username": "operator1",
                                        "password": "operator-password-123"},
                   follow_redirects=False)
        assert r.status_code == 303, r.text
        token = r.cookies.get("quberon_session")
        assert token
        c.headers["Cookie"] = f"quberon_session={token}"
        s = c.get(f"/api/robots/{ROBOT}/status")
        assert s.status_code == 200, s.text
        return c, s.json()["csrf_token"]


def _load_worker(kind, server, stop_event, counters):
    try:
        client, csrf = server.login()
    except Exception:
        counters[kind + "_login_errors"] = counters.get(kind + "_login_errors", 0) + 1
        return
    i = 0
    try:
        while not stop_event.is_set():
            i += 1
            try:
                if kind == "planner":
                    r = client.post(f"/api/robots/{ROBOT}/plan",
                                    json={"text": "check status"},
                                    headers={"X-CSRF-Token": csrf})
                    key = ("planner_busy" if r.status_code == 200
                           and r.json().get("provider_status") == "busy"
                           else f"planner_{r.status_code}")
                elif kind == "status":
                    r = client.get(f"/api/robots/{ROBOT}/status")
                    key = f"status_{r.status_code}"
                else:
                    r = client.post(f"/api/robots/{ROBOT}/simulated-task",
                                    json={"action": "SIMULATE_INSPECTION"},
                                    headers={"X-CSRF-Token": csrf,
                                             "Idempotency-Key": f"load-{i}-{threading.get_ident()}"})
                    key = f"task_{r.status_code}"
            except Exception as exc:  # counted, never hidden
                key = f"{kind}_error_{type(exc).__name__}"
            counters[key] = counters.get(key, 0) + 1
    finally:
        client.close()


def run_scenario(scn: Scenario, tmp_root: str) -> dict:
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix=f"f3-{scn.name}-", dir=tmp_root)
    cpu_n = scn.cpu_workers or (os.cpu_count() or 1 if scn.name == "cpu_contention" else 0)
    core_label = scn.core
    counters: dict = {}
    stop_event = threading.Event()
    threads, procs = [], []
    ctx = multiprocessing.get_context("fork")
    cpu_stop = ctx.Event()
    samples_ms, outcomes = [], []
    with AdapterProbe(scn.adapter_delay_s) as probe:
        server = _Server(tmpdir, scn.core, SlowPlanner(0.03))
        try:
            for kind, n in (("planner", scn.planner_workers),
                            ("status", scn.status_workers),
                            ("task", scn.task_workers)):
                for _ in range(n):
                    t = threading.Thread(target=_load_worker,
                                         args=(kind, server, stop_event, counters),
                                         daemon=True)
                    t.start()
                    threads.append(t)
            for _ in range(cpu_n):
                p = ctx.Process(target=_cpu_spin, args=(cpu_stop,), daemon=True)
                p.start()
                procs.append(p)
            if threads or procs:
                time.sleep(0.3)  # let load actually establish before sampling

            client, csrf = server.login()
            try:
                def one_stop(i):
                    t0 = time.perf_counter_ns()
                    r = client.post(f"/api/robots/{ROBOT}/stop",
                                    json={"note": "f3 load"},
                                    headers={"X-CSRF-Token": csrf,
                                             "Idempotency-Key": f"f3-{scn.name}-{i}"})
                    dt = (time.perf_counter_ns() - t0) / 1e6
                    try:
                        body = r.json()
                    except Exception:
                        body = {}
                    return dt, {"status": r.status_code,
                                "command_state": body.get("command_state"),
                                "secure_core": (body.get("secure_core") or {}).get("status")}

                if scn.stop_concurrency <= 1:
                    for i in range(scn.samples):
                        dt, out = one_stop(i)
                        samples_ms.append(dt)
                        outcomes.append(out)
                else:
                    done = 0
                    while done < scn.samples:
                        batch = min(scn.stop_concurrency, scn.samples - done)
                        results: list = [None] * batch

                        def run_one(j, base=done):
                            results[j] = one_stop(base + j)

                        ts = [threading.Thread(target=run_one, args=(j,))
                              for j in range(batch)]
                        for t in ts:
                            t.start()
                        for t in ts:
                            t.join()
                        for dt, out in results:
                            samples_ms.append(dt)
                            outcomes.append(out)
                        done += batch
            finally:
                client.close()
        finally:
            stop_event.set()
            cpu_stop.set()
            for t in threads:
                t.join(timeout=5)
            for p in procs:
                p.terminate()
            server.close()
    from collections import Counter
    outcome_counts = Counter(
        f"{o['status']}/{o['command_state']}/{o['secure_core']}" for o in outcomes)
    return {
        "scenario": scn.name,
        "core": core_label,
        "adapter_delay_s": scn.adapter_delay_s,
        "cpu_workers": cpu_n,
        "planner_workers": scn.planner_workers,
        "status_workers": scn.status_workers,
        "task_workers": scn.task_workers,
        "stop_concurrency": scn.stop_concurrency,
        "stats": summarize(samples_ms),
        "samples_ms": samples_ms,
        "outcomes": dict(sorted(outcome_counts.items())),
        "adapter_stop_calls": probe.calls,
        "load_counters": dict(sorted(counters.items())),
    }


def run_all(samples=30, tmp_root=None):
    import tempfile
    root = tmp_root or tempfile.mkdtemp(prefix="f3-loadtest-")
    results = []
    for scn in DEFAULT_SCENARIOS:
        scn = Scenario(**{**scn.__dict__, "samples": samples})
        results.append(run_scenario(scn, root))
    return results
