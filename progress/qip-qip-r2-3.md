NODE: qip-qip-r2-3
TIER: 1
BRANCH: node/qip-qip-r2-3
COMMITS: see final message / git log on this branch (progress file is committed with the change it reports)
STATUS: complete for the owned-path deliverable; QIP-R2.3 remains UNIMPLEMENTED (not traced)

QUESTION AND VERDICT
QIP-R2.3 (AUTHORIZE): "Application-level authorisation MUST NOT be
represented as a safety-rated authorisation architecture or as
evidence of physical safety." It was UNIMPLEMENTED in QIP-v0.1 Section
11 with no reason recorded.

Verdict: EXPLICITLY UNTESTABLE by this conformance suite. No passing
conformance trace is claimed, and no trace is rounded up from partial
coverage. QIP-AUTH-01 covers QIP-R2.1; QIP-AUTH-02 and QIP-AUTH-04
cover QIP-R2.2 (QIP-v0.1 Section 11). None covers R2.3.

Reason, recorded in conformance/test_conformance.py
(test_QIP_AUTH_05_qip_r2_3_representation_claim_untestable, always
skipped = NOT TESTED) and in conformance/README.md (NOT TESTED):
- R2.3 predicates over representations -- any human-facing claim, in
  any medium, at any time -- not over intervention behaviour
  observable through conformance/adapter_interface.py
  AdapterUnderTest.
- The neutral surface can only sample status, stop, task, proposal,
  intervene and events results. It has no operation that enumerates an
  implementation's documentation, UI text, exports, logs, marketing or
  future representations.
- QIP-v0.1 defines no neutral claim vocabulary / phrase list whose
  absence would decide what counts as a "safety-rated authorisation
  architecture" or "evidence of physical safety"; that classification
  requires human judgement by the profile owner.
- Sampling the quberon binding's payloads for forbidden phrases, or
  asserting its implementation-specific disclaimer fields
  (adapter_mode="SIMULATION", safety_notice, secure-core scope
  "SIMULATION_ONLY_STOP_AUTHORIZATION" in app/main.py), would prove
  only that those sampled payloads carry no such claim today. It would
  still pass while an unsampled representation violated R2.3. That is
  partial coverage, which the node instruction and QIP Section 11
  forbid rounding up to a trace.
- This does not assert quberon makes no such representation anywhere;
  no human claim audit of all representations was performed here.

CHANGED (owned paths only)
- conformance/test_conformance.py: appended stable ID QIP-AUTH-05
  (no renumbering) as an unconditional pytest.skip with the reason
  above; module ID index updated to flag AUTH-05 as an
  explicitly-untestable record, skipped = NOT TESTED, never a trace.
- conformance/README.md: QIP-R2.3 added as the first NOT TESTED entry
  with the same reason and its limits.
- progress/qip-qip-r2-3.md: this file.
No file under docs/specs/intervention-profile/ was edited. This node
does not amend QIP traceability; QIP-R2.3 stays UNIMPLEMENTED in
QIP-v0.1 Section 11. Any amendment follows Section 11's procedure and
belongs to the profile owner.

EVIDENCE
Command / toolchain / host / UTC / raw output path:
- Raw output is embedded verbatim below in this file
  (progress/qip-qip-r2-3.md, section RAW OUTPUT). Scratch copies were
  also written during the run to $TMPDIR/qip-r2-3-evidence/*.log on
  the host below; those scratch files are not repo evidence.
- Host: Darwin Quberon1.local 24.3.0 Darwin Kernel Version 24.3.0:
  Thu Jan 2 20:22:58 PST 2025; root:xnu-11215.81.4~3/RELEASE_ARM64_T8132 arm64
- Python: Python 3.11.15 (.venv from requirements.txt)
- Rust (with-Rust mode): cargo 1.99.1 (5f94df478 2026-08-27) (Homebrew);
  rustc 1.99.1 (58cf8f9c3 2026-10-13) (Homebrew)
- Cargo build: cargo build --workspace -> Finished dev profile in
  4.11s, exit 0; target/debug/quberon-secure-core-cli present.

TESTS (both modes)
With Rust core built:
- .venv/bin/python -m pytest conformance/ -q -rs
  -> 28 passed, 1 skipped (only QIP-AUTH-05 QIP-R2.3 untestable), exit 0
- .venv/bin/python -m pytest -q
  -> 211 passed, 1 skipped, exit 0
Without Rust (cargo removed from PATH and
target/debug/quberon-secure-core-cli moved aside for the run, then
restored):
- PATH=/usr/bin:/bin:/usr/sbin:/sbin .venv/bin/python -m pytest conformance/ -q -rs
  -> 27 passed, 2 skipped (QIP-AUTH-05 untestable; QIP-LATCH-03 NOT
  TESTED: secure-core binary unavailable), exit 0
- PATH=/usr/bin:/bin:/usr/sbin:/sbin .venv/bin/python -m pytest -q
  -> 199 passed, 13 skipped, exit 0
- Fail-direction subset in the same no-Rust run:
  pytest conformance/test_conformance.py -q -rs -k "DEG or STATE_01"
  -> 4 passed, 25 deselected, exit 0
- Named single test:
  pytest conformance/test_conformance.py::test_QIP_AUTH_05_qip_r2_3_representation_claim_untestable -q -rs
  -> 1 skipped, exit 0
- import app.main creating zero files: run in an empty temp dir with
  PYTHONPATH pointing at this worktree -> "import ok",
  files_created:0

RAW OUTPUT
--- with Rust, 2026-11-06T15:02:53Z ---
cargo 1.99.1 (5f94df478 2026-08-27) (Homebrew)
rustc 1.99.1 (58cf8f9c3 2026-10-13) (Homebrew)
........s....................                                            [100%]
=========================== short test summary info ============================
SKIPPED [1] conformance/test_conformance.py:100: NOT TESTED -- QIP-R2.3 explicitly untestable by this suite: representational claim over all human-facing representations, no neutral adapter surface enumerates them and no profile-defined claim vocabulary exists; sampled-payload absence would be partial coverage, not a trace (see README.md NOT TESTED)
28 passed, 1 skipped, 1 warning in 4.62s
conformance_exit:0
........s............................................................... [ 33%]
........................................................................ [ 67%]
....................................................................     [100%]
211 passed, 1 skipped, 2 warnings in 40.82s
full_exit:0

--- without Rust, 2026-11-06T15:03:43Z ---
........s.......s............                                            [100%]
=========================== short test summary info ============================
SKIPPED [1] conformance/test_conformance.py:100: NOT TESTED -- QIP-R2.3 explicitly untestable by this suite: representational claim over all human-facing representations, no neutral adapter surface enumerates them and no profile-defined claim vocabulary exists; sampled-payload absence would be partial coverage, not a trace (see README.md NOT TESTED)
SKIPPED [1] conformance/test_conformance.py:25: NOT TESTED in this run: secure-core binary unavailable, so the authorized reset path cannot be exercised
27 passed, 2 skipped, 1 warning in 4.02s
conformance_exit:0
........s.......s....................................................... [ 33%]
..............................................................s.......s. [ 67%]
s..........................................ss..ss..ss.ss............     [100%]
199 passed, 13 skipped, 2 warnings in 38.17s
full_exit:0
....                                                                     [100%]
4 passed, 25 deselected, 1 warning in 0.70s
fail_direction_exit:0

--- QIP-AUTH-05 alone ---
s                                                                        [100%]
SKIPPED [1] conformance/test_conformance.py:100: NOT TESTED -- QIP-R2.3 explicitly untestable by this suite: representational claim over all human-facing representations, no neutral adapter surface enumerates them and no profile-defined claim vocabulary exists; sampled-payload absence would be partial coverage, not a trace (see README.md NOT TESTED)
1 skipped, 1 warning in 0.00s

--- import app.main, zero files ---
import ok
files_created:0

STILL NOT TRUE
- QIP-R2.3 is not traced, not passed, and not implemented as a QIP
  trace: QIP-AUTH-05 is a skipped NOT TESTED record only.
- No QIP class (OBSERVE, INTERVENE, AUTHORIZE or EVIDENCE) is claimed;
  in particular AUTHORIZE is not claimed on the basis of QIP-AUTH-01
  to 04, which cover only QIP-R2.1/QIP-R2.2 behaviour.
- It has not been shown that no representation anywhere in the
  repository, UI, exports or external material presents application
  authorisation as safety-rated or as physical-safety evidence; that
  human claim audit was not performed and is not performed by any test
  here.
- Nothing here is certification, standards conformance, a safety-rated
  authorisation architecture, physical-safety, latency or regulatory
  evidence. The system under test remains the in-repo simulator.
- QIP-v0.1 Section 11 still reads QIP-R2.3 = UNIMPLEMENTED; this node
  did not amend it, and the tools/repro checklist reading that table
  will therefore still report QIP-R2.3 as UNSUPPORTED_EXPLICIT.

NEEDS A HUMAN DECISION
- Profile owner: accept this explicitly-untestable record for
  QIP-R2.3, or define a human claim-audit procedure (scope of
  representations to be audited, reviewer, cadence, evidence record)
  outside this runtime conformance suite, or amend/reword QIP-R2.3
  under QIP-v0.1 Section 11's amendment procedure. Until then it must
  stay UNIMPLEMENTED.
- Profile owner only: if a future audited decision ever changes the
  Section 11 row, that amendment is theirs; it must not be made by a
  conformance work node.
