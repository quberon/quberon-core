#!/bin/bash
# File an incident as a GitHub issue.
#
#   ops/incident.sh <kind> <message>
#
# A perpetual system that fails silently at 03:00 is worse than no system.
# Issues are used rather than desktop notifications because a headless Mac
# shows nobody a notification, and because an issue survives a reboot, is
# visible from a phone, and can be closed when resolved.
#
# Deduplicated by title within the last 7 days, so a tick that keeps failing
# comments on one issue instead of opening 500.

set -uo pipefail

KIND="${1:?usage: incident.sh <kind> <message>}"
MESSAGE="${2:-no message}"

REPO="${QUBERON_REPO:-$HOME/quberon-core}"
case "$(uname -s)" in
  Darwin) DEFAULT_STATE="$HOME/Library/Application Support/Quberon" ;;
  *)      DEFAULT_STATE="$HOME/.local/state/quberon" ;;
esac
STATE="${QUBERON_STATE:-$DEFAULT_STATE}"
LOGDIR="${QUBERON_LOGDIR:-$HOME/Library/Logs/quberon}"
FALLBACK="$STATE/incidents.log"
mkdir -p "$STATE" "$LOGDIR"

UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TITLE="[incident:$KIND] ${MESSAGE:0:90}"

# Always record locally first. If gh fails, the incident still exists.
printf '%s\t%s\t%s\n' "$UTC" "$KIND" "$MESSAGE" >> "$FALLBACK"

BODY_FILE="$(mktemp "${TMPDIR:-/tmp}/quberon-incident-XXXXXX.md")"
cleanup() { rm -f "$BODY_FILE"; }
trap cleanup EXIT

{
  echo "Filed automatically by \`ops/incident.sh\`. Nothing here is a claim about the product."
  echo
  echo "| field | value |"
  echo "|---|---|"
  echo "| kind | \`$KIND\` |"
  echo "| UTC | $UTC |"
  echo "| host | $(hostname) |"
  echo "| repo | $REPO |"
  echo
  echo "## Message"
  echo
  echo '```'
  echo "$MESSAGE"
  echo '```'
  echo
  echo "## Supervisor log, last 200 lines"
  echo
  echo '```'
  tail -n 200 "$LOGDIR/supervisor.log" 2>/dev/null || echo "(no supervisor log)"
  echo '```'
  echo
  echo "## Scheduler state"
  echo
  echo '```json'
  tail -c 4000 "$STATE/state.json" 2>/dev/null || echo "(no state.json)"
  echo '```'
} > "$BODY_FILE"

if ! command -v gh >/dev/null 2>&1; then
  echo "incident: gh not on PATH; recorded in $FALLBACK only" >&2
  exit 0
fi

cd "$REPO" || exit 0

# Deduplicate: comment on an open issue with the same title rather than open a
# second one. Matching happens here, in code, not with a search query whose
# tokenizer we would have to trust.
EXISTING="$(gh issue list --state open --label incident --limit 100 \
            --json number,title 2>/dev/null \
            | python3 -c '
import json, sys
try:
    items = json.load(sys.stdin) or []
except Exception:
    items = []
want = sys.argv[1]
print(next((str(i["number"]) for i in items if i.get("title") == want), ""))
' "$TITLE" 2>/dev/null || echo "")"

if [ -n "$EXISTING" ]; then
  gh issue comment "$EXISTING" --body-file "$BODY_FILE" >/dev/null 2>&1 \
    && echo "incident: commented on issue #$EXISTING" \
    || echo "incident: comment failed; recorded in $FALLBACK" >&2
  exit 0
fi

# Ensure the label exists; ignore failure if it already does.
gh label create incident --color B60205 --description "Filed by the build supervisor" >/dev/null 2>&1

if gh issue create --title "$TITLE" --body-file "$BODY_FILE" --label incident >/dev/null 2>&1; then
  echo "incident: issue created: $TITLE"
else
  echo "incident: gh issue create failed; recorded in $FALLBACK" >&2
fi
exit 0
