# Node qip-qip-r3-3 — QIP-R3.3 (INTERVENE)

NODE: qip-qip-r3-3
TIER: 1
BRANCH: node/qip-qip-r3-3
COMMITS: see git log on this branch (filled at push time; this file is in the same commit it reports, so its own hash cannot be listed inside itself)
STATUS: done — QIP-R3.3 recorded as explicitly untestable via the adapter conformance suite; it remains UNIMPLEMENTED and is NOT traced to any passing test. No QIP traceability table was amended by this node (QIP-v0.1 Section 11 amendment belongs to the profile owner and is outside this node's owned paths).

## Finding

QIP-R3.3 (QIP-v0.1.md Section 6): "Priority handling under this section
is a software scheduling property of this profile only; it MUST NOT be
represented as a real-time or physical stop-time guarantee." At base it
was `UNIMPLEMENTED` with no reason recorded (Section 11, line 305).

It is explicitly untestable via conformance/adapter_interface.py because:

1. Subject mismatch: the requirement constrains representations made
   about the system (docs, UI, reports, claims), not runtime behaviour.
   No AdapterUnderTest operation (status, stop, reset, task, proposal,
   intervene, events, capabilities, fault injections) returns a claim
   or representation about timing guarantees, so there is no neutral
   observable on which a conformance assertion could fail.
2. No threshold: the profile allocates no response-time budget,
   deadline, or stop-time value for R3 (page-one notice), so any
   latency measurement lacks a pass/fail criterion for R3.3. The F3
   loadtest (progress/F3-stop-load.md) is by its own scope R3.1/R3.2
   evidence and explicitly not an R3.3 claim.
3. Partial observables stay partial: absence of a guarantee field in a
   NeutralResult, disclaimers present in in-repo prose, or local timing
   numbers cover only this snapshot and cannot show priority handling
   is never represented as a guarantee elsewhere. Per the node brief,
   partial coverage stays UNIMPLEMENTED and is never rounded up.

Assessment route, if any: human/governance review of claims against
raw output (QIP-R11.1/R11.2 discipline), owned by the profile owner.

## CHANGED

- conformance/test_conformance.py — header note plus unconditional
  skip test `test_QIP_R3_3_priority_must_not_be_represented_as_guarantee`
  whose docstring and skip reason record the untestability above. It
  allocates no stable QIP-* ID and claims no trace.
- conformance/README.md — NOT TESTED section gains an explicit
  QIP-R3.3 EXPLICITLY UNTESTABLE bullet with the same reasoning.
- progress/qip-qip-r3-3.md — this report.

No file outside conformance/** and progress/qip-qip-r3-3.md was changed.
In particular docs/specs/intervention-profile/QIP-v0.1.md Section 11
still reads `QIP-R3.3 | INTERVENE | UNIMPLEMENTED` (verified by grep
before editing; not edited by this node).

## EVIDENCE

Command / toolchain / host / UTC: raw outputs were captured live in
this session on Darwin Quberon1.local 24.3.0 (arm64), Python 3.11.15
(.venv), cargo 1.99.1 (Homebrew), 2026-11-06 ~15:52-15:56 UTC.
Raw output path: this file (verbatim blocks below); the exit-gate
command was run exactly as specified.

Exit gate, with Rust core built (`cargo build --workspace`, finished
successfully), exact command `python -m pytest conformance/ -q`
(run as `.venv/bin/python -m pytest conformance/ -q`):

    ............s................                                            [100%]
    =============================== warnings summary ===============================
    .venv/lib/python3.11/site-packages/starlette/testclient.py:40
      DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated
    -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
    28 passed, 1 skipped, 1 warning in 4.13s

Same command with `-rs`, with Rust core built:

    SKIPPED [1] conformance/test_conformance.py:129: QIP-R3.3 EXPLICITLY UNTESTABLE via adapter conformance: it constrains representations of priority handling, returns no neutral observable, and defines no timing threshold; remains UNIMPLEMENTED (not a trace, not a pass)
    28 passed, 1 skipped, 1 warning in 4.25s

Same command with `-rs`, BEFORE the Rust binary was built (no
target/debug/quberon-secure-core-cli present):

    SKIPPED [1] conformance/test_conformance.py:129: QIP-R3.3 EXPLICITLY UNTESTABLE via adapter conformance: it constrains representations of priority handling, returns no neutral observable, and defines no timing threshold; remains UNIMPLEMENTED (not a trace, not a pass)
    SKIPPED [1] conformance/test_conformance.py:28: NOT TESTED in this run: secure-core binary unavailable, so the authorized reset path cannot be exercised
    27 passed, 2 skipped, 1 warning in 3.71s

Baseline before this node's edits (no Rust binary), same command:
`27 passed, 1 skipped` — the only delta this node adds is the one
explicit R3.3 skip; no previously passing test changed state.

## TESTS (both modes)

- With Rust (`cargo build --workspace` OK):
  - `pytest conformance/ -q` = 28 passed, 1 skipped (raw above).
  - Full suite `pytest -q` = 211 passed, 1 skipped, 2 warnings in 39.44s.
    The sole skip is the new QIP-R3.3 untestable record.
- Without Rust (binary moved aside, PATH=/usr/bin:/bin:/usr/sbin:/sbin):
  - `pytest conformance/ -q -rs` = 27 passed, 2 skipped (raw above;
    second skip is pre-existing QIP-LATCH-03 NOT TESTED without core).
  - Full suite `pytest -q` = 199 passed, 13 skipped, 2 warnings in 36.91s.
  (Binary was restored afterwards; the restored run is the exit-gate
  block above.)
- `import app.main` creating zero files: run from an empty scratch dir
  with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=<repo> printed
  `import ok`; `ls -la` of that dir afterwards showed 0 files.
- Both fail-direction tests are part of the suite runs above
  (QIP-DEG-01/QIP-DEG-02 pass in both modes; QIP-DEG-03 passes with
  the core built and is among the skips counted without it — its state
  was not changed by this node).

## STILL NOT TRUE

- QIP-R3.3 is NOT satisfied, NOT traced, and NOT implemented by this
  node; it remains UNIMPLEMENTED in QIP-v0.1 Section 11. The skip added
  here is a NOT TESTED record, never a pass.
- Nothing here is evidence that any human, document, UI, or downstream
  tool will refrain from representing priority handling as a real-time
  or physical stop-time guarantee; that representation risk is exactly
  what cannot be observed by this suite.
- No latency, deadline, starvation, real-time, physical stop-time,
  certification, physical-safety, or regulatory-compliance claim is
  made or supported. The loadtest numbers in progress/F3-stop-load.md
  remain local Mac simulation observations scoped to R3.1/R3.2.
- QIP-R3.1 and QIP-R3.2 remain UNIMPLEMENTED (out of scope for this node).
- No QIP conformance class (OBSERVE/INTERVENE/AUTHORIZE/EVIDENCE) is claimed.

## NEEDS A HUMAN DECISION

- Profile owner: whether to keep QIP-R3.3 in Section 11 as
  `UNIMPLEMENTED` with a pointer to this explicit-untestable record, or
  to reword/reclassify R3.3 (e.g. as a claim-discipline/governance
  requirement assessed by editorial review rather than conformance
  testing). That amendment must follow QIP-v0.1 Section 11's procedure
  and cannot be made by a work node.
- Profile owner: whether any future claim-review checklist (who reviews
  representations, against which raw output, how often) should exist
  as the human assessment route for R3.3.
