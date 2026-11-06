#!/bin/bash
# Launch one Hermes worker, fully detached.
#
#   ops/worker.sh <node-id> <prompt-file> <worktree> [model]
#
# Detachment is the point. The adversarial rerun died with RC=143 (SIGTERM)
# because it was a child of an agent turn. setsid puts the worker in its own
# session and process group, so neither the supervisor exiting nor a turn
# ending can signal it. caffeinate keeps the Mac awake for its duration;
# without it a Mac Mini sleeps mid-run and you get another truncated log.

set -uo pipefail

NODE_ID="${1:?usage: worker.sh <node-id> <prompt-file> <worktree> [model]}"
PROMPT="${2:?missing prompt file}"
TREE="${3:?missing worktree}"
MODEL="${4:-}"

case "$(uname -s)" in
  Darwin) DEFAULT_STATE="$HOME/Library/Application Support/Quberon" ;;
  *)      DEFAULT_STATE="$HOME/.local/state/quberon" ;;
esac
STATE="${QUBERON_STATE:-$DEFAULT_STATE}"
LOGDIR="${QUBERON_LOGDIR:-$HOME/Library/Logs/quberon}/nodes"
PIDDIR="$STATE/pids"
mkdir -p "$LOGDIR" "$PIDDIR"

LOG="$LOGDIR/$NODE_ID.log"
PIDFILE="$PIDDIR/$NODE_ID.pid"
rm -f "$PIDFILE"

[ -f "$PROMPT" ] || { echo "worker: prompt file not found: $PROMPT" >&2; exit 1; }
[ -d "$TREE" ]   || { echo "worker: worktree not found: $TREE" >&2; exit 1; }

# --- The Hermes invocation. VERIFY THIS BEFORE TRUSTING IT. ------------------
# Requirements the real command must satisfy, each verified and recorded in
# ops/RUNBOOK.md before this system is considered working:
#   1. runs without a TTY and without interactive prompts
#   2. survives its launcher exiting
#   3. returns a meaningful exit code
#   4. accepts the prompt from a file, not argv (prompts are long)
# If Hermes has no non-interactive mode, stop and say so. That changes the
# design and must not be worked around with expect scripts or a fake TTY.
HERMES_BIN="${QUBERON_HERMES_BIN:-hermes}"
if ! command -v "$HERMES_BIN" >/dev/null 2>&1; then
  echo "worker: $HERMES_BIN not on PATH (PATH=$PATH)" >&2
  exit 127
fi

# Detachment preflight. Linux hosts usually ship setsid(1); macOS does not.
# Perl is part of the base macOS install and POSIX::setsid gives the same
# new-session semantics. Fail before claiming a worker started.
if command -v setsid >/dev/null 2>&1; then
  DETACH=(setsid)
elif command -v perl >/dev/null 2>&1; then
  DETACH=(perl -MPOSIX -e 'POSIX::setsid() or die "setsid failed"; exec { $ARGV[0] } @ARGV' --)
else
  echo "worker: no detachment mechanism available (need setsid or perl)" >&2
  exit 127
fi

CMD=("$HERMES_BIN" chat --oneshot --query-file "$PROMPT" --in "$TREE" --provider meta-ai -Q)
[ -n "$MODEL" ] && CMD+=(-m "$MODEL")

{
  echo "=============================================================="
  echo "node:    $NODE_ID"
  echo "model:   ${MODEL:-default}"
  echo "tree:    $TREE"
  echo "prompt:  $PROMPT"
  echo "started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "command: ${CMD[*]}"
  echo "=============================================================="
} >> "$LOG"

cd "$TREE" || exit 1

# "${DETACH[@]}" starts a new session, so no shared process group with the
# supervisor. caffeinate -is: keep the machine awake while this runs.
# The exit code is appended so harvest can tell a crash from a clean finish.
"${DETACH[@]}" nohup bash -c '
  caffeinate -is "$@" >> "'"$LOG"'" 2>&1
  rc=$?
  printf "%s [worker] exit rc=%s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$rc" >> "'"$LOG"'"
  exit $rc
' _ "${CMD[@]}" >> "$LOG" 2>&1 &

WPID=$!
echo "$WPID" > "$PIDFILE"
echo "worker: $NODE_ID started pid=$WPID log=$LOG"
exit 0
