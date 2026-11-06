#!/usr/bin/env python3
"""Push a new task into the running build system, safely.

This is the answer to "how do I add work without stopping everything".
You do not interrupt the supervisor, restart anything, or message an agent.
You append a validated node to ops/backlog.json and the next tick picks it up.

    ops/add_task.py --id viz-1-evidence-renderers \
        --title "Render committed evidence files into deterministic SVGs" \
        --owns 'viz/**' --owns 'progress/viz-1-evidence-renderers.md' \
        --gate 'python -m pytest viz/tests -q' \
        --priority 12 --model design

    ops/add_task.py --from-file new-tasks.json      # a list of node objects
    ops/add_task.py --list                          # what is queued now
    ops/add_task.py --dry-run ...                   # validate without writing

Validation, all mechanical, all refusals rather than warnings:

  * the id must be unique across the backlog, the running state and the
    ownership areas
  * owns must be non-empty; a node with no declared paths cannot be scheduled
    and cannot be ownership-checked at harvest
  * the declared tier may not be lower than the tier derived from the paths
    themselves, so nobody can label control-path work Tier 1
  * a node may not claim a reserved area of a higher tier
  * Tier 2 and 3 nodes are written with approved_by_human false unless you
    pass --approved, and the scheduler will not dispatch them until then

Overlap with another queued node is reported but allowed: the scheduler
serialises overlapping nodes rather than refusing them.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(__file__).resolve().parent
REPO = Path(os.environ.get("QUBERON_REPO", str(OPS.parent))).resolve()


def _load_schedule():
    spec = importlib.util.spec_from_file_location("quberon_schedule", OPS / "schedule.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate(node: dict, m, ownership: dict, backlog: list, state_ids: set,
             approved: bool) -> list:
    """Return a list of refusal reasons. Empty list means the node is admissible."""
    errs = []

    nid = node.get("id", "")
    if not nid or not nid.replace("-", "").replace("_", "").isalnum():
        errs.append(f"id {nid!r} must be non-empty and alphanumeric with - or _")
    if any(n["id"] == nid for n in backlog):
        errs.append(f"id {nid!r} already in ops/backlog.json")
    if nid in state_ids:
        errs.append(f"id {nid!r} is already a node in the scheduler state")
    if any(a["id"] == nid for a in ownership.get("areas", [])):
        errs.append(f"id {nid!r} collides with an ownership area")

    if not node.get("title"):
        errs.append("title is required: a node without a task statement cannot be worked")

    owns = node.get("owns") or []
    if not owns:
        errs.append("owns must be non-empty; an unowned node cannot be ownership-checked")

    declared = int(node.get("tier", 1))
    if declared not in (1, 2, 3):
        errs.append(f"tier {declared} must be 1, 2 or 3")

    # The paths decide the tier, not the label on the node.
    derived = m.tier_of_paths([o.replace("**", "x").replace("*", "x") for o in owns], ownership)
    if derived > declared:
        errs.append(
            f"declared tier {declared} but the owned paths derive tier {derived}; "
            f"control-path, CI, ops and credential paths cannot be relabelled downward"
        )

    for area_id, area_tier in m.reserved_conflicts(owns, ownership):
        if area_tier > declared:
            errs.append(
                f"claims reserved area {area_id!r} (tier {area_tier}) at tier {declared}; "
                f"that area needs an explicit work order"
            )

    if declared >= 2 and not approved and not node.get("approved_by_human"):
        # Not an error: it is queued but parked. Recorded so the operator knows.
        node["approved_by_human"] = False

    return errs


def overlaps(node: dict, m, backlog: list) -> list:
    out = []
    for other in backlog:
        if other.get("status") not in ("ready", "blocked"):
            continue
        if other.get("owns") and m.sets_overlap(node["owns"], other["owns"]):
            out.append(other["id"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id")
    ap.add_argument("--title")
    ap.add_argument("--owns", action="append", default=[],
                    help="repeatable; git-style glob, ** crosses directories")
    ap.add_argument("--gate", default="", help="command that must exit 0 on a clean clone")
    ap.add_argument("--tier", type=int, default=1)
    ap.add_argument("--priority", type=int, default=50, help="lower runs first")
    ap.add_argument("--model", choices=["mechanical", "design"], default="mechanical")
    ap.add_argument("--note", default="")
    ap.add_argument("--status", default="ready", choices=["ready", "blocked"])
    ap.add_argument("--needs-scoping", action="store_true")
    ap.add_argument("--approved", action="store_true",
                    help="mark a Tier 2/3 node approved for dispatch")
    ap.add_argument("--from-file", help="JSON file containing a list of node objects")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    m = _load_schedule()
    ownership = json.loads((OPS / "ownership.json").read_text())
    backlog_doc = json.loads((OPS / "backlog.json").read_text())
    backlog = backlog_doc["nodes"]

    try:
        state_ids = set(json.loads((m.STATE_FILE).read_text()).get("nodes", {}).keys())
    except Exception:
        state_ids = set()

    if a.list:
        rows = sorted(backlog, key=lambda n: (n.get("priority", 50), n["id"]))
        print(f"{'priority':>8}  {'tier':>4}  {'status':<10} {'appr':<5} id")
        for n in rows:
            appr = "-" if n.get("tier", 1) == 1 else ("yes" if n.get("approved_by_human") else "NO")
            scope = " [needs scoping]" if n.get("needs_scoping") else ""
            print(f"{n.get('priority',50):>8}  {n.get('tier',1):>4}  "
                  f"{n.get('status','?'):<10} {appr:<5} {n['id']}{scope}")
        print(f"\n{len(rows)} nodes queued. Dispatchable now: "
              f"{sum(1 for n in rows if n.get('status')=='ready' and not n.get('needs_scoping') and (n.get('tier',1)==1 or n.get('approved_by_human')))}")
        return 0

    if a.from_file:
        incoming = json.loads(Path(a.from_file).read_text())
        if isinstance(incoming, dict):
            incoming = incoming.get("nodes", [])
    else:
        if not a.id or not a.title:
            ap.error("--id and --title are required unless --from-file or --list is used")
        incoming = [{
            "id": a.id, "title": a.title, "owns": a.owns, "gate": a.gate,
            "tier": a.tier, "priority": a.priority, "model": a.model,
            "status": a.status, "needs_scoping": a.needs_scoping,
            **({"note": a.note} if a.note else {}),
            **({"approved_by_human": True} if a.approved else {}),
        }]

    accepted, rejected = [], []
    for node in incoming:
        node.setdefault("source", "manual:add_task")
        node.setdefault("created_utc", utcnow())
        node.setdefault("attempts", 0)
        node.setdefault("status", "ready")
        node.setdefault("needs_scoping", False)
        if a.approved:
            node["approved_by_human"] = True

        errs = validate(node, m, ownership, backlog + accepted, state_ids, a.approved)
        if errs:
            rejected.append((node.get("id", "<no id>"), errs))
            continue
        accepted.append(node)

    for nid, errs in rejected:
        print(f"REFUSED {nid}", file=sys.stderr)
        for e in errs:
            print(f"    - {e}", file=sys.stderr)

    for node in accepted:
        # Compare against what is queued AND against the other nodes being
        # added right now, or a batch can silently serialise against itself.
        ov = overlaps(node, m, backlog + [n for n in accepted if n is not node])
        tierlabel = f"tier {node.get('tier',1)}"
        if node.get("tier", 1) >= 2 and not node.get("approved_by_human"):
            tierlabel += ", parked until approved"
        print(f"{'WOULD ADD' if a.dry_run else 'ADDED'} {node['id']} ({tierlabel}, "
              f"priority {node.get('priority',50)})")
        for o in node["owns"]:
            print(f"    owns {o}")
        if ov:
            print(f"    serialises behind: {', '.join(ov)}")

    if a.dry_run:
        print("\ndry run: ops/backlog.json unchanged")
        return 1 if rejected else 0

    if accepted:
        backlog.extend(accepted)
        backlog_doc["nodes"] = backlog
        tmp = OPS / "backlog.json.tmp"
        tmp.write_text(json.dumps(backlog_doc, indent=2) + "\n")
        os.replace(tmp, OPS / "backlog.json")
        print(f"\nops/backlog.json now holds {len(backlog)} nodes. "
              f"The next supervisor tick will pick up anything dispatchable; "
              f"nothing needs restarting.")
        print("Commit it: ops/** is Tier 2, so this change goes through a PR.")

    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main())
