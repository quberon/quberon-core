"""Execute corpus cases against validate_plan (direct) and /plan (endpoint).

Never run this corpus against the Pi or any deployed instance.
Runs only against a throwaway local instance with its own temp database.
Fully offline, no network, no API key, no live provider: the endpoint
path uses a stub provider that returns the raw payload parsed exactly
as a provider response would be (json.loads, else the raw value), so
the validator -- not a model -- is the system under test.
Payloads are fed as raw strings, never pre-parsed by the corpus loader
beyond the provider-emulation step inside each path.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
os.environ.setdefault("ADVERSARIAL_SENTINEL", "QUBERON_N5_SENTINEL_7f3a9c")

from invariants import check_all  # noqa: E402
from integrations.meta import validate_plan  # noqa: E402

ROBOT = os.environ.get("ROBOT_ID", "quberon-demo-001")


def parse_raw(raw):
    try:
        return json.loads(raw)
    except Exception:
        return raw


def load_cases(paths):
    cases = []
    for p in paths:
        for line in Path(p).read_text().splitlines():
            if line.strip():
                cases.append(json.loads(line))
    return cases


def outcome_of(validation, body=None):
    if isinstance(validation, dict) and validation.get("allowed_as_proposal") is True:
        return "accepted"
    if isinstance(body, dict) and body.get("provider_status") in {"unavailable", "busy"}:
        return "rejected"
    return "rejected"


def run_direct(case, latch=False):
    raw = case["payload"]
    plan = parse_raw(raw)
    before = repr(latch).encode()
    t0 = time.perf_counter()
    exc, validation = None, None
    try:
        validation = validate_plan(plan, ROBOT, latch)
    except Exception as e:  # I1 captures this; never propagate
        exc = f"{type(e).__name__}: {e}"
    dt = (time.perf_counter() - t0) * 1000
    text = json.dumps(validation, default=str) if validation is not None else (exc or "")
    obs = {"path": "direct", "expectation": case["expectation"], "plan": plan,
           "validation": validation, "response_text": text, "response_json": None,
           "http_status": None, "exception": exc, "latency_ms": round(dt, 3),
           "response_bytes": len(text.encode()), "latch_before": before,
           "latch_after": repr(latch).encode(), "adapter_calls_before": 0,
           "adapter_calls_after": 0, "new_audit_actions": [],
           "secure_core_calls_before": 0, "secure_core_calls_after": 0,
           "forbidden_strings": [os.environ["ADVERSARIAL_SENTINEL"], str(Path.home())]}
    inv, viol = check_all(obs)
    return {"id": case["id"], "class": case["class"], "subclass": case["subclass"],
            "path": "direct", "outcome": outcome_of(validation),
            "expected": case["expectation"], "http_status": None,
            "invariants": inv, "violations": viol,
            "latency_ms": obs["latency_ms"], "response_bytes": obs["response_bytes"]}


class RawProvider:
    name = "raw-stub-no-live-provider"

    def __init__(self):
        self.raw = ""

    def propose(self, robot_id, text):
        return parse_raw(self.raw)


class CountingCore:
    def __init__(self):
        self.calls = 0

    def authorize_stop(self, **kw):
        self.calls += 1
        raise RuntimeError("secure core must not be called by /plan")

    def __getattr__(self, name):
        def f(**kw):
            self.calls += 1
            raise RuntimeError("secure core must not be called by /plan")
        return f


def make_endpoint():
    from fastapi.testclient import TestClient
    from adapters.robot_sim import SimulatedRobotAdapter
    from app.main import Store, create_app

    counters = {"adapter": 0}
    orig = {}
    for meth in ("stop", "simulated_task", "reset_simulation"):
        orig[meth] = getattr(SimulatedRobotAdapter, meth)

        def make(m, o):
            def wrapped(self, *a, **k):
                counters["adapter"] += 1
                return o(self, *a, **k)
            return wrapped
        setattr(SimulatedRobotAdapter, meth, make(meth, orig[meth]))

    tmp = tempfile.mkdtemp(prefix="n5-adversarial-")
    db = str(Path(tmp) / "test.db")
    provider = RawProvider()
    core = CountingCore()
    app = create_app(db_path=db, provider=provider, secure_core=core)
    # create_app treats secure_core=None as no client; our counting stub was
    # passed explicitly and stored. Verify:
    assert app.state.secure_core is core
    store = Store(db)
    store.create_user("operator1", "operator-password-123", "operator")
    client = TestClient(app, base_url="https://testserver", raise_server_exceptions=False)
    r = client.post("/auth/login", data={"username": "operator1", "password": "operator-password-123"},
                    follow_redirects=False)
    assert r.status_code == 303, r.text
    status = client.get(f"/api/robots/{ROBOT}/status").json()
    return client, app, provider, core, counters, status["csrf_token"], db, orig


def audit_actions(app):
    with app.state.store._db() as db:
        return [r["action"] for r in db.execute("SELECT action FROM events ORDER BY ts, id")]


def run_endpoint(case, ctx):
    client, app, provider, core, counters, csrf, db_path, _ = ctx
    provider.raw = case["payload"]
    plan = parse_raw(case["payload"])
    app.state.store.stop_latched = False
    latch_before = repr(app.state.store.stop_latched).encode()
    audit_before = audit_actions(app)
    a0, c0 = counters["adapter"], core.calls
    t0 = time.perf_counter()
    exc, resp = None, None
    try:
        resp = client.post(f"/api/robots/{ROBOT}/plan", json={"text": "adversarial corpus case"},
                           headers={"X-CSRF-Token": csrf})
    except Exception as e:
        exc = f"{type(e).__name__}: {e}"
    dt = (time.perf_counter() - t0) * 1000
    text = resp.text if resp is not None else (exc or "")
    body = None
    validation = None
    if resp is not None:
        try:
            body = resp.json()
        except Exception:
            body = None
        if isinstance(body, dict):
            validation = body.get("validation")
    latch_after = repr(app.state.store.stop_latched).encode()
    audit_after = audit_actions(app)
    # multiset difference, preserving order of new events
    remaining = list(audit_before)
    new_actions = []
    for a in audit_after:
        if a in remaining:
            remaining.remove(a)
        else:
            new_actions.append(a)
    obs = {"path": "endpoint", "expectation": case["expectation"], "plan": plan,
           "validation": validation, "response_text": text, "response_json": body,
           "http_status": resp.status_code if resp is not None else None,
           "exception": exc, "latency_ms": round(dt, 3),
           "response_bytes": len(text.encode()), "latch_before": latch_before,
           "latch_after": latch_after, "adapter_calls_before": a0,
           "adapter_calls_after": counters["adapter"], "new_audit_actions": new_actions,
           "secure_core_calls_before": c0, "secure_core_calls_after": core.calls,
           "forbidden_strings": [os.environ["ADVERSARIAL_SENTINEL"], str(Path.home()), db_path]}
    inv, viol = check_all(obs)
    return {"id": case["id"], "class": case["class"], "subclass": case["subclass"],
            "path": "endpoint", "outcome": outcome_of(validation, body),
            "expected": case["expectation"],
            "http_status": resp.status_code if resp is not None else None,
            "invariants": inv, "violations": viol,
            "latency_ms": obs["latency_ms"], "response_bytes": obs["response_bytes"]}


SEV_RANK = {"over-block": 0, "S4": 0, "S3": 1, "S2": 2, "S1": 3, "S0": 4}


def summarize(results, cases_by_id):
    by_class, by_inv = {}, {}
    for iid in [f"I{i}" for i in range(1, 11)]:
        by_inv[iid] = {"checked": 0, "violations": 0, "worst": None}
    escapes, overblocked = [], []
    for r in results:
        c = by_class.setdefault(r["class"], {"cases": 0, "expected_reject": 0, "rejected": 0,
                                             "accepted_in_error": 0, "violations": 0, "worst": None})
        # count cases once (direct path) for class case count
        if r["path"] == "direct":
            c["cases"] += 1
        if r["outcome"] == "rejected" and r["path"] == "direct":
            c["rejected"] += 1
        if r["expected"] == "reject":
            if r["path"] == "direct":
                c["expected_reject"] += 1
            if r["outcome"] == "accepted":
                c["accepted_in_error"] += 1
                escapes.append({"id": r["id"], "path": r["path"], "kind": "accepted-in-error",
                                "class": r["class"]})
        for v in r["violations"]:
            c["violations"] += 1
            if c["worst"] is None or SEV_RANK[v["severity"]] > SEV_RANK[c["worst"]]:
                c["worst"] = v["severity"]
            escapes.append({"id": r["id"], "path": r["path"], "kind": "invariant-violation", **v})
        for iid, st in r["invariants"].items():
            if iid == "I10" and r["expected"] != "accept":
                continue
            by_inv[iid]["checked"] += 1
            if st == "fail":
                by_inv[iid]["violations"] += 1
                sev = {"I1": "S2", "I2": "S1", "I3": "S1", "I4": "S0", "I5": "S0", "I6": "S1",
                       "I7": "S0", "I8": "S3", "I9": "S1", "I10": "over-block"}[iid]
                if by_inv[iid]["worst"] is None or SEV_RANK[sev] > SEV_RANK[by_inv[iid]["worst"]]:
                    by_inv[iid]["worst"] = sev
        if r["expected"] == "accept" and r["outcome"] != "accepted":
            overblocked.append({"id": r["id"], "path": r["path"], "class": r["class"]})
    return {"by_class": by_class, "by_invariant": by_inv,
            "escapes": escapes, "overblocked": overblocked,
            "total_results": len(results),
            "s0_violations": [e for e in escapes if e.get("severity") == "S0"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", nargs="+", default=[str(HERE / "corpus")])
    ap.add_argument("--mutations", type=int, default=0)
    ap.add_argument("--paths", default="direct,endpoint")
    ap.add_argument("--out", default=str(HERE / "results" / "results.jsonl"))
    ap.add_argument("--summary", default=str(HERE / "results" / "summary.json"))
    args = ap.parse_args()
    files = []
    for c in args.corpus:
        p = Path(c)
        found = sorted(p.glob("*.jsonl")) if p.is_dir() else [p]
        if args.mutations:  # regenerated below; never ingest a stale mutations file
            found = [f for f in found if f.name != "mutations.jsonl"]
        files.extend(found)
    cases = load_cases(files)
    if args.mutations:
        from mutate import generate_mutations
        control = [c for c in cases if c["class"] == "benign-control"]
        muts = generate_mutations(control, target=args.mutations)
        (HERE / "corpus" / "mutations.jsonl").write_text(
            "".join(json.dumps(m) + "\n" for m in muts))
        print(f"mutations_generated={len(muts)}")
        cases = cases + muts
    hashes = [hashlib.sha256(c["payload"].encode()).hexdigest() for c in cases]
    print(f"cases={len(cases)} unique_payloads={len(set(hashes))} paths={args.paths}")
    results = []
    paths = args.paths.split(",")
    ctx = make_endpoint() if "endpoint" in paths else None
    try:
        for case in cases:
            # mutations are direct-only in this pilot (volume path)
            case_paths = ["direct"] if case["class"] == "mutation" else paths
            for p in case_paths:
                r = run_direct(case) if p == "direct" else run_endpoint(case, ctx)
                results.append(r)
                for v in r["violations"]:
                    if v["severity"] == "S0":
                        print(f"S0 VIOLATION {r['id']} {p} {v} -- STOPPING", flush=True)
                        Path(args.out).write_text("".join(json.dumps(x) + "\n" for x in results))
                        Path(args.summary).write_text(json.dumps(
                            summarize(results, {}), indent=2))
                        return 2
    finally:
        if ctx:
            from adapters.robot_sim import SimulatedRobotAdapter
            for meth, o in ctx[-1].items():
                setattr(SimulatedRobotAdapter, meth, o)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("".join(json.dumps(r) + "\n" for r in results))
    summary = summarize(results, {})
    Path(args.summary).write_text(json.dumps(summary, indent=2))
    print(json.dumps({"total_results": summary["total_results"],
                      "escapes": len(summary["escapes"]),
                      "overblocked": len(summary["overblocked"]),
                      "s0": len(summary["s0_violations"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
