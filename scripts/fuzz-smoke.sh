#!/bin/sh
# Bounded fuzz smoke test. Honest contract:
#   exit 0  - cargo-fuzz was available and the bounded run completed
#   exit 77 - cargo-fuzz / nightly toolchain unavailable (NOT a fuzz pass;
#             CI must surface this, and the proptest suite remains the
#             executable evidence on stable)
# Usage: scripts/fuzz-smoke.sh [seconds-per-target]
set -u
SECONDS_PER_TARGET="${1:-30}"
if ! command -v cargo-fuzz >/dev/null 2>&1 && ! cargo fuzz --version >/dev/null 2>&1; then
  echo "FUZZ NOT RUN: cargo-fuzz unavailable on this toolchain (exit 77)"
  exit 77
fi
cd "$(dirname "$0")/../fuzz"
for target in envelope_parse audit_record; do
  echo "fuzzing $target for ${SECONDS_PER_TARGET}s"
  cargo fuzz run "$target" -- "-max_total_time=$SECONDS_PER_TARGET" || exit 1
done
echo "fuzz smoke complete"
