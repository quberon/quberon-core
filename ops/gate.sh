#!/bin/bash
# The only thing that may mark a node done.
#
#   ops/gate.sh <node-id> <branch> [node-gate-command]
#
# Clean-clones the branch into a throwaway directory, runs the node's own gate
# command plus the universal gate, and writes every raw log, toolchain version,
# host and UTC timestamp into docs/evidence/<node-id>/ on the branch.
#
# Exit 0 only if everything passed. A summary line where raw output was
# requested is a failed gate, not a style note.

set -uo pipefail

NODE_ID="${1:?usage: gate.sh <node-id> <branch> [gate-command]}"
BRANCH="${2:?usage: gate.sh <node-id> <branch> [gate-command]}"
NODE_GATE="${3:-}"

REPO="${QUBERON_REPO:-$HOME/quberon-core}"
OPS="$REPO/ops"
PY="${QUBERON_PYTHON:-python3}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/quberon-gate-${NODE_ID}-XXXXXX")"
CLONE="$WORK/clone"
EV="$WORK/evidence"
mkdir -p "$EV"

FAILED=0
say() { printf '%s [gate:%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$NODE_ID" "$*"; }
fail() { say "FAIL: $*"; FAILED=1; }

cleanup() {
  if [ "${QUBERON_GATE_KEEP:-0}" = "1" ]; then
    say "work dir kept at $WORK"
  else
    rm -rf "$WORK"
  fi
}
trap cleanup EXIT

# --- Clean clone. Never reuse the worker's tree: it hides uncommitted state. --
say "clean-cloning $BRANCH"
if ! git clone --quiet --branch "$BRANCH" "file://$REPO" "$CLONE" 2>"$EV/clone.log"; then
  cat "$EV/clone.log"
  say "FAIL: clean clone of $BRANCH failed"
  exit 1
fi
cd "$CLONE" || exit 1
COMMIT="$(git rev-parse HEAD)"

# --- Record the environment exactly, not approximately. ----------------------
{
  echo "node_id=$NODE_ID"
  echo "branch=$BRANCH"
  echo "commit=$COMMIT"
  echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host=$(hostname)"
  echo "uname=$(uname -a)"
  echo "python=$($PY --version 2>&1)"
  echo "python_path=$(command -v "$PY")"
  echo "cargo=$(command -v cargo >/dev/null 2>&1 && cargo --version || echo ABSENT)"
  echo "rustc=$(command -v rustc >/dev/null 2>&1 && rustc --version || echo ABSENT)"
  echo "make=$(command -v make >/dev/null 2>&1 && make --version | head -1 || echo ABSENT)"
} > "$EV/environment.txt"
say "commit $COMMIT"

# --- 1. Universal gate: full suite WITH Rust. --------------------------------
say "universal gate 1/4: full suite with Rust"
if make setup > "$EV/with-rust-setup.log" 2>&1; then
  if ! make test > "$EV/with-rust-test.log" 2>&1; then
    fail "full suite with Rust"
  fi
else
  fail "make setup (with Rust)"
fi
if command -v cargo >/dev/null 2>&1; then
  if ! cargo test --workspace --all-features --locked > "$EV/with-rust-cargo.log" 2>&1; then
    fail "cargo test --workspace"
  fi
else
  echo "cargo ABSENT on this host: Rust-mode gate NOT RUN (this is a skipped check, not a pass)" \
    > "$EV/with-rust-cargo.log"
  fail "cargo absent: the with-Rust mode could not be verified on this host"
fi

# --- 2. Universal gate: full suite WITHOUT Rust. -----------------------------
# Rust removed from PATH and the built CLI hidden, so the degraded path is
# genuinely degraded rather than accidentally finding a binary.
say "universal gate 2/4: full suite without Rust"
NORUST_PATH="$(echo "$PATH" | tr ':' '\n' | grep -v -E '(cargo|rustup|\.rustup)' | paste -sd: -)"
( rm -rf target/debug/quberon-secure-core-cli target/release/quberon-secure-core-cli 2>/dev/null
  rm -rf .venv
  env -u QUBERON_SECURE_CORE_BIN PATH="$NORUST_PATH" bash -c 'make setup && make test'
) > "$EV/without-rust.log" 2>&1 || fail "full suite without Rust"

# --- 3. Universal gate: the two fail-direction tests, named explicitly. ------
# These encode the asymmetry that is the whole safety argument: an unreachable
# core must not block a STOP, and a reachable core that refuses must.
say "universal gate 3/4: fail-direction tests"
for t in \
  "tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not" \
  "tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter"
do
  if ! .venv/bin/python -m pytest "$t" -q >> "$EV/fail-direction.log" 2>&1; then
    fail "fail-direction test $t"
  fi
done

# --- 4. Universal gate: importing the app must create no files. --------------
say "universal gate 4/4: import side effects"
.venv/bin/python - > "$EV/import-side-effects.log" 2>&1 <<'PYEOF'
import os, sys, tempfile, pathlib
probe = pathlib.Path(tempfile.mkdtemp(prefix="quberon-import-probe-"))
os.environ["TMPDIR"] = str(probe)
before = set(probe.rglob("*"))
import app.main  # noqa: F401
after = set(probe.rglob("*"))
created = sorted(str(p) for p in (after - before))
print("created:", created)
sys.exit(1 if created else 0)
PYEOF
[ $? -eq 0 ] || fail "importing app.main created files (N2 lifecycle invariant)"

# --- 5. The node's own gate command. -----------------------------------------
if [ -n "$NODE_GATE" ]; then
  say "node gate: $NODE_GATE"
  echo "\$ $NODE_GATE" > "$EV/node-gate.log"
  ( export PATH="$CLONE/.venv/bin:$PATH"; eval "$NODE_GATE" ) >> "$EV/node-gate.log" 2>&1 \
    || fail "node gate command"
else
  echo "no node-specific gate command declared" > "$EV/node-gate.log"
fi

# --- 6. Publish the raw evidence onto the branch. ----------------------------
# Evidence that is not committed does not exist.
DEST="docs/evidence/$NODE_ID"
mkdir -p "$DEST"
cp "$EV"/*.log "$EV"/environment.txt "$DEST"/ 2>/dev/null
{
  echo "# Gate evidence: $NODE_ID"
  echo
  echo "- commit: \`$COMMIT\`"
  echo "- branch: \`$BRANCH\`"
  echo "- UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- host: $(hostname), $(uname -sr)"
  echo "- result: $([ "$FAILED" -eq 0 ] && echo PASS || echo FAIL)"
  echo
  echo "Raw logs in this directory are the evidence; this file is only an index."
  echo "A skipped check is recorded as skipped and is never a pass."
} > "$DEST/README.md"

git add "$DEST" >/dev/null 2>&1
if ! git diff --cached --quiet 2>/dev/null; then
  git -c user.name="quberon-gate" -c user.email="gate@quberon.local" \
      commit -q -m "docs(evidence): gate run for $NODE_ID at $STAMP"
  git push --quiet origin "HEAD:$BRANCH" 2>>"$EV/push.log" || say "WARN: evidence push failed"
fi

if [ "$FAILED" -eq 0 ]; then
  say "PASS"
else
  say "FAILED; evidence under $DEST"
fi
exit "$FAILED"
