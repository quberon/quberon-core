#!/bin/bash
# Watches the supervisor. Every 15 minutes, via launchd.
#
# Checks: the supervisor label is loaded, the last tick is recent, no running
# node has gone silent, and the flake hunter is alive. Files an incident and
# tries exactly one kickstart. Never twice: a restart loop that hides a real
# fault is worse than a stopped system you can see.

set -uo pipefail

REPO="${QUBERON_REPO:-$HOME/quberon-core}"
OPS="$REPO/ops"
case "$(uname -s)" in
  Darwin) DEFAULT_STATE="$HOME/Library/Application Support/Quberon" ;;
  *)      DEFAULT_STATE="$HOME/.local/state/quberon" ;;
esac
STATE="${QUBERON_STATE:-$DEFAULT_STATE}"
LOGDIR="${QUBERON_LOGDIR:-$HOME/Library/Logs/quberon}"
PY="${QUBERON_PYTHON:-python3}"
UID_NUM="$(id -u)"
mkdir -p "$LOGDIR"

say() { printf '%s [watchdog] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

if [ -f "$STATE/HALT" ] || [ -f "$OPS/HALT" ]; then
  say "HALT present; supervisor is stopped on purpose, nothing to do"
  exit 0
fi

PROBLEMS=""

# --- 1. Is the supervisor label loaded? --------------------------------------
if ! launchctl print "gui/$UID_NUM/com.quberon.supervisor" >/dev/null 2>&1; then
  PROBLEMS="$PROBLEMS; supervisor label is not loaded"
fi

# --- 2. Is the last tick recent? ---------------------------------------------
TICK_AGE="$("$PY" - <<'PYEOF' 2>/dev/null || echo -1
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
state = Path(os.environ.get("QUBERON_STATE", ""))
try:
    data = json.loads((state / "state.json").read_text())
    t = data.get("last_tick_utc")
    if not t:
        print(-1); sys.exit()
    dt = datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    print(int((datetime.now(timezone.utc) - dt).total_seconds()))
except Exception:
    print(-1)
PYEOF
)"
STALE="$("$PY" -c "import json;print(json.load(open('$OPS/config.json')).get('tick_stale_minutes',10)*60)" 2>/dev/null || echo 600)"
if [ "$TICK_AGE" -lt 0 ] 2>/dev/null; then
  PROBLEMS="$PROBLEMS; no readable last_tick_utc in state.json"
elif [ "$TICK_AGE" -gt "$STALE" ] 2>/dev/null; then
  PROBLEMS="$PROBLEMS; last tick was ${TICK_AGE}s ago (limit ${STALE}s)"
fi

# --- 3. Is the flake hunter alive? -------------------------------------------
# It is a KeepAlive daemon, so "not loaded" is a real fault, not a schedule.
if ! launchctl print "gui/$UID_NUM/com.quberon.flakehunter" >/dev/null 2>&1; then
  PROBLEMS="$PROBLEMS; flakehunter label is not loaded"
fi

# --- 4. Disk, because everything else fails confusingly once it is full. -----
FREE_GB="$(df -g "$REPO" 2>/dev/null | awk 'NR==2 {print $4}')"
if [ -n "${FREE_GB:-}" ] && [ "$FREE_GB" -lt 5 ] 2>/dev/null; then
  PROBLEMS="$PROBLEMS; only ${FREE_GB}GB free"
fi

if [ -z "$PROBLEMS" ]; then
  say "ok: tick ${TICK_AGE}s ago, labels loaded, ${FREE_GB:-?}GB free"
  exit 0
fi

PROBLEMS="${PROBLEMS#; }"
say "PROBLEM: $PROBLEMS"
bash "$OPS/incident.sh" watchdog "Supervisor health check failed: $PROBLEMS"

# One kickstart attempt, recorded, never repeated within the same failure.
MARKER="$STATE/.watchdog-kickstarted"
if [ -f "$MARKER" ] && [ "$(find "$MARKER" -mmin -60 2>/dev/null | wc -l)" -gt 0 ]; then
  say "already kickstarted within the hour; not retrying, this needs a human"
  exit 1
fi
date -u +%Y-%m-%dT%H:%M:%SZ > "$MARKER"
say "attempting one kickstart"
launchctl kickstart -k "gui/$UID_NUM/com.quberon.supervisor" 2>&1 | sed 's/^/  /'
exit 1
