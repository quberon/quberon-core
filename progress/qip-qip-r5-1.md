# qip-qip-r5-1 — QIP-R5.1 restart persistence (INTERVENE)

NODE: qip-qip-r5-1 (QIP-R5.1, INTERVENE)
TIER: 1
BRANCH: node/qip-qip-r5-1 (off origin/main 7fd9ea5; not rebased mid-node)
COMMITS: see final message / PR (this file is committed with the change)
STATUS: conformance trace supplied; QIP traceability amendment NOT done (not this node's to do)

## What was traced, and to what

QIP-v0.1 Section 11 (docs/specs/intervention-profile/QIP-v0.1.md:309) read:
  QIP-R5.1 | INTERVENE | UNIMPLEMENTED (restart persistence not in N4)

Added, in conformance/** only (append-only ID, no renumbering):
- conformance/test_conformance.py::test_QIP_LATCH_04_stop_latch_persists_across_restart
  (new stable ID QIP-LATCH-04, appended after QIP-LATCH-01..03)
- conformance/adapter_interface.py: neutral AdapterUnderTest.restart()
  plus `restartable` capability, False by default. A False capability
  yields skip = NOT TESTED, never a pass (same rule as QIP-DEG-03
  injection capabilities).
- conformance/quberon_adapter.py: restart() = new app instance on the
  same durable SQLite DB (the simulator's restart surface), clients
  rebuilt/re-authenticated; `_build()` factored out of `__init__`.
  No app/control-path code was changed.
- conformance/README.md: restart semantics + explicit limits (below).

Non-vacuity (why this is not the weak existing project test):
quberon-core's fresh-start default is itself latched, so "STOP,
restart, still latched" could pass against a fresh DB. QIP-LATCH-04
therefore requires the secure core, first reaches the non-default
UNLATCHED state via admin reset, restarts and asserts still unlatched
(proving restart re-reads durable state, not defaults), then STOPs,
restarts, and asserts latch retained, observed SIMULATED_STOPPED,
and task refused (409) while latched. Without the Rust core it skips.

## EVIDENCE

Host: Darwin Mac 24.3.0 arm64 (macOS 15.3.1)
Toolchain: Python 3.11.15 (.venv from requirements.txt), cargo/rustc
  1.99.1 (Homebrew), Rust core built with `cargo build --workspace`
UTC runs: 2026-11-06 16:08 UTC (directory/date in raw logs)
Raw output paths (scratch, not repo):
  /Users/quberon1/.hermes/cache/scratch/qip-r5-1/with-rust-conformance.log
  /Users/quberon1/.hermes/cache/scratch/qip-r5-1/without-core-conformance.log
  /Users/quberon1/.hermes/cache/scratch/qip-r5-1/full-with-rust.log
  /Users/quberon1/.hermes/cache/scratch/qip-r5-1/full-rust-removed-from-path.log
  /Users/quberon1/.hermes/cache/scratch/qip-r5-1/full-no-binary.log
Raw output (verbatim tails, not summaries):

With Rust, conformance (`.venv/bin/python -m pytest conformance/ -q -rs`, exit 0):
  .............................                                            [100%]
  29 passed, 1 warning in 4.49s
  (baseline before this change: 28 passed; the +1 is QIP-LATCH-04.
   Standalone QIP-LATCH-04: `1 passed, 1 warning in 0.44s`)

Without core binary, conformance (binary moved aside /
QUBERON_SECURE_CORE_BIN=/nonexistent, exit 0):
  ...............ss............                                            [100%]
  SKIPPED [2] conformance/test_conformance.py:23: NOT TESTED in this run: secure-core binary unavailable, so the authorized reset path cannot be exercised
  27 passed, 2 skipped, 1 warning in 3.73s
  (the 2 skips are QIP-LATCH-03 and QIP-LATCH-04: NOT TESTED, not passes)

Full suite with Rust (`.venv/bin/python -m pytest -q`, exit 0):
  212 passed, 2 warnings in 39.65s

Full suite with Rust removed from PATH (`PATH=/usr/bin:/bin
.venv/bin/python -m pytest -q -rs`; built binary still on disk, exit 0):
  212 passed, 2 warnings in 38.94s

Full suite with the secure-core binary actually removed (binary moved
aside, then restored; exit 0):
  199 passed, 13 skipped, 2 warnings in 37.13s
  (13 skips include QIP-LATCH-03/04, 3x tests/test_app.py, 8x
   tests/test_secure_core.py, all "Rust CLI not built")

Note: pointing QUBERON_SECURE_CORE_BIN at /nonexistent for the FULL
suite gives 6 failed / 204 passed / 2 skipped — that is an artefact
of test_secure_core tests guarding on the on-disk binary, not on the
env override, and is not either gate mode; it is recorded here only
so nobody re-runs that probe expecting a gate result.

import side-effect check (empty scratch cwd + HOME, exit 0):
  $ PYTHONPATH=<repo> HOME=<scratch/importcheck> .venv/bin/python -c "import app.main; print('import ok')"
  import ok
  zero new files   (before/after `find . -type f` diff was empty)

Both fail-direction tests in-suite (QIP-DEG-01 unavailable vs
QIP-DEG-03 reachable refusal / persistence-degraded) pass in the
29-passed run above; no fail-direction behaviour was changed.

Exit gate: `python -m pytest conformance/ -q` exits 0 in both modes
above (29 passed with Rust; 27 passed, 2 skipped without the binary).

## TESTS (both modes)
- With Rust: conformance 29 passed; full 212 passed.
- Without Rust/binary: conformance 27 passed, 2 skipped (NOT TESTED);
  full 199 passed, 13 skipped (NOT TESTED). Skips are never passes.

## CHANGED
- conformance/adapter_interface.py (restart() + restartable capability)
- conformance/quberon_adapter.py (_build() factor-out, restart())
- conformance/test_conformance.py (QIP-LATCH-04 appended; header 01..04)
- conformance/README.md (restart semantics and NOT TESTED limits)
- progress/qip-qip-r5-1.md (this file)
Nothing outside owned paths was modified. In particular
docs/specs/intervention-profile/QIP-v0.1.md Section 11 is untouched.

## STILL NOT TRUE (mandatory, non-empty)
- QIP-R5.1 is still UNIMPLEMENTED in QIP-v0.1 Section 11. This node
  supplied a passing conformance identifier (QIP-LATCH-04); it did not
  and may not amend QIP traceability. The row becomes a trace only if
  the profile owner runs the Section 11 amendment procedure (fetch,
  rebase, grep merged tree + raw output, amend) and merges it.
- QIP-LATCH-04 restart is a new in-process app instance on the same
  SQLite file — not an OS process kill/restart, host reboot, power
  loss, or restart/reconnect against a real/manufacturer controller.
- Restart recovery from either QIP-DEG-03 degraded state (real
  persistence failure, real Rust-core rejection) remains NOT TESTED.
- Without the Rust binary QIP-LATCH-04 is NOT TESTED (skip), so no
  restart-persistence claim exists for no-Rust runs.
- No QIP class (OBSERVE/INTERVENE/AUTHORIZE/EVIDENCE) is claimed.
  No certification, physical-safety, latency, real-time, or
  regulatory-compliance claim is supported by this repository or
  by this test; SIMULATED_STOPPED is simulator vocabulary only.

## NEEDS A HUMAN DECISION
- Profile owner: whether to amend QIP-v0.1 Section 11 QIP-R5.1 from
  UNIMPLEMENTED to QIP-LATCH-04 via the Section 11 procedure,
  accepting the in-process/SQLite restart scope above (a real
  process/controller restart test would need work outside
  conformance/** and is a separate node if wanted).
