#!/usr/bin/env python3
"""Daily spend ceiling for the autonomous build system.

An autonomous loop without a ceiling is an open tap. This is the tap handle.

    ops/budget.py --check                    exit 0 under ceiling, 2 over
    ops/budget.py --add --node X --tokens N --usd 1.23
    ops/budget.py --show                     today's ledger as JSON
    ops/budget.py --history 7                last 7 days, one line each

The ledger is append-only per day and lives in $QUBERON_STATE/budget/, outside
the repository, so it never dirties a worktree or leaks into a clean-clone gate.

Ceilings come from ops/config.json -> budget.daily_usd_ceiling and
budget.daily_token_ceiling. A missing config is a hard stop, not a default:
guessing a spending limit is exactly the wrong thing to be relaxed about.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(os.environ.get("QUBERON_REPO", str(Path.home() / "quberon-core"))).resolve()

if sys.platform == "darwin":
    _default_state = Path.home() / "Library" / "Application Support" / "Quberon"
else:
    _default_state = Path.home() / ".local" / "state" / "quberon"
STATE_DIR = Path(os.environ.get("QUBERON_STATE", str(_default_state)))
BUDGET_DIR = STATE_DIR / "budget"


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def ledger_path(day: str = None) -> Path:
    return BUDGET_DIR / f"{day or today()}.json"


def load_ledger(day: str = None) -> dict:
    p = ledger_path(day)
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"day": day or today(), "usd": 0.0, "tokens": 0, "entries": []}


def ceilings() -> dict:
    cfg_path = REPO / "ops" / "config.json"
    try:
        cfg = json.loads(cfg_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"budget: cannot read {cfg_path}: {e}", file=sys.stderr)
        print("budget: refusing to assume a spending ceiling", file=sys.stderr)
        sys.exit(3)
    b = cfg.get("budget") or {}
    if "daily_usd_ceiling" not in b and "daily_token_ceiling" not in b:
        print("budget: config has no ceiling defined; refusing to run unbounded", file=sys.stderr)
        sys.exit(3)
    return {
        "usd": float(b.get("daily_usd_ceiling", float("inf"))),
        "tokens": int(b.get("daily_token_ceiling", sys.maxsize)),
        "on_exhausted": b.get("on_exhausted", "halt_dispatch"),
    }


def cmd_check() -> int:
    cap, led = ceilings(), load_ledger()
    over = []
    if led["usd"] >= cap["usd"]:
        over.append(f"usd {led['usd']:.2f} >= {cap['usd']:.2f}")
    if led["tokens"] >= cap["tokens"]:
        over.append(f"tokens {led['tokens']} >= {cap['tokens']}")
    if over:
        print(f"budget: EXHAUSTED for {led['day']} ({'; '.join(over)}); "
              f"dispatch halts until UTC midnight", file=sys.stderr)
        return 2
    print(f"budget: ok {led['day']} usd={led['usd']:.2f}/{cap['usd']:.2f} "
          f"tokens={led['tokens']}/{cap['tokens']}")
    return 0


def cmd_add(node: str, tokens: int, usd: float, model: str) -> int:
    led = load_ledger()
    led["entries"].append({
        "utc": utcnow(), "node": node, "model": model,
        "tokens": int(tokens), "usd": round(float(usd), 6),
    })
    led["tokens"] = sum(int(e.get("tokens", 0)) for e in led["entries"])
    led["usd"] = round(sum(float(e.get("usd", 0.0)) for e in led["entries"]), 6)
    atomic_write_json(ledger_path(), led)
    print(f"budget: recorded node={node} tokens={tokens} usd={usd:.4f} "
          f"-> day total usd={led['usd']:.2f} tokens={led['tokens']}")
    return 0


def cmd_show() -> int:
    print(json.dumps(load_ledger(), indent=2, sort_keys=True))
    return 0


def cmd_history(days: int) -> int:
    cap = ceilings()
    now = datetime.now(timezone.utc)
    for i in range(days):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        led = load_ledger(day)
        flag = "OVER" if (led["usd"] >= cap["usd"] or led["tokens"] >= cap["tokens"]) else "ok"
        print(f"{day}  usd={led['usd']:8.2f}  tokens={led['tokens']:>12}  "
              f"entries={len(led['entries']):>4}  {flag}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--add", action="store_true")
    g.add_argument("--show", action="store_true")
    g.add_argument("--history", type=int, metavar="DAYS")
    ap.add_argument("--node", default="unknown")
    ap.add_argument("--model", default="unknown")
    ap.add_argument("--tokens", type=int, default=0)
    ap.add_argument("--usd", type=float, default=0.0)
    a = ap.parse_args()

    BUDGET_DIR.mkdir(parents=True, exist_ok=True)
    if a.check:
        return cmd_check()
    if a.add:
        return cmd_add(a.node, a.tokens, a.usd, a.model)
    if a.show:
        return cmd_show()
    return cmd_history(a.history)


if __name__ == "__main__":
    sys.exit(main())
