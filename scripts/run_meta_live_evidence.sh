#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

missing=()
for name in META_API_URL META_API_KEY META_MODEL; do
  if [[ -z "${!name:-}" ]]; then
    missing+=("$name")
  fi
done

if (( ${#missing[@]} )); then
  printf 'BLOCKED: missing application environment variable(s): %s\n' "${missing[*]}" >&2
  printf 'Copy .env.example to .env, fill it locally, and rerun. No provider call was made.\n' >&2
  exit 2
fi

PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if [[ -x .venv/bin/python ]]; then
    PYTHON=.venv/bin/python
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
  else
    printf 'BLOCKED: Python interpreter not found. No provider call was made.\n' >&2
    exit 2
  fi
fi

printf 'Application credentials present by name. Running exactly one advisory planning call.\n'
exec "$PYTHON" scripts/meta_live_evidence.py --output docs/evidence/meta-live.md
