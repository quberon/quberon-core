NODE: qip-3-fail-direction-argument
TIER: 1
BRANCH: node/qip-3-fail-direction-argument
COMMITS: see final message / PR (this file is committed with the artefact)
STATUS: complete

CHANGED:
- docs/specs/intervention-profile/FAIL-DIRECTION.md (new): standalone argued
  artefact for the fail-direction asymmetry. States FDA-1..FDA-6 and a full
  (action x authority-state) decision table: core unavailable -> STOP
  executes unsigned (adapter invoked once, HTTP 200, latch retained, audit
  UNSIGNED/core_unavailable); core rejects -> STOP blocked (adapter not
  invoked, HTTP 503, latch retained, command/observed UNKNOWN, audit
  secure_core_rejected); reset and task always fail closed on
  unavailability (no unsigned reset/task, latch retained). Includes the
  persistence-degraded stricter branch, five counterarguments
  (fail-safe-defaults objection, OCSP soft-fail objection, "blocking a STOP
  is dangerous" objection with the simulation-only scope boundary,
  fail-open-on-rejection objection, complexity objection), a prior-art
  table with PRIOR-ART.md review-depth markers preserved (Saltzer &
  Schroeder 1975; RFC 6960 OCSP good/revoked/unknown; Cloudflare OCSP
  soft/hard-fail; ISO 13850 / ISO 13849-1 / IEC 61508 at
  scope-and-abstract depth only; Regulation (EU) 2023/1230; NIST
  SP 800-207), an explicitly bounded originality claim (novel combination
  within the reviewed set; no worldwide-novelty proof), traceability to
  the two named tests verbatim, falsifiability conditions, and limits.
  Naming collision recorded: this rule is QIP-R7.1-R7.4 / graph.md
  R-IMM-1/R-IMM-2, not QIP-R4 (idempotency) and not GRAPH-HARNESS R4
  (parallelism). No code, test, or existing spec file was changed.
- progress/qip-3-fail-direction.md (this report, owned path)
- progress/qip-3-fail-direction-argument.md (identical report copy at the
  path named in the node brief's Report section)

EVIDENCE:
- command: cargo build --workspace; then
  /tmp/qip3-venv/bin/python -m pytest -q (with Rust);
  target/ moved aside + env PATH=/usr/bin:/bin:/usr/sbin:/sbin
  /tmp/qip3-venv/bin/python -m pytest -q (without Rust/PATH and without
  the built binary); both named fail-direction tests with -v;
  python -m pytest conformance/ -q; import app.main in an empty
  directory with a before/after file listing.
- toolchain: Python 3.11.15 (/tmp/qip3-venv, requirements.txt),
  pytest 8.3.4, cargo 1.99.1 (Homebrew) for the with-Rust mode only.
- host: Quberon1.local (macOS 15.3.1)
- UTC: 2026-11-06T10:52-10:57Z (runs); artefact drafted same session.
- raw output path: /tmp/qip3-evidence/{full-with-rust.log,
  full-without-rust.log,fail-direction-tests.log,conformance-final.log,
  import.log,import-before.txt,import-after.txt} on the build host;
  raw output is also reproduced verbatim below (R-IMM-4).

Raw output — full suite with Rust (cargo build exit 0, then pytest -q):
    ................................................................  [ 34%]
    ................................................................  [ 68%]
    ...................................................................      [100%]
    211 passed, 2 warnings in 44.44s

Raw output — full suite without Rust (PATH stripped, target/ moved aside):
    ...............s................................................  [ 34%]
    .............................................................s.......s.s [ 68%]
    ..........................................ss..ss..ss.ss............      [100%]
    199 passed, 12 skipped, 2 warnings in 41.78s
    (target/ restored afterwards; `which cargo` under the stripped PATH
    exited 1, confirming cargo was not reachable in that mode.)

Raw output — both fail-direction tests (pytest -v):
    tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not PASSED [ 50%]
    tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter PASSED [100%]
    ======================== 2 passed, 1 warning in 0.28s =========================

Raw output — exit gate (python -m pytest conformance/ -q):
    ............................                                      [100%]
    28 passed, 1 warning in 4.35s

Raw output — import inertness (empty cwd, before/after find diff):
    import ok
    IMPORT_ZERO_FILES:OK
    (before list empty; diff produced no output.)

CLEAN-CLONE EXIT GATE:
- git clone of this branch to /tmp/qip3-cleanclone, checkout a7a6094,
  /tmp/qip3-venv/bin/python -m pytest conformance/ -q ->
  raw: "27 passed, 1 skipped, 1 warning in 4.08s", exit 0
  (no Rust binary in the clean clone; the 1 skip is NOT TESTED there).

TESTS (both modes):
- with Rust: full suite 211 passed; conformance 28 passed;
  both fail-direction tests 2 passed (adapter-invocation counts asserted
  inside the tests: unavailable -> stop_calls == 1, reset_calls == 0;
  rejected -> calls == 0, latch true, observed UNKNOWN).
- without Rust: full suite 199 passed, 12 skipped (skips are NOT TESTED
  for the Rust-binary-dependent tests, never counted as passes here);
  the two named fail-direction tests do not require the Rust binary
  (secure_core=None and a stub RejectingCore) and passed in the
  dedicated -v run above.

STILL NOT TRUE:
- No physical-safety, certification, latency, real-time, or
  regulatory-compliance claim is supported by this repository or by
  this artefact. Nothing here was run on a real robot, a real
  manufacturer interface, or real failing storage.
- FDA-2 (blocked STOP on reachable rejection) has not been re-decided
  for any non-simulation use; the artefact states it must be
  re-decided with a deployment risk assessment and qualified assessors
  before any such use.
- Reset/task "fail closed" is an availability-plus-latch gate only:
  the Rust core issues no motion decision (its closed enum represents
  STOP only), so a present-but-would-reject core is not independently
  attested for reset/task. No signed motion authorisation exists.
- The two named tests use a stub RejectingCore and secure_core=None;
  they do not by themselves exercise a real Rust core rejection
  end-to-end, timeout-classified-as-unavailable at the app boundary,
  or latch persistence across restart in the degraded branches.
- Originality is bounded: no reviewed prior-art source states the
  combination, but no exhaustive literature/patent search was done.
- QIP-v0.1.md Section 11 still traces QIP-R7.1/QIP-R7.4 as
  UNIMPLEMENTED (predates Wave 5 F1 QIP-DEG-03); this node did not
  edit that table (see NEEDS A HUMAN DECISION).

NEEDS A HUMAN DECISION:
- Whether to amend QIP-v0.1.md Section 11 to trace QIP-R7.1/QIP-R7.4
  to QIP-DEG-03 (now implemented) — inside this node's owned tree but
  it changes the normative profile's traceability table, so it should
  be its own deliberate change, not folded into this artefact node.
- Whether FDA-1's unsigned STOP remains acceptable policy for any
  future non-simulation deployment, and under what risk assessment.
