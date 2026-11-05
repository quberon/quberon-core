# F1-degraded-conformance — progress (Wave 5, Tier 1)

Node: Wave5 F1 | Owns: conformance/** and progress/F1-degraded-conformance.md only
Base: origin/main 35ee2aef6f7a2fcf17e51de40678aee97ba0b350
Gate sources: docs/specs/GRAPH-HARNESS.md, docs/specs/intervention-profile/
QIP-v0.1.md (QIP-R7.1/R7.4 traced to QIP-DEG-03, previously UNIMPLEMENTED
because DEG-03 was skipped), graph.md R-IMM-1/R-IMM-2, progress.md.
Attempts: 1 of 3 used (attempt 1: DEG-03 passed on first run; no gate
weakened, no app/control-path file edited).

## Question and answer

Could the neutral interface express (a) persistence-degraded and
(b) secure-core reachable-refusal? The app already distinguishes both
states; AdapterUnderTest simply had no way to REACH them. Proof from
read-only inspection of app/main.py (not edited):
- persistence: Store/SQLite-error paths set persistence_ok=False; the
  stop/task/reset handlers then refuse 503, latch retained.
- refusal: execute_stop treats SecureCoreUnavailable as unsigned
  (200/ACKNOWLEDGED, DEG-01) but any other SecureCoreError (incl.
  SecureCoreRejected) as reachable refusal: 503, command/observed
  UNKNOWN, latch retained, adapter not invoked, audit
  auth_result="secure_core_rejected".
So the interface was extended within conformance/** only, rather than
declaring the states inexpressible.

## Deliverable

- conformance/adapter_interface.py: two implementation-neutral injection
  points (inject_persistence_failure, inject_secure_core_refusal) that
  name states, not mechanisms, plus capabilities
  persistence_failure_injectable / secure_core_refusal_injectable
  (default False + NotImplementedError: cannot inject = NOT TESTED,
  never a pass). No IDs renumbered; QIP-DEG-03 keeps its name/ID.
- conformance/quberon_adapter.py: persistence injection sets the same
  persistence_ok=False flag app.main's own degraded paths set; refusal
  injection installs a reachable stub authority raising the app's
  existing SecureCoreRejected (code REFUSED_CONFORMANCE_INJECTION).
  Conformance-side only: no app/**, integrations/**, or control-path edit.
- conformance/conftest.py: adapter_persistence_degraded and
  adapter_refusing_core fixtures applying the neutral injections.
- conformance/test_conformance.py: QIP-DEG-03 un-skipped. Asserts:
  persistence-degraded -> status persistence_ok False, stop_latched
  True, observed UNKNOWN, stop/task/reset all 503, latch retained;
  reachable refusal -> stop 503, secure_core_status "rejected",
  command/observed UNKNOWN, stop_latched True, status UNKNOWN/latched,
  exactly one audit event with auth_result "secure_core_rejected".
- conformance/README.md: injection section; DEG-03 removed from
  NOT TESTED and replaced with its injection limits (below).

## Exact results (this branch, Rust core built)

Command: .venv/bin/python -m pytest conformance/test_conformance.py::test_QIP_DEG_03_persistence_failure_and_reachable_refusal -q -rs
Raw: 1 passed, 1 warning in 0.30s

Command: cargo build --workspace; .venv/bin/python -m pytest conformance/ -q -rs
Raw: 28 passed, 1 warning in 4.80s  (was 27 passed, 1 skipped at base)

Command: .venv/bin/python -m pytest -q   (make test equivalent, full repo)
Raw: 144 passed, 2 warnings in 31.22s

Negative control (deterministic, code not model): a no-core adapter
WITHOUT injection reports persistence_ok True and STOP
200/ACKNOWLEDGED/secure_core_status "unavailable" -- i.e. DEG-03's
503/"rejected"/persistence_ok-False assertions fail without injection,
so the pass is caused by the injected states, not by ambient behaviour.

Clean-clone-style verification: see "Verification" below (filled from a
fresh clone of the pushed branch before merge).

## Class verdict change (only this row changes)

| Class | IDs | Before | After |
|---|---|---|---|
| DEGRADED | QIP-DEG-01..03 | 2/3, DEG-03 NOT TESTED (skipped) | 3/3 in this run (28 passed, 0 skipped with core built) |

This supports (does not by itself amend) QIP-v0.1 QIP-R7.1/QIP-R7.4,
which stay UNIMPLEMENTED in docs/specs/intervention-profile/QIP-v0.1.md
until that document's own amendment procedure is run by its owner;
F1 does not edit it. This is NOT standards conformance (R11).

## NOT TESTED (explicit gaps — remain gaps)

- Real disk/SQLite persistence failure and restart recovery from it:
  injection flips the app's degraded flag, it does not corrupt storage.
- Real Rust secure-core rejection of a signed envelope, signed-
  attestation verification, sequence/epoch handling under refusal:
  injection uses a stub authority; no signing is exercised.
- Adapter non-invocation under refusal is observed via UNKNOWN /
  latch / audit outcomes, not via an invocation counter on a real adapter.
- Any real manufacturer interface/mapping, capability negotiation (R10).
- Physical stopping/response time, load/starvation, network partition,
  real-controller restart/reconnect, physical reset.
- Independent physical-state sensing, observation latency; audit
  retention/clock trust/export/custody; recognizer qualification;
  standards/PL/SIL/hazard/legal conformity (R11).
- Without the Rust binary, QIP-LATCH-03 still skips (NOT TESTED in
  that run); DEG-03 itself does not need the binary.

## Verification (filled with raw output before merge)

- Local: 28 passed conformance (core built); 144 passed full. See above.
- Clean-clone-style: PENDING at first commit; filled before merge.
- CI: must be green before merge; no claim ahead of that evidence.
