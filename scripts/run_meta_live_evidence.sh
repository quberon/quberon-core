#!/bin/sh
# One-shot live Meta evidence runner (offline-safe wrapper).
#
# Precedence, deliberately:
#   interpreter: $PYTHON (explicit) > .venv/bin/python > python3.11 > python3
#   configuration: the caller's exported environment only. This wrapper
#   sets no META_* defaults, sources no .env file, and never prints the
#   environment or any header/credential. An explicitly exported value
#   therefore always wins over any file or default.
# The Python runner preflights httpx, makes at most one provider call,
# writes sanitized evidence, and exits non-zero when blocked/failed.
# This wrapper preserves that exit code (exec).
set -eu
cd "$(dirname "$0")/.."

if [ -n "${PYTHON:-}" ]; then
    PY="$PYTHON"
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
    PY="python3.11"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    echo "meta-live evidence: BLOCKED / FAILED; no python interpreter found; no provider call was made" >&2
    exit 1
fi

exec "$PY" scripts/meta_live_evidence.py "$@"
