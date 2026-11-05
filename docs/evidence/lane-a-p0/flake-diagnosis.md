# Lane A P0 — flake diagnosis

Date (UTC): 2026-11-05

## Scope and status

The intermittent first-batch failure observed independently at `42b3411`
remains an **open P0 non-determinism** because neither that run nor the agent's
runs captured the failing test name and traceback. It must not be represented
as conclusively closed by later green totals.

## Concrete defect found during Lane A

A separate, concrete state-leak defect was found in
`test_b5_make_demo_prints_exact_degraded_message` (`tests/test_app.py`, around
line 349 at `42b3411`). Before the fix, the test used
`subprocess.run(..., timeout=8)` to launch `make demo`. On timeout Python killed
the direct `make` process, but its Uvicorn child could survive and continue to
hold port 8000. A later invocation could then terminate quickly because it
could not bind that port, creating order-dependent and spuriously fast test
behavior.

The test now launches `make demo` in a new process session and terminates the
whole process group with `SIGTERM`, followed by `SIGKILL` if necessary. The
test itself checks the required degraded-mode message and acts as regression
coverage for child-process cleanup.

## Failing-first evidence

No deterministic failing-first regression test was produced before applying
the process-group cleanup. The defect was inferred from observed runtime and
process/port behavior: an unexpectedly fast subsequent run was consistent with
a surviving Uvicorn process and bind failure. Therefore the cleanup is a
plausible and concrete fix for one identified leak, but it does **not** prove
that it caused the independent `1 failed, 36 passed` batches.

The independent failures reportedly coincided with other suites and
`make demo` processes running on the same Mac, which is compatible with the
orphaned-Uvicorn mechanism. Without the original failing test name and
traceback, attribution remains unproven.

## Evidence after the cleanup

The cleanup test passed repeatedly and port 8000 was observed free after those
runs. Complete suites and clean-clone runs subsequently passed, including the
independent no-Rust verification at `42b3411` on Python 3.12.7 (`37 passed,
11 skipped, 0 failed`). Those are useful non-reproduction results, not proof
that all STOP-path non-determinism has been eliminated.

## Closure criterion

Keep this item open until either:

1. the original failure is reproduced with the exact test name, traceback,
   process list, port ownership, database path, and concurrent workload
   recorded; or
2. a defined stress standard is completed in isolated and concurrent modes,
   with every raw run committed rather than represented only by an aggregate
   summary.

No claim of closure is made here.
