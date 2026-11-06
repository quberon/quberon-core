#!/usr/bin/env python3
"""Quberon deterministic build scheduler.

Stdlib only, Python 3.9+. Contains NO model call. Every decision in this file
is mechanical: fetch, compare, match, count, merge. Model work happens inside
the workers this module spawns, never in the scheduler itself.

Subcommands, each idempotent and safe to re-run:

    reconcile   fetch remote truth (never recall it from a transcript)
    harvest     gate finished nodes, merge Tier 1, leave Tier 2 at the PR
    refill      derive new backlog nodes deterministically from the repository
    dispatch    fill free slots with disjoint, ready nodes, detached
    heartbeat   record liveness and flag silent nodes
    report      regenerate REPORT.md from state (no reasoning)
    status      print a short human summary

Runtime state lives OUTSIDE the repository, in $QUBERON_STATE. Writing
scheduler state into the worktree would leave main permanently dirty and every
clean-clone gate would fail on the state file itself.
"""

from __future__ import annotations

import argparse
import fnmatch  # noqa: F401  (kept for reference; matching uses _glob_re)
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Paths and small utilities
# --------------------------------------------------------------------------

REPO = Path(os.environ.get("QUBERON_REPO", str(Path.home() / "quberon-core"))).resolve()
OPS = REPO / "ops"

if sys.platform == "darwin":
    _default_state = Path.home() / "Library" / "Application Support" / "Quberon"
else:
    _default_state = Path.home() / ".local" / "state" / "quberon"
STATE_DIR = Path(os.environ.get("QUBERON_STATE", str(_default_state)))

STATE_FILE = STATE_DIR / "state.json"
WORKTREES = STATE_DIR / "worktrees"
PROMPTS = STATE_DIR / "prompts"
NODE_LOGS = STATE_DIR / "logs" / "nodes"
HALT_FILES = (STATE_DIR / "HALT", REPO / "ops" / "HALT")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"{utcnow()} [schedule] {msg}", flush=True)


def run(cmd, cwd=None, timeout=300, check=False):
    """Run a command. Returns (rc, stdout, stderr). Never raises on non-zero."""
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if check and p.returncode != 0:
            log(f"command failed rc={p.returncode}: {' '.join(cmd)}\n{p.stderr[:2000]}")
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s: {' '.join(cmd)}"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    with os.fdopen(fd, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_json(path: Path, obj) -> None:
    atomic_write(path, json.dumps(obj, indent=2, sort_keys=False) + "\n")


def read_json(path: Path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def halted() -> bool:
    return any(p.exists() for p in HALT_FILES)


# --------------------------------------------------------------------------
# Config, ownership, backlog, state
# --------------------------------------------------------------------------


def load_config() -> dict:
    cfg = read_json(OPS / "config.json")
    if cfg is None:
        raise SystemExit("ops/config.json missing or invalid; refusing to guess defaults")
    return cfg


def load_ownership() -> dict:
    own = read_json(OPS / "ownership.json")
    if own is None:
        raise SystemExit("ops/ownership.json missing or invalid; refusing to dispatch blind")
    return own


def load_backlog() -> list:
    return read_json(OPS / "backlog.json", {"nodes": []})["nodes"]


def save_backlog(nodes: list) -> None:
    write_json(OPS / "backlog.json", {"version": 1, "nodes": nodes})


def load_state() -> dict:
    return read_json(
        STATE_FILE,
        {"version": 1, "nodes": {}, "remote": {}, "last_tick_utc": None, "incidents": []},
    )


def save_state(st: dict) -> None:
    write_json(STATE_FILE, st)


# --------------------------------------------------------------------------
# Glob matching and the disjointness rule
# --------------------------------------------------------------------------


def _glob_re(pattern: str) -> "re.Pattern":
    """Translate a git-style glob into a regex. '**' crosses '/', '*' does not."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def path_matches(path: str, patterns) -> bool:
    return any(_glob_re(p).match(path) for p in patterns)


def _literal_prefix(pattern: str) -> str:
    parts = []
    for seg in pattern.split("/"):
        if any(c in seg for c in "*?["):
            break
        parts.append(seg)
    return "/".join(parts)


def globs_overlap(a: str, b: str) -> bool:
    """Conservative: may report overlap where none exists, never the reverse.

    Erring toward 'they overlap' costs us a serialised pair of nodes. Erring the
    other way costs us two agents editing the same file, which is how an
    autonomous system quietly corrupts its own evidence.
    """
    if a == b:
        return True
    if _glob_re(a).match(b) or _glob_re(b).match(a):
        return True
    pa, pb = _literal_prefix(a), _literal_prefix(b)
    if not pa or not pb:  # a pattern rooted at a wildcard can touch anything
        return True
    return pa == pb or pa.startswith(pb + "/") or pb.startswith(pa + "/")


def sets_overlap(owns_a, owns_b) -> bool:
    return any(globs_overlap(x, y) for x in owns_a for y in owns_b)


def tier_of_paths(paths, ownership: dict) -> int:
    if any(path_matches(p, ownership.get("tier3_paths", [])) for p in paths):
        return 3
    if any(path_matches(p, ownership.get("tier2_paths", [])) for p in paths):
        return 2
    return 1


def reserved_conflicts(owns, ownership: dict):
    """Return reserved areas whose tier exceeds a node that claims these globs."""
    hits = []
    for area in ownership.get("areas", []):
        if area.get("status") != "reserved":
            continue
        if sets_overlap(owns, area.get("owns", [])):
            hits.append((area["id"], area.get("tier", 2)))
    return hits


# --------------------------------------------------------------------------
# git / gh helpers
# --------------------------------------------------------------------------


def git(*args, cwd=None, timeout=300):
    return run(["git", *args], cwd=cwd or REPO, timeout=timeout)


def gh_json(args, timeout=120):
    rc, out, err = run(["gh", *args], cwd=REPO, timeout=timeout)
    if rc != 0:
        return None, f"gh {' '.join(args)} rc={rc}: {err.strip()[:500]}"
    try:
        return json.loads(out or "null"), None
    except json.JSONDecodeError as e:
        return None, f"gh output not JSON: {e}"


def incident(kind: str, message: str) -> None:
    rc, _, err = run(["bash", str(OPS / "incident.sh"), kind, message], timeout=120)
    if rc != 0:
        log(f"INCIDENT (filing failed rc={rc}): {kind}: {message} :: {err[:300]}")


# --------------------------------------------------------------------------
# reconcile
# --------------------------------------------------------------------------


def cmd_reconcile(cfg, ownership, st) -> dict:
    git("fetch", "origin", "--prune", "--quiet", timeout=180)
    rc, head, _ = git("rev-parse", "origin/main")
    remote = {"fetched_utc": utcnow(), "main": head.strip() if rc == 0 else None}

    prs, err = gh_json(
        [
            "pr", "list", "--state", "open", "--limit", "100", "--json",
            "number,title,headRefName,isDraft,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,labels",
        ]
    )
    if err:
        remote["pr_error"] = err
        incident("gh", f"Cannot list PRs, dispatch and merge are unsafe: {err}")
    remote["open_prs"] = prs or []

    runs, err2 = gh_json(
        ["run", "list", "--branch", "main", "--limit", "1", "--json", "conclusion,status,displayTitle,url"]
    )
    remote["main_ci"] = (runs or [{}])[0] if not err2 else {"error": err2}

    st["remote"] = remote

    ci = remote.get("main_ci") or {}
    if ci.get("status") == "completed" and ci.get("conclusion") not in (None, "success"):
        st["main_red"] = True
        incident("ci", f"main CI is {ci.get('conclusion')}: {ci.get('url')}")
    else:
        st["main_red"] = False

    log(f"reconcile: main={remote['main']} open_prs={len(remote['open_prs'])} main_red={st['main_red']}")
    return st


# --------------------------------------------------------------------------
# harvest
# --------------------------------------------------------------------------


def pid_alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def pr_for_branch(st, branch):
    for pr in st.get("remote", {}).get("open_prs", []):
        if pr.get("headRefName") == branch:
            return pr
    return None


def checks_all_green(pr) -> bool:
    roll = pr.get("statusCheckRollup") or []
    if not roll:
        return False  # empty rollup is "unknown", never "green"
    for c in roll:
        concl = (c.get("conclusion") or "").upper()
        state = (c.get("state") or "").upper()
        if concl in ("SUCCESS", "NEUTRAL", "SKIPPED") or state == "SUCCESS":
            continue
        return False
    return True


def changed_paths(branch, base="origin/main"):
    rc, out, _ = git("diff", "--name-only", f"{base}...origin/{branch}")
    if rc != 0:
        return None
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def cmd_harvest(cfg, ownership, st) -> dict:
    for node_id, nd in list(st["nodes"].items()):
        if nd.get("status") not in ("running", "gating"):
            continue
        if pid_alive(nd.get("pid")):
            started = nd.get("started_epoch", time.time())
            if (time.time() - started) > cfg["node_budget_minutes"] * 60:
                log(f"{node_id}: over budget, terminating")
                try:
                    os.kill(int(nd["pid"]), 15)  # SIGTERM; longrun checkpoints on it
                except OSError:
                    pass
                nd["status"] = "over_budget"
            continue

        # Process gone: the node is finished, one way or another.
        branch = nd["branch"]
        log(f"{node_id}: worker exited, running gate")
        nd["status"] = "gating"
        save_state(st)

        rc, out, err = run(["bash", str(OPS / "gate.sh"), node_id, branch], timeout=3600)
        nd["gate_rc"] = rc
        nd["gate_finished_utc"] = utcnow()
        nd["evidence_path"] = f"docs/evidence/{node_id}/"
        if rc != 0:
            nd["attempts"] = nd.get("attempts", 1)
            if nd["attempts"] >= cfg["node_max_attempts"]:
                nd["status"] = "partial"
                log(f"{node_id}: gate failed, attempts exhausted -> partial")
            else:
                nd["status"] = "ready_retry"
                log(f"{node_id}: gate failed, will retry ({nd['attempts']}/{cfg['node_max_attempts']})")
            continue

        # Gate passed. Ownership check against the real diff, not the claim.
        paths = changed_paths(branch)
        if paths is None:
            nd["status"] = "blocked"
            nd["blocked_reason"] = "cannot diff branch against origin/main"
            continue
        strays = [p for p in paths if not path_matches(p, nd["owns"])]
        if strays:
            nd["status"] = "blocked"
            nd["blocked_reason"] = f"wrote outside owns: {strays[:10]}"
            incident("ownership", f"{node_id} wrote outside its owned paths: {strays[:10]}")
            continue

        effective_tier = max(nd.get("tier", 1), tier_of_paths(paths, ownership))
        nd["effective_tier"] = effective_tier

        pr = pr_for_branch(st, branch)
        if not pr:
            nd["status"] = "awaiting_pr"
            log(f"{node_id}: gate green but no open PR found")
            continue
        nd["pr"] = pr["number"]

        if effective_tier >= 2:
            nd["status"] = "awaiting_human"
            log(f"{node_id}: Tier {effective_tier} -> PR #{pr['number']} stops for human review")
            continue

        if pr.get("isDraft") or pr.get("mergeable") != "MERGEABLE" or not checks_all_green(pr):
            nd["status"] = "awaiting_ci"
            log(f"{node_id}: PR #{pr['number']} not mergeable yet "
                f"(mergeable={pr.get('mergeable')} green={checks_all_green(pr)})")
            continue

        rc2, _, err2 = run(
            ["gh", "pr", "merge", str(pr["number"]), cfg["merge_method"], "--delete-branch"],
            cwd=REPO, timeout=300,
        )
        if rc2 == 0:
            nd["status"] = "merged"
            nd["merged_utc"] = utcnow()
            log(f"{node_id}: Tier 1 merged as PR #{pr['number']}")
        else:
            nd["status"] = "merge_failed"
            nd["blocked_reason"] = err2[:500]
            incident("merge", f"{node_id} PR #{pr['number']} merge failed: {err2[:300]}")

    save_state(st)
    return st


# --------------------------------------------------------------------------
# refill: nine deterministic generators
# --------------------------------------------------------------------------


def _slug(text, maxlen=40):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:maxlen].strip("-") or "item"


def _tracked_files(subdir=None):
    args = ["ls-files"]
    if subdir:
        args.append(subdir)
    rc, out, _ = git(*args)
    return [ln for ln in out.splitlines() if ln.strip()] if rc == 0 else []


def gen_limitations(cfg, ownership):
    """1. Every line in docs/LIMITATIONS.md is a thing to make untrue."""
    p = REPO / "docs" / "LIMITATIONS.md"
    if not p.exists():
        return [], "docs/LIMITATIONS.md does not exist: W5-N6 was never done"
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line.startswith(("- ", "* ")):
            continue
        body = line[2:].strip()
        if len(body) < 12:
            continue
        out.append({
            "id": f"lim-{_slug(body)}",
            "title": f"Make untrue: {body}",
            "source": "generator:limitations",
            "tier": 1, "priority": 20, "owns": [], "gate": "",
            "needs_scoping": True,
        })
    return out, None


def gen_qip_gaps(cfg, ownership):
    """2. QIP requirements with no traced passing test.

    The authoritative table is section 11 of QIP-v0.1.md, whose rows read
    `| QIP-R3.1 | INTERVENE | UNIMPLEMENTED (no load/priority test in N4) |`.
    TRACEABILITY.md discusses the count in prose and is not machine-readable,
    so parsing it yields nothing: that was a real bug in the first version of
    this generator and is why every generator reports a skip reason.
    """
    qip = REPO / "docs" / "specs" / "intervention-profile" / "QIP-v0.1.md"
    if not qip.exists():
        return [], "QIP-v0.1.md not found"
    out, seen = [], set()
    for line in qip.read_text().splitlines():
        if not line.startswith("|") or "UNIMPLEMENTED" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        m = re.match(r"^(QIP-[A-Za-z0-9.\-]+)$", cells[0])
        if not m or m.group(1) in seen:
            continue
        rid = m.group(1)
        seen.add(rid)
        reason = cells[-1].replace("UNIMPLEMENTED", "").strip(" ()") or "no reason recorded"
        out.append({
            "id": f"qip-{_slug(rid)}",
            "title": (f"{rid} ({cells[1]}) is UNIMPLEMENTED: {reason}. "
                      f"Trace it to a passing conformance test or record it as "
                      f"explicitly untestable. Partial coverage stays UNIMPLEMENTED; "
                      f"never round a gap up to a trace."),
            "source": "generator:qip-section-11",
            "tier": 1, "priority": 10, "model": "design",
            "owns": ["conformance/**", f"progress/qip-{_slug(rid)}.md"],
            "gate": "python -m pytest conformance/ -q",
            "needs_scoping": False,
            "note": "A work node may not amend QIP traceability itself; section 11 "
                    "defines the amendment procedure and it belongs to the profile owner.",
        })
    return out, None


def gen_handoffs(cfg, ownership):
    """3. handoff: records left by nodes that refused to write outside their area."""
    out = []
    for f in _tracked_files("progress"):
        try:
            text = (REPO / f).read_text()
        except OSError:
            continue
        for m in re.finditer(r"^\s*handoff:\s*(.+)$", text, re.MULTILINE):
            body = m.group(1).strip()
            out.append({
                "id": f"ho-{_slug(body)}",
                "title": f"Handoff from {f}: {body}",
                "source": f"generator:handoff:{f}",
                "tier": 1, "priority": 15, "owns": [], "gate": "",
                "needs_scoping": True,
            })
    return out, None


def gen_todos(cfg, ownership):
    """4. Untracked TODO/FIXME/XXX in tracked source: fix it or delete it."""
    rc, out, _ = git("grep", "-nE", r"(TODO|FIXME|XXX)[: ]", "--", "*.py", "*.rs", "*.sh")
    if rc not in (0, 1):
        return [], "git grep failed"
    items = []
    for line in out.splitlines()[:200]:
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        path, lineno, body = parts
        items.append({
            "id": f"todo-{_slug(path + '-' + lineno)}",
            "title": f"Resolve or remove: {path}:{lineno} {body.strip()[:80]}",
            "source": "generator:todo",
            "tier": 1, "priority": 60, "owns": [path], "gate": "",
            "needs_scoping": True,
        })
    return items, None


def gen_control_path_coverage(cfg, ownership):
    """5. Control-path functions with no test mentioning them by name."""
    control = ["app/main.py", "integrations/secure_core.py", "integrations/interventions.py"]
    test_text = ""
    for f in _tracked_files("tests") + _tracked_files("conformance"):
        try:
            test_text += (REPO / f).read_text()
        except OSError:
            pass
    out = []
    for cf in control:
        p = REPO / cf
        if not p.exists():
            continue
        for m in re.finditer(r"^(?:async )?def ([a-z_][a-z0-9_]*)\(", p.read_text(), re.MULTILINE):
            name = m.group(1)
            if name.startswith("_") or len(name) < 5:
                continue
            if name in test_text:
                continue
            out.append({
                "id": f"cov-{_slug(cf + '-' + name)}",
                "title": f"No test names {cf}:{name}() - add coverage or justify the omission",
                "source": "generator:control-coverage",
                "tier": 1, "priority": 25,
                "owns": [f"tests/test_cov_{_slug(name)}.py", f"progress/cov-{_slug(name)}.md"],
                "gate": f"python -m pytest tests/test_cov_{_slug(name)}.py -q",
                "needs_scoping": False,
            })
    return out, None


def gen_registry(cfg, ownership):
    """6. candidate_unverified registry rows need decision packets (never promotion)."""
    p = REPO / "research" / "humanoids" / "registry" / "candidates.jsonl"
    if not p.exists():
        return [], "registry candidates.jsonl not found"
    n = sum(1 for line in p.read_text().splitlines()
            if '"candidate_unverified"' in line)
    if not n:
        return [], None
    return [{
        "id": "reg-decision-packet-refresh",
        "title": f"Refresh the human decision packet for {n} candidate_unverified entities",
        "source": "generator:registry",
        "tier": 1, "priority": 40,
        "owns": ["research/humanoids/**", "progress/reg-decision-packet.md"],
        "gate": "python research/humanoids/tools/validate_registry.py",
        "needs_scoping": False,
        "note": "Research only. No promotion, universe_size_claim stays null.",
    }], None


def gen_adversarial_findings(cfg, ownership):
    """7. Adversarial escapes without a regression test, and summaries with no provenance.

    Two distinct problems are detected here:

    a) an escape recorded in a *-summary.json whose id appears in no test;
    b) a summary file carrying counts but no provenance. postmerge-summary.json
       on main holds `total_results: 63012, escapes: []` with no commit, UTC,
       toolchain or completeness marker in the file itself. Its provenance lives
       only in a sibling markdown, so the machine-readable artefact can be quoted
       with no way to tell which code it tested or whether the run finished.
       That is how a truncated run gets cited as a result.
    """
    rdir = REPO / "research" / "adversarial" / "results"
    if not rdir.exists():
        return [], "research/adversarial/results not found"
    try:
        hard = (REPO / "tests" / "test_adversarial_hardening.py").read_text()
    except OSError:
        hard = ""

    out, seen = [], set()
    required_provenance = ("complete", "commit", "finished_utc", "toolchain", "generator")

    for f in sorted(rdir.glob("*summary*.json")):
        data = read_json(f, {})
        if not isinstance(data, dict):
            continue

        missing = [k for k in required_provenance if k not in data]
        if missing and "total_results" in data:
            nid = f"advprov-{_slug(f.stem)}"
            if nid not in seen:
                seen.add(nid)
                out.append({
                    "id": nid,
                    "title": (f"{f.name} reports total_results={data.get('total_results')} "
                              f"but carries no {', '.join(missing)}. Make the summary "
                              f"self-describing via ops/longrun.py so a count can never "
                              f"be quoted without the run that produced it."),
                    "source": f"generator:adversarial-provenance:{f.name}",
                    "tier": 1, "priority": 4, "model": "mechanical",
                    "owns": ["research/adversarial/**", f"progress/{nid}.md"],
                    "gate": "python -m pytest research/adversarial/tests -q",
                    "needs_scoping": False,
                })

        # Group by defect, not by case. 100 oversize-resource escapes are one
        # defect observed 100 times; filing 100 nodes would inflate throughput
        # while fixing nothing, which is the exact failure this system avoids.
        escapes = data.get("escapes") or []
        if not isinstance(escapes, list):
            continue
        groups = {}
        for esc in escapes:
            if not isinstance(esc, dict):
                continue
            key = (esc.get("class", "unknown"), esc.get("path", "?"), esc.get("kind", "?"))
            groups.setdefault(key, []).append(esc.get("id") or esc.get("case_id"))

        for (cls, path, kind), ids in sorted(groups.items()):
            # A class already named in the hardening suite is covered; the
            # tokens are matched loosely because test names are prose, and a
            # false "covered" here only costs us a node we would have skipped.
            tokens = [t for t in re.split(r"[^a-z0-9]+", str(cls).lower()) if len(t) > 3]
            if tokens and all(t in hard.lower() for t in tokens):
                continue
            nid = f"adv-{_slug(f'{cls}-{path}')}"
            if nid in seen:
                continue
            seen.add(nid)
            out.append({
                "id": nid,
                "title": (f"Adversarial defect class '{cls}' on the {path} path "
                          f"({kind}) has no regression test naming it. "
                          f"{len(ids)} escapes in {f.name}, e.g. {ids[0]}."),
                "source": f"generator:adversarial:{f.name}",
                "tier": 1, "priority": 5, "model": "design",
                "owns": [f"tests/test_adv_{_slug(str(cls))}.py", f"progress/{nid}.md"],
                "gate": f"python -m pytest tests/test_adv_{_slug(str(cls))}.py -q",
                "needs_scoping": False,
                "note": f"{len(ids)} escape records collapse to one defect. "
                        f"Fix the class, do not write one test per case.",
            })
    return out, None


def gen_advisories(cfg, ownership):
    """8. Dependency advisories. A tool that is absent is SKIPPED, never zero."""
    if not shutil.which("cargo"):
        return [], "cargo absent: advisory scan SKIPPED, not zero findings"
    rc, out, err = run(["cargo", "deny", "check", "advisories"], cwd=REPO, timeout=600)
    if rc == 127:
        return [], "cargo-deny absent: advisory scan SKIPPED, not zero findings"
    if rc == 0:
        return [], None
    ids = sorted(set(re.findall(r"(RUSTSEC-\d{4}-\d{4})", out + err)))
    return [{
        "id": f"adv-dep-{_slug(i)}",
        "title": f"Resolve advisory {i}",
        "source": "generator:advisories",
        "tier": 2, "priority": 8,
        "owns": ["Cargo.toml", "Cargo.lock", "deny.toml"],
        "gate": "cargo deny check advisories",
        "needs_scoping": False,
    } for i in ids], None


def gen_flakes(cfg, ownership):
    """9. CI failures on main in the last 50 runs."""
    runs, err = gh_json(["run", "list", "--branch", "main", "--limit", "50",
                         "--json", "conclusion,displayTitle,url"])
    if err:
        return [], f"gh run list failed: {err}"
    bad = [r for r in (runs or []) if r.get("conclusion") not in (None, "success", "skipped")]
    if not bad:
        return [], None
    return [{
        "id": "flake-main-ci",
        "title": f"{len(bad)} of the last 50 main CI runs did not succeed - root cause with captured output",
        "source": "generator:flakes",
        "tier": 1, "priority": 3,
        "owns": ["docs/evidence/flake-main-ci/**", "progress/flake-main-ci.md"],
        "gate": "",
        "needs_scoping": True,
    }], None


GENERATORS = [
    gen_limitations, gen_qip_gaps, gen_handoffs, gen_todos,
    gen_control_path_coverage, gen_registry, gen_adversarial_findings,
    gen_advisories, gen_flakes,
]


def cmd_refill(cfg, ownership, st) -> dict:
    backlog = load_backlog()
    known = {n["id"] for n in backlog} | set(st["nodes"].keys())
    added, skipped = 0, {}

    for gen in GENERATORS:
        try:
            items, skip_reason = gen(cfg, ownership)
        except Exception as e:  # a broken generator must not stop the loop
            items, skip_reason = [], f"{gen.__name__} raised {type(e).__name__}: {e}"
        if skip_reason:
            skipped[gen.__name__] = skip_reason
        for item in items:
            if item["id"] in known:
                continue
            item.setdefault("status", "ready")
            item.setdefault("created_utc", utcnow())
            item.setdefault("attempts", 0)
            backlog.append(item)
            known.add(item["id"])
            added += 1

    st["refill_skipped"] = skipped
    if added:
        save_backlog(backlog)
    ready = [n for n in backlog if n.get("status") == "ready" and not n.get("needs_scoping")]
    log(f"refill: +{added} new, {len(ready)} dispatchable, skipped_generators={len(skipped)}")
    if not ready:
        incident(
            "backlog",
            "Backlog has no dispatchable node. Generators skipped: "
            + json.dumps(skipped)[:800],
        )
    save_state(st)
    return st


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------

PROMPT_TEMPLATE = """# Node {id}

You are one worker in the Quberon build system. You own exactly the paths listed
below and nothing else. Read REPO-MAP.md first.

## Task
{title}

{note}

## Tier {tier}
{tier_rules}

## Owned paths - writing outside these is a failed node, not a judgement call
{owns}

If the task genuinely requires a change outside your owned paths, do not make it.
Append a line to progress/{id}.md of exactly this form and stop:

    handoff: <path> needs <change> because <reason>

## Exit gate
Your node is done only when this exits zero on a clean clone:

    {gate}

plus the universal gate, which ops/gate.sh runs for you: full suite with Rust,
full suite with Rust removed from PATH, both fail-direction tests, and
`import app.main` creating zero files.

A summary line where raw output was requested is a failed gate, not a style note.
You have {budget} minutes and at most {attempts} attempts. After that, report
STATUS: partial with raw diagnostics. Never rewrite the exit criterion to reach it.

## Base
Branch {branch} off {base}. Do not rebase onto a moving main mid-node.

## Report, into progress/{id}.md and as your final message
NODE / TIER / BRANCH / COMMITS / STATUS / CHANGED / EVIDENCE (command, toolchain,
host, UTC, raw output path) / TESTS (both modes) / STILL NOT TRUE / NEEDS A HUMAN
DECISION.

STILL NOT TRUE is mandatory and must be non-empty for any control-path work.
Claim nothing you did not observe. No certification, physical-safety, latency or
regulatory-compliance claim is ever supported by this repository.
"""

TIER_RULES = {
    1: "You may open a PR. The scheduler merges it automatically once the gate passes and CI is green. You do not merge it yourself.",
    2: "Control path. You stop at an open PR. You do not merge, under any circumstance, even if CI is green and the change looks obviously correct.",
    3: "You prepare only. You do not execute. No credential use, no deployment, no spend, no physical device write, no public claim.",
}


def cmd_dispatch(cfg, ownership, st) -> dict:
    if halted():
        log("dispatch: HALT present")
        return st
    if st.get("main_red"):
        log("dispatch: main CI is red; only a fix node may run")
        return st

    running = {k: v for k, v in st["nodes"].items() if v.get("status") in ("running", "gating")}
    free = cfg["max_slots"] - len(running)
    if free <= 0:
        log(f"dispatch: {len(running)}/{cfg['max_slots']} slots busy")
        return st

    backlog = load_backlog()
    candidates = [n for n in backlog
                  if n.get("status") == "ready"
                  and not n.get("needs_scoping")
                  and n.get("owns")]
    candidates.sort(key=lambda n: (n.get("priority", 50), n.get("tier", 1), n["id"]))

    claimed = [v["owns"] for v in running.values()]

    for node in candidates:
        if free <= 0:
            break

        if node.get("tier", 1) >= 3 and not node.get("approved_by_human"):
            continue
        if node.get("tier", 1) >= 2 and not node.get("approved_by_human"):
            # Tier 2 may be built, but only when a human queued it explicitly.
            continue

        bad = [a for a in reserved_conflicts(node["owns"], ownership)
               if a[1] > node.get("tier", 1)]
        if bad:
            node["status"] = "blocked"
            node["blocked_reason"] = f"claims reserved higher-tier area {bad}"
            continue

        if any(sets_overlap(node["owns"], other) for other in claimed):
            continue  # not a failure; it simply waits for a disjoint slot

        node_id = node["id"]
        branch = cfg["branch_prefix"] + node_id
        tree = WORKTREES / node_id

        git("worktree", "remove", "--force", str(tree))
        if tree.exists():
            shutil.rmtree(tree, ignore_errors=True)
        git("branch", "-D", branch)
        rc, _, err = git("worktree", "add", "-b", branch, str(tree), cfg["default_base"], timeout=600)
        if rc != 0:
            node["status"] = "blocked"
            node["blocked_reason"] = f"worktree add failed: {err[:300]}"
            incident("worktree", f"{node_id}: worktree add failed: {err[:300]}")
            continue

        PROMPTS.mkdir(parents=True, exist_ok=True)
        prompt_path = PROMPTS / f"{node_id}.md"
        tier = node.get("tier", 1)
        atomic_write(prompt_path, PROMPT_TEMPLATE.format(
            id=node_id,
            title=node["title"],
            note=node.get("note", ""),
            tier=tier,
            tier_rules=TIER_RULES.get(tier, TIER_RULES[2]),
            owns="\n".join(f"- {o}" for o in node["owns"]),
            gate=node.get("gate") or "make test",
            budget=cfg["node_budget_minutes"],
            attempts=cfg["node_max_attempts"],
            branch=branch,
            base=cfg["default_base"],
        ))

        model = cfg["models"]["design" if node.get("model") == "design" else "mechanical"]
        NODE_LOGS.mkdir(parents=True, exist_ok=True)
        rc, _, err = run(["bash", str(OPS / "worker.sh"), node_id, str(prompt_path), str(tree), model],
                         timeout=120)
        pid = None
        pidfile = STATE_DIR / "pids" / f"{node_id}.pid"
        if pidfile.exists():
            pid = pidfile.read_text().strip()
        if rc != 0 or not pid:
            node["status"] = "blocked"
            node["blocked_reason"] = f"worker launch failed rc={rc}: {err[:300]}"
            incident("worker", f"{node_id}: worker launch failed rc={rc}: {err[:300]}")
            continue

        node["status"] = "dispatched"
        st["nodes"][node_id] = {
            "id": node_id, "tier": tier, "owns": node["owns"], "branch": branch,
            "status": "running", "pid": pid, "model": model,
            "started_utc": utcnow(), "started_epoch": time.time(),
            "attempts": node.get("attempts", 0) + 1,
            "last_heartbeat_utc": utcnow(), "worktree": str(tree),
        }
        claimed.append(node["owns"])
        free -= 1
        log(f"dispatch: {node_id} tier={tier} pid={pid} model={model}")

    save_backlog(backlog)
    save_state(st)
    return st


# --------------------------------------------------------------------------
# heartbeat / report / status
# --------------------------------------------------------------------------


def cmd_heartbeat(cfg, ownership, st) -> dict:
    st["last_tick_utc"] = utcnow()
    stale = cfg["heartbeat_stale_minutes"] * 60
    for node_id, nd in st["nodes"].items():
        if nd.get("status") != "running":
            continue
        logf = NODE_LOGS / f"{node_id}.log"
        if logf.exists():
            age = time.time() - logf.stat().st_mtime
            nd["log_age_s"] = int(age)
            if age > stale and pid_alive(nd.get("pid")):
                nd["silent"] = True
                incident("silent-node",
                         f"{node_id} produced no output for {int(age/60)} minutes (pid {nd.get('pid')} alive)")
            else:
                nd["silent"] = False
    save_state(st)
    return st


def cmd_report(cfg, ownership, st) -> dict:
    lines = [f"# Quberon build report", "", f"Generated {utcnow()} by ops/schedule.py (no reasoning; pure reduction).", ""]
    r = st.get("remote", {})
    lines += [f"- origin/main: `{r.get('main')}`",
              f"- open PRs: {len(r.get('open_prs', []))}",
              f"- main CI: {(r.get('main_ci') or {}).get('conclusion')}",
              f"- last tick: {st.get('last_tick_utc')}",
              f"- HALT: {'PRESENT' if halted() else 'absent'}", ""]

    buckets = {}
    for nd in st["nodes"].values():
        buckets.setdefault(nd.get("status", "unknown"), []).append(nd)

    for status in ("running", "awaiting_human", "awaiting_ci", "awaiting_pr", "blocked",
                   "partial", "merge_failed", "over_budget", "merged"):
        items = buckets.get(status, [])
        if not items:
            continue
        lines.append(f"## {status} ({len(items)})")
        for nd in sorted(items, key=lambda n: n["id"]):
            extra = nd.get("blocked_reason", "")
            pr = f" PR #{nd['pr']}" if nd.get("pr") else ""
            lines.append(f"- `{nd['id']}` tier {nd.get('effective_tier', nd.get('tier'))}{pr} {extra}")
        lines.append("")

    skipped = st.get("refill_skipped") or {}
    if skipped:
        lines.append("## Generators that could not run")
        lines.append("")
        lines.append("A skipped generator is not zero findings.")
        lines.append("")
        for k, v in skipped.items():
            lines.append(f"- `{k}`: {v}")
        lines.append("")

    atomic_write(STATE_DIR / "REPORT.md", "\n".join(lines) + "\n")
    log(f"report: {STATE_DIR / 'REPORT.md'}")
    return st


def cmd_status(cfg, ownership, st) -> dict:
    cmd_report(cfg, ownership, st)
    print((STATE_DIR / "REPORT.md").read_text())
    return st


# --------------------------------------------------------------------------

COMMANDS = {
    "reconcile": cmd_reconcile, "harvest": cmd_harvest, "refill": cmd_refill,
    "dispatch": cmd_dispatch, "heartbeat": cmd_heartbeat, "report": cmd_report,
    "status": cmd_status,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=sorted(COMMANDS))
    args = ap.parse_args()

    for d in (STATE_DIR, WORKTREES, PROMPTS, NODE_LOGS, STATE_DIR / "pids"):
        d.mkdir(parents=True, exist_ok=True)

    if halted() and args.command in ("dispatch", "refill"):
        log(f"{args.command}: HALT present, skipping")
        return 0

    cfg, ownership, st = load_config(), load_ownership(), load_state()
    st = COMMANDS[args.command](cfg, ownership, st)
    save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
