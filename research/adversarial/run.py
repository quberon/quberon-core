"""Execute corpus cases against validate_plan (direct) and /plan (endpoint).

Never run this corpus against the Pi or any deployed instance.
Runs only against a throwaway local instance with its own temp database.
Fully offline, no network, no API key, no live provider: the endpoint
path uses a stub provider that returns the raw payload parsed exactly
as a provider response would be (json.loads, else the raw value), so
the validator -- not a model -- is the system under test.
Payloads are fed as raw strings, never pre-parsed by the corpus loader
beyond the provider-emulation step inside each path.

Wave 4 full scale: generated cases run direct + endpoint; deterministic
mutations run through the actual /plan endpoint (not direct-only, as in
the pilot). Every case is assigned one of five system states in a fixed
rotation: latched, unlatched, persistence-degraded,
secure-core-unavailable, secure-core-rejecting. In latched and
persistence-degraded states the latch is held (fail-closed semantics),
so an originally benign proposal is expected to be rejected there; that
rejection is NOT counted as a benign false-reject. False-reject is
measured only where acceptance is state-permitted.

WEAK EVIDENCE WARNING: the corpus templates and the validator were
authored by the same agent. See evidence/adversarial-full.md.
Real-model adversary is BLOCKED (no application META_API_URL/META_MODEL
in this environment; Hermes credentials are never reused). The
independent-model architecture (separate generation step, offline run)
is retained, but this corpus is templates.

Stops immediately on any S0 violation (I4 latch, I5 adapter, I7 core).
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
from provenance import (  # noqa: E402
    atomic_write_json, enrich_summary, git_commit, toolchain, utcnow,
)
from integrations.meta import validate_plan  # noqa: E402
from integrations.secure_core import SecureCoreRejected, SecureCoreUnavailable  # noqa: E402

ROBOT = os.environ.get("ROBOT_ID", "quberon-demo-001")

STATES = ["latched", "unlatched", "persistence-degraded",
          "secure-core-unavailable", "secure-core-rejecting"]
LATCH_HELD_STATES = {"latched", "persistence-degraded"}


def state_for_index(i):
    return STATES[i % len(STATES)]


def state_for_case(case, idx=0):
    """Deterministic state by case-ID hash, NOT by position: template
    subclasses cycle with period 5, so a positional rotation would alias
    every subclass to a single state. Hashing decouples them."""
    h = int(hashlib.sha256(case["id"].encode()).hexdigest()[:8], 16)
    return STATES[h % len(STATES)]


def latch_for_state(state):
    return state in LATCH_HELD_STATES


def effective_expectation(case, state):
    """State-adjusted expectation: latch-held states reject even benign."""
    if case["expectation"] == "accept" and latch_for_state(state):
        return "reject"
    return case["expectation"]


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
    return "rejected"


def run_direct(case, state="unlatched"):
    raw = case["payload"]
    plan = parse_raw(raw)
    latch = latch_for_state(state)
    exp = effective_expectation(case, state)
    before = repr(latch).encode()
    t0 = time.perf_counter()
    exc, validation = None, None
    try:
        validation = validate_plan(plan, ROBOT, latch)
    except Exception as e:  # I1 captures this; never propagate
        exc = f"{type(e).__name__}: {e}"
    dt = (time.perf_counter() - t0) * 1000
    text = json.dumps(validation, default=str) if validation is not None else (exc or "")
    obs = {"path": "direct", "expectation": exp, "plan": plan,
           "validation": validation, "response_text": text, "response_json": None,
           "http_status": None, "exception": exc, "latency_ms": round(dt, 3),
           "response_bytes": len(text.encode()), "latch_before": before,
           "latch_after": repr(latch).encode(), "adapter_calls_before": 0,
           "adapter_calls_after": 0, "new_audit_actions": [],
           "secure_core_calls_before": 0, "secure_core_calls_after": 0,
           "forbidden_strings": [os.environ["ADVERSARIAL_SENTINEL"], str(Path.home())]}
    inv, viol = check_all(obs)
    return {"id": case["id"], "class": case["class"], "subclass": case["subclass"],
            "path": "direct", "state": state, "outcome": outcome_of(validation),
            "expected": exp, "original_expectation": case["expectation"],
            "http_status": None, "invariants": inv, "violations": viol,
            "latency_ms": obs["latency_ms"], "response_bytes": obs["response_bytes"]}


class RawProvider:
    name = "raw-stub-no-live-provider"

    def __init__(self):
        self.raw = ""

    def propose(self, robot_id, text):
        return parse_raw(self.raw)


class CountingCore:
    """Generic counting core: any /plan call to it is an I7 S0."""
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


class UnavailableCore(CountingCore):
    def authorize_stop(self, **kw):
        self.calls += 1
        raise SecureCoreUnavailable("secure core unavailable (test state)")


class RejectingCore(CountingCore):
    def authorize_stop(self, **kw):
        self.calls += 1
        raise SecureCoreRejected("secure core rejecting (test state)",
                                 decision={"code": "REJECTED_TEST_STATE"})


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

    tmp = tempfile.mkdtemp(prefix="n2-adversarial-")
    db = str(Path(tmp) / "test.db")
    provider = RawProvider()
    cores = {"generic": CountingCore(), "unavailable": UnavailableCore(),
             "rejecting": RejectingCore()}
    app = create_app(db_path=db, provider=provider, secure_core=cores["generic"])
    assert app.state.secure_core is cores["generic"]
    store = Store(db)
    store.create_user("operator1", "operator-password-123", "operator")
    client = TestClient(app, base_url="https://testserver", raise_server_exceptions=False)
    r = client.post("/auth/login", data={"username": "operator1", "password": "operator-password-123"},
                    follow_redirects=False)
    assert r.status_code == 303, r.text
    status = client.get(f"/api/robots/{ROBOT}/status").json()
    return {"client": client, "app": app, "provider": provider, "cores": cores,
            "counters": counters, "csrf": status["csrf_token"], "db": db, "orig": orig}


def apply_state(ctx, state):
    """Configure the throwaway instance for one of the five states."""
    app = ctx["app"]
    store = app.state.store
    store.stop_latched = latch_for_state(state)
    store.persistence_ok = state != "persistence-degraded"
    if state == "secure-core-unavailable":
        app.state.secure_core = ctx["cores"]["unavailable"]
    elif state == "secure-core-rejecting":
        app.state.secure_core = ctx["cores"]["rejecting"]
    else:
        app.state.secure_core = ctx["cores"]["generic"]
    return app.state.secure_core


def audit_actions(app):
    with app.state.store._db() as db:
        return [r["action"] for r in db.execute("SELECT action FROM events ORDER BY ts, id")]


def run_endpoint(case, ctx, state="unlatched"):
    client, app, provider = ctx["client"], ctx["app"], ctx["provider"]
    core = apply_state(ctx, state)
    exp = effective_expectation(case, state)
    provider.raw = case["payload"]
    plan = parse_raw(case["payload"])
    latch_before = repr(app.state.store.stop_latched).encode()
    audit_before = audit_actions(app)
    a0, c0 = ctx["counters"]["adapter"], core.calls
    t0 = time.perf_counter()
    exc, resp = None, None
    try:
        resp = client.post(f"/api/robots/{ROBOT}/plan", json={"text": "adversarial corpus case"},
                           headers={"X-CSRF-Token": ctx["csrf"]})
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
    remaining = list(audit_before)
    new_actions = []
    for a in audit_after:
        if a in remaining:
            remaining.remove(a)
        else:
            new_actions.append(a)
    obs = {"path": "endpoint", "expectation": exp, "plan": plan,
           "validation": validation, "response_text": text, "response_json": body,
           "http_status": resp.status_code if resp is not None else None,
           "exception": exc, "latency_ms": round(dt, 3),
           "response_bytes": len(text.encode()), "latch_before": latch_before,
           "latch_after": latch_after, "adapter_calls_before": a0,
           "adapter_calls_after": ctx["counters"]["adapter"], "new_audit_actions": new_actions,
           "secure_core_calls_before": c0, "secure_core_calls_after": core.calls,
           "forbidden_strings": [os.environ["ADVERSARIAL_SENTINEL"], str(Path.home()), ctx["db"]]}
    inv, viol = check_all(obs)
    return {"id": case["id"], "class": case["class"], "subclass": case["subclass"],
            "path": "endpoint", "state": state, "outcome": outcome_of(validation, body),
            "expected": exp, "original_expectation": case["expectation"],
            "http_status": resp.status_code if resp is not None else None,
            "invariants": inv, "violations": viol,
            "latency_ms": obs["latency_ms"], "response_bytes": obs["response_bytes"]}


SEV_RANK = {"over-block": 0, "S4": 0, "S3": 1, "S2": 2, "S1": 3, "S0": 4}


def summarize(results, cases_by_id):
    by_class, by_inv, by_state = {}, {}, {}
    seen_class_ids = {}
    for iid in [f"I{i}" for i in range(1, 11)]:
        by_inv[iid] = {"checked": 0, "violations": 0, "worst": None}
    escapes, overblocked = [], []
    benign = {"results": 0, "accept_expected": 0, "rejected_in_error": 0}
    for r in results:
        c = by_class.setdefault(r["class"], {"cases": 0, "expected_reject": 0, "rejected": 0,
                                             "accepted_in_error": 0, "violations": 0, "worst": None})
        ids = seen_class_ids.setdefault(r["class"], set())
        if r["id"] not in ids:
            ids.add(r["id"])
            c["cases"] += 1
            if (cases_by_id.get(r["id"]) or {}).get("expectation") == "reject":
                c["expected_reject"] += 1
        if r["outcome"] == "rejected":
            c["rejected"] += 1
        s = by_state.setdefault(r.get("state", "unlatched"),
                                {"results": 0, "accepted": 0, "rejected": 0, "violations": 0})
        s["results"] += 1
        s["accepted" if r["outcome"] == "accepted" else "rejected"] += 1
        payload = (cases_by_id.get(r["id"]) or {}).get("payload", "")
        if r["expected"] == "reject" and r["outcome"] == "accepted":
            c["accepted_in_error"] += 1
            escapes.append({"id": r["id"], "path": r["path"], "state": r.get("state"),
                            "kind": "accepted-in-error", "class": r["class"],
                            "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                            "payload_prefix": payload[:200]})
        for v in r["violations"]:
            c["violations"] += 1
            s["violations"] += 1
            if c["worst"] is None or SEV_RANK[v["severity"]] > SEV_RANK[c["worst"]]:
                c["worst"] = v["severity"]
            escapes.append({"id": r["id"], "path": r["path"], "state": r.get("state"),
                            "kind": "invariant-violation", "class": r["class"],
                            "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                            "payload_prefix": payload[:200], **v})
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
        # Benign false-reject: original benign/control accept, state permits
        # acceptance (expected==accept after state adjustment), but rejected.
        if r["original_expectation"] == "accept":
            benign["results"] += 1
            if r["expected"] == "accept":
                benign["accept_expected"] += 1
                if r["outcome"] != "accepted":
                    benign["rejected_in_error"] += 1
                    overblocked.append({"id": r["id"], "path": r["path"], "state": r.get("state"),
                                        "class": r["class"]})
    benign_rate = (
        round(benign["rejected_in_error"] / benign["accept_expected"], 6)
        if benign["accept_expected"] else None)
    benign_out = {**benign, "false_reject_rate": benign_rate}
    return {"by_class": by_class, "by_invariant": by_inv, "by_state": by_state,
            "escapes": escapes, "overblocked": overblocked, "benign": benign_out,
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
        print(f"mutations_generated={len(muts)}", flush=True)
        cases = cases + muts
    hashes = [hashlib.sha256(c["payload"].encode()).hexdigest() for c in cases]
    print(f"cases={len(cases)} unique_payloads={len(set(hashes))} paths={args.paths}", flush=True)
    cases_by_id = {c["id"]: c for c in cases}
    results = []
    paths = args.paths.split(",")
    ctx = make_endpoint() if "endpoint" in paths else None
    t_start = time.time()
    started_utc = utcnow()
    run_commit = git_commit()
    generator = {"script": "research/adversarial/run.py",
                 "name": "adversarial-runner",
                 "command": " ".join(sys.argv),
                 "mutations": args.mutations, "paths": args.paths,
                 "cases": len(cases)}

    def _enrich(summary, complete, reason):
        return enrich_summary(
            summary, complete=complete, reason=reason,
            started_utc=started_utc, duration_s=round(time.time() - t_start, 3),
            commit=run_commit, toolchain_info=toolchain(commit=run_commit),
            generator=generator)
    try:
        for idx, case in enumerate(cases):
            state = state_for_case(case, idx)
            # Mutations run through the actual endpoint in Wave 4.
            case_paths = ["endpoint"] if case["class"] == "mutation" else paths
            for p in case_paths:
                r = run_direct(case, state) if p == "direct" else run_endpoint(case, ctx, state)
                results.append(r)
                for v in r["violations"]:
                    if v["severity"] == "S0":
                        print(f"S0 VIOLATION {r['id']} {p} state={state} {v} -- STOPPING", flush=True)
                        Path(args.out).write_text("".join(json.dumps(x) + "\n" for x in results))
                        # S0 stop is not a finished run: never citable.
                        atomic_write_json(Path(args.summary), _enrich(
                            summarize(results, cases_by_id),
                            complete=False, reason="S0 violation: stopped early"))
                        return 2
            if (idx + 1) % 10000 == 0:
                print(f"progress cases={idx+1}/{len(cases)} results={len(results)} "
                      f"elapsed_s={round(time.time()-t_start,1)}", flush=True)
    finally:
        if ctx:
            from adapters.robot_sim import SimulatedRobotAdapter
            for meth, o in ctx["orig"].items():
                setattr(SimulatedRobotAdapter, meth, o)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("".join(json.dumps(r) + "\n" for r in results))
    summary = summarize(results, cases_by_id)
    # Self-describing: the count travels with complete/commit/finished_utc/
    # toolchain/generator (via ops.longrun when importable, else the
    # vendored fallback in provenance.py; the source is recorded inside).
    enriched = _enrich(summary, complete=True, reason="finished")
    atomic_write_json(Path(args.summary), enriched)
    summary = enriched
    print(json.dumps({"total_results": summary["total_results"],
                      "escapes": len(summary["escapes"]),
                      "overblocked": len(summary["overblocked"]),
                      "benign": summary["benign"],
                      "s0": len(summary["s0_violations"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
