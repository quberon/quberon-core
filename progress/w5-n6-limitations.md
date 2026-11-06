# Node w5-n6-limitations — progress / final report

NODE: w5-n6-limitations
TIER: 1
BRANCH: node/w5-n6-limitations
COMMITS: see final message / PR (this file is committed with docs/LIMITATIONS.md; commit hash is recorded in the PR, not self-referenced here to avoid a hash-of-itself)
STATUS: complete for owned paths; outside-path references are handed off below, not made
CHANGED:
- docs/LIMITATIONS.md (new, canonical, append-only thereafter)
- progress/w5-n6-limitations.md (this file, new)

## What was done

Created docs/LIMITATIONS.md as the single canonical statement of what is
not true, assembled only from limitation / NOT TESTED / claim-discipline /
unsupported / roadmap material already in progress/*.md and
docs/DILIGENCE.md (plus README "Known limitations" and degraded-mode
matrix, quoted as source, not edited). Entries are grouped (physical
control/safety; latency/load; certification/standards/legal; secure core
and custody; degraded/persistence/audit; live models and adversarial
evidence; voice/gesture; Isaac Sim; manufacturers/registry/R10; Pi/phone/
cellular/GNSS/deployment; counts/reproducibility; roadmap-not-claimed),
each with its source file named inline. The file states its append-only
rule: no entry is edited or deleted; retirement requires a dated
supersession entry naming old entry, new evidence path, commit, host,
toolchain, and clean-clone command.

Search note (honest): at base 7fd9ea5 there is no literal heading
"STILL NOT TRUE" in progress/*.md or docs/DILIGENCE.md
(`grep -rn "NOT TRUE" progress/ docs/DILIGENCE.md` -> no matches), and
there is no ops/ directory or ops/schedule.py in this clone
(`git ls-files` / REPO-MAP.md: 269 tracked paths, none under ops/).
The assembly therefore used the equivalent sections that exist
(NOT TESTED, Limits, Claim discipline, Unsupported, Roadmap
(explicitly not claimed), Known limitations). The generator-1 unblock
claim about ops/schedule.py could not be verified from this repository;
only the exit gate `test -s docs/LIMITATIONS.md` was verified here.

## EVIDENCE

Command, toolchain, host, UTC, raw output path:

- Exit gate: `test -s docs/LIMITATIONS.md; echo TEST_S_EXIT:$?`
  -> TEST_S_EXIT:0 (raw line reproduced under TESTS).
- Toolchain/host: Darwin Quberon1.local 24.3.0 arm64 (macOS 15.3.1);
  Python 3.11.15 (.venv); cargo 1.99.1 (5f94df478 2026-08-27);
  rustc 1.99.1 (58cf8f9c3 2026-10-13) Homebrew.
- UTC at run start: 2026-11-06T10:52:24Z (`date -u`).
- Raw logs on the build host (not committed; summaries below are copied
  verbatim tails, and this progress file is the committed evidence):
  /tmp/w5n6-setup-rust.log, /tmp/w5n6-with-rust.log,
  /tmp/w5n6-cargo.log, /tmp/w5n6-without-rust-path.log,
  /tmp/w5n6-without-rust.log, /tmp/w5n6-faildirection.log,
  /tmp/w5n6-import.log

Raw output (verbatim tails, not summaries):

make setup (with Rust) -> EXIT:0
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 4.42s

With Rust, `.venv/bin/python -m pytest -q` -> WITH_RUST_EXIT:0
    211 passed, 2 warnings in 40.94s

With Rust, `cargo test --workspace` -> CARGO_EXIT:0
    test result: ok. 14 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.65s
    test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
    test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.26s
    test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s

Rust removed from PATH only (PATH=/tmp/w5n6-norust-bin:/usr/bin:/bin,
python3.11 shimmed, `command -v cargo` -> exit 1; built CLI still on disk,
so Rust-gated tests still run): -> WITHOUT_RUST_PATH_EXIT:0
    211 passed, 2 warnings in 40.96s

Without Rust as this repo historically defines it (same PATH plus
target/debug/quberon-secure-core-cli temporarily moved aside and restored
after the run): -> WITHOUT_RUST_BINARY_EXIT:0
    199 passed, 12 skipped, 2 warnings in 39.15s

Both fail-direction tests:
`.venv/bin/python -m pytest tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter -v`
-> FAILDIR_EXIT:0
    tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not PASSED [ 50%]
    tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter PASSED [100%]
    ========================= 2 passed, 1 warning in 0.30s =========================

`import app.main` creating zero files: run from empty
/tmp/w5n6-importcheck with PYTHONPATH=<worktree>,
`python -c "import app.main; print('import ok')"` -> IMPORT_EXIT:0,
"import ok", FILES_CREATED_COUNT:0 (`find . -type f | wc -l`).
Worktree afterwards: `git status --porcelain` shows only
?? docs/LIMITATIONS.md (and this progress file once written);
.venv/ and target/ are gitignored build output from make setup.

Exit gate: `test -s docs/LIMITATIONS.md` -> TEST_S_EXIT:0

## TESTS (both modes)

- With Rust: 211 passed, 2 warnings (pytest); cargo 14 + 3 passed.
- Rust removed from PATH: 211 passed (CLI binary still present on disk —
  stated, not hidden); with CLI binary also removed (repo's historical
  without-Rust mode): 199 passed, 12 skipped, 2 warnings.
- Fail-direction (both named tests): 2 passed.
- Import inertness: import ok, 0 files created.
No gate in ops/gate.sh was run: ops/gate.sh does not exist in this clone,
so the universal gate was executed manually as the four checks above.
That substitution is stated here, not concealed.

## STILL NOT TRUE

Mandatory, non-empty (canonical full text: docs/LIMITATIONS.md):

- No physical robot control, no safety-rated/certified e-stop, no
  physical stop time, no independent physical-state sensing.
- No latency, deadline, starvation, Pi, or hardware timing claim; load
  numbers are one shared Mac's simulation observations, calibration
  failed, and successful-task contention, network partition, Rust-core
  under load, and Pi execution remain unmeasured.
- No certification, standards (PL/SIL), hazard-analysis, or
  regulatory/legal-compliance claim; no QIP class is claimed; QIP R10
  manufacturer mapping and QIP-R3/R7 promotion remain UNIMPLEMENTED
  pending the profile owner's amendment procedure.
- Live Meta inference is NOT verified (BLOCKED, 0 provider calls);
  adversarial corpora are same-agent deterministic templates (weak
  evidence), no independent-model adversary has run.
- No signer authority beyond a bundled self-asserted key; a rebuilt and
  re-signed bundle passes internal-consistency checks; no HSM/TPM
  custody, secure OTA, or SLSA provenance.
- Real disk/SQLite persistence failure and restart recovery, audit
  retention/clock-trust/export/custody, real signing under refusal,
  microphone/camera capture, sensor qualification, and an Isaac Sim run
  have not been shown.
- Registry: 0 verified companies, 25 candidates unverified,
  universe_size_claim null, human decisions pending; voice/gesture is
  synthetic-only with documented boundary limits.
- Pi: secure-core gate not deployed on the Pi; Pi success path, camera,
  health endpoint NOT RUN in Wave 6 prep; phone is not zero-setup;
  cellular has no failover claim; GNSS has no RTK/accuracy claim.
- No universal test count; no standing cargo audit/deny/SBOM claim;
  fuzz smoke not run; no byte-reproducible-binary claim.
- ops/schedule.py and ops/gate.sh are not present in this clone, so no
  claim is made that generator 1 now produces anything; only that
  docs/LIMITATIONS.md now exists and is non-empty.

## NEEDS A HUMAN DECISION

- Whether the scheduler/generator that expects this file lives outside
  this repository (no ops/ in clone): confirm where generator 1 reads
  docs/LIMITATIONS.md from, since it cannot be verified here.
- The reference edits below are outside this node's owned paths and were
  not made; a human or the owning node must apply them for the
  "referenced from README and every evidence bundle" requirement to be
  literally true in the tree.

handoff: README.md needs a link to docs/LIMITATIONS.md beside the docs/DILIGENCE.md reference at the claim-to-evidence map because README.md is outside the owned paths of node w5-n6-limitations
handoff: docs/evidence/README.md needs a docs/LIMITATIONS.md row stating it is the canonical not-true statement because docs/evidence/README.md is outside the owned paths of node w5-n6-limitations
handoff: crates/quberon-evidence-bundle/SPEC.md needs a reference to docs/LIMITATIONS.md in its unsupported-claims section because the evidence-bundle spec is outside the owned paths of node w5-n6-limitations
handoff: evidence-bundle-conformance/README.md needs a reference to docs/LIMITATIONS.md beside its limitation disclosure because evidence-bundle-conformance/README.md is outside the owned paths of node w5-n6-limitations
handoff: tools/quberon-verify/README.md needs a reference to docs/LIMITATIONS.md in its claim-boundary wording because tools/quberon-verify/README.md is outside the owned paths of node w5-n6-limitations
handoff: crates/quberon-evidence-bundle/README.md needs a reference to docs/LIMITATIONS.md in its claim-boundary wording because crates/quberon-evidence-bundle/README.md is outside the owned paths of node w5-n6-limitations
