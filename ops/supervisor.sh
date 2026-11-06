#!/bin/bash
# Quberon supervisor tick. Fired by launchd every 120s. Deterministic: this
# script and everything it calls contain no model call. If there is nothing to
# do it exits in under two seconds having spent nothing.
#
# Order matters. Kill switch, then lock, then resources, then budget, then work.

set -uo pipefail

REPO="${QUBERON_REPO:-$HOME/quberon-core}"
OPS="$REPO/ops"

case "$(uname -s)" in
  Darwin) DEFAULT_STATE="$HOME/Library/Application Support/Quberon" ;;
  *)      DEFAULT_STATE="$HOME/.local/state/quberon" ;;
esac
STATE="${QUBERON_STATE:-$DEFAULT_STATE}"
LOGDIR="${QUBERON_LOGDIR:-$HOME/Library/Logs/quberon}"
LOG="$LOGDIR/supervisor.log"
PY="${QUBERON_PYTHON:-python3}"

mkdir -p "$LOGDIR" "$STATE" || exit 1
log() { printf '%s [supervisor] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$LOG"; }

# --- 1. Kill switch. Checked before anything else, always. -------------------
if [ -f "$STATE/HALT" ] || [ -f "$OPS/HALT" ]; then
  log "HALT present; no dispatch this tick"
  exit 0
fi

# --- 2. Single instance. mkdir is atomic; stale locks are reaped. ------------
LOCK="$STATE/supervisor.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  prev=$(cat "$LOCK/pid" 2>/dev/null || echo "")
  if [ -n "$prev" ] && kill -0 "$prev" 2>/dev/null; then
    log "tick skipped: pid $prev still running"
    exit 0
  fi
  log "reaping stale lock (pid=${prev:-none})"
  rm -rf "$LOCK"
  mkdir "$LOCK" 2>/dev/null || { log "cannot acquire lock"; exit 0; }
fi
echo $$ > "$LOCK/pid"
cleanup() { rm -rf "$LOCK"; }
trap cleanup EXIT INT TERM

# --- 3. Environment sanity. launchd gives a minimal PATH; a missing tool ------
#        must look like a missing tool, not like a mysterious code bug.
missing=""
for t in git gh "$PY"; do
  command -v "$t" >/dev/null 2>&1 || missing="$missing $t"
done
if [ -n "$missing" ]; then
  log "FATAL: not on PATH:$missing (PATH=$PATH)"
  bash "$OPS/incident.sh" environment "Supervisor cannot run; missing on PATH:$missing. Check EnvironmentVariables in the launchd plist." 2>/dev/null
  exit 1
fi
if [ ! -d "$REPO/.git" ]; then
  log "FATAL: $REPO is not a git repository"
  exit 1
fi

# --- 4. Resource guards. A perpetual system fills disks. ---------------------
free_gb=$(df -g "$REPO" 2>/dev/null | awk 'NR==2 {print $4}')
min_gb=$("$PY" -c "import json,sys;print(json.load(open('$OPS/config.json')).get('min_free_gb',10))" 2>/dev/null || echo 10)
if [ -n "${free_gb:-}" ] && [ "$free_gb" -lt "$min_gb" ] 2>/dev/null; then
  log "INCIDENT: ${free_gb}GB free, below ${min_gb}GB; dispatch halted"
  bash "$OPS/incident.sh" disk "Only ${free_gb}GB free on the $REPO volume; dispatch halted."
  exit 0
fi

# Log rotation: 50MB, keep 14 days.
if [ -f "$LOG" ]; then
  size=$(stat -f%z "$LOG" 2>/dev/null || stat -c%s "$LOG" 2>/dev/null || echo 0)
  if [ "$size" -gt 52428800 ]; then
    mv "$LOG" "$LOG.$(date -u +%Y%m%dT%H%M%SZ)"
    find "$LOGDIR" -name 'supervisor.log.*' -mtime +14 -delete 2>/dev/null
    log "rotated log at ${size} bytes"
  fi
fi

# --- 5. Spend ceiling. -------------------------------------------------------
if ! "$PY" "$OPS/budget.py" --check >> "$LOG" 2>&1; then
  log "daily budget exhausted; reconciling and reporting only, no dispatch"
  "$PY" "$OPS/schedule.py" reconcile >> "$LOG" 2>&1
  "$PY" "$OPS/schedule.py" harvest   >> "$LOG" 2>&1
  "$PY" "$OPS/schedule.py" heartbeat >> "$LOG" 2>&1
  "$PY" "$OPS/schedule.py" report    >> "$LOG" 2>&1
  exit 0
fi

# --- 6. The cycle. Each step is idempotent and safe to re-run. ---------------
start=$(date +%s)
for step in reconcile harvest refill dispatch heartbeat report; do
  if ! "$PY" "$OPS/schedule.py" "$step" >> "$LOG" 2>&1; then
    rc=$?
    log "step $step exited rc=$rc"
    bash "$OPS/incident.sh" scheduler "schedule.py $step exited rc=$rc; see $LOG"
    break
  fi
done
log "tick complete in $(( $(date +%s) - start ))s"
exit 0
