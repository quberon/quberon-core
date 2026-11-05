# Progress - F7 reproducibility and assurance pack (Wave 5, Tier 1)

Owner: F7 alone. Owns ONLY: tools/repro/**, docs/assurance/**,
progress/F7-repro-assurance.md. No README edits, no legal conclusions,
no certification/conformance/class claim. Base: 35ee2ae
(35ee2aef6f7a2fcf17e51de40678aee97ba0b350, verified
`git log -1 --format=%H origin/main` = HEAD at start; `gh pr list
--state open` returned none at start).

Sources read: docs/specs/GRAPH-HARNESS.md (M0 exit: every claim
reproducible from a clean clone; M2 assurance map as research only),
docs/DILIGENCE.md (claim->evidence->clean-clone command, reconciled
counts), docs/specs/intervention-profile/QIP-v0.1.md R11 + S.11
traceability (raw output required; no class claimed; UNIMPLEMENTED
rows explicit), PRIOR-ART.md + LEGAL-RESEARCH-ROADMAP.md (primary
sources only, no conclusions; Machinery Reg. (EU) 2023/1230 EUR-Lex
`official full public text reviewed`).

## Attempts (max 3)

- Attempt 1: built runner + docs; unit tests; worktree full run
  (below). Passed locally.
- Attempt 2: clean-clone full run from the pushed branch (below,
  filled after that run) + CI fixes if any. No gate weakened.
- Attempt 3: unused unless CI requires a fix within owned files.

## What was built

- tools/repro/repro.py (stdlib only, executable): records
  environment-manifest.json (git commit/branch/dirty count, platform,
  Python/tool versions, SHA-256 of requirements.txt/Cargo.toml/
  Cargo.lock/Makefile/scripts/sbom.sh/CI workflow/DILIGENCE/QIP;
  no env dump, no secrets); runs make setup (unless --skip-setup /
  python-only / record-only), pytest, cargo test --locked, and the
  repo's scripts/sbom.sh, each with raw logs/<step>.log, exit code,
  duration; SKIPPED is recorded with a reason and never as a pass
  (no cargo -> cargo_tests SKIPPED, SBOM NOT GENERATED, explicit).
  Hashes (SHA-256+size) the SBOM + built secure-core CLI +
  caller --artifact globs into artifact-hashes.json. Emits
  claim-to-evidence.{json,md} parsed (not hand-written) from
  docs/DILIGENCE.md rows and QIP S.11 rows, plus the run itself as a
  row; UNIMPLEMENTED -> UNSUPPORTED_EXPLICIT, DILIGENCE `none`
  commands -> NOT_CLONE_VERIFIABLE, traces ->
  TRACE_PRESENT_NO_CLASS_CLAIM (never upgraded). Exit 0 only if every
  executed step exited 0.
- tools/repro/tests/test_repro.py: 5 tests (SHA-256 known vector,
  DILIGENCE/QIP parsing, unsupported statuses explicit, record-only
  run proves nothing and fakes no pass, no-artifact case explicit).
- tools/repro/README.md: exact commands/outputs/limits.
- docs/assurance/README.md: scope/limits (not certification, not a
  legal conclusion, not physical-safety validation, no QIP class).
- docs/assurance/CLAIM-TO-EVIDENCE.md: status vocabulary + standing
  unsupported categories; per-run checklists are generated.
- docs/assurance/RESEARCH-QUESTIONS.md: EU Machinery Regulation
  (EU) 2023/1230 and AI Act (EU) 2024/1689 ONLY as unresolved
  research questions Q-M1..M4 / Q-A1..A4 with EUR-Lex Official
  Journal primary URLs; no applicability/compliance conclusion.

## Deterministic check first (raw)

Baseline (pre-change, venv from requirements.txt, no Rust CLI built):
  pytest -q -> 131 passed, 13 skipped

Attempt 1 worktree run (this Mac, Python 3.11.15, cargo 1.99.1,
uncommitted F7 files present so manifest dirty=true):
  /tmp/f7-venv/bin/python tools/repro/repro.py --skip-setup --out repro-out
  -> exit 0; runs={setup: SKIPPED (--skip-setup), python_tests: PASS,
     cargo_tests: PASS, sbom: PASS}; artifacts=2; checklist=51 rows;
     unsupported=23
  python_tests.log tail: 136 passed, 13 skipped (131 baseline + 5 new
     repro tests)
  cargo test: suites 14 passed + 3 passed (17, per logs; final suite
     lines in repro-out/logs/cargo_tests.log at run time)
  sbom.log: wrote sbom.cdx.json with 98 components
  artifact hashes (that run): repro-out/sbom.cdx.json sha256=
     5797672cbbfcfc5d0326f685ae35c1025d05ba2ae573ede22a23710c8634ad1d;
     target/debug/quberon-secure-core-cli sha256=
     4ec2f6e519b667be30f8aca1158c142c6d1eaac4362ca58b0b4f2960ba022d9b
  repro-out/ and target/ were deleted after recording (generated
     output is not committed).

Clean-clone run (attempt 2, raw): fresh `git clone -b wave5/f7` at
e449fca9cb4ea49e8615c43fe919aabedeee0205 into /tmp/f7-clean,
manifest git.dirty=false, then default full mode:
  python3.11 tools/repro/repro.py --out repro-out -> exit 0;
  runs={setup: PASS (11.256s), python_tests: PASS (34.022s),
        cargo_tests: PASS (8.023s), sbom: PASS}
  python_tests.log tail: 148 passed, 1 skipped (with-Rust mode;
     counts are host/mode-specific, not universalised)
  cargo_tests.log: test result ok 14 passed + 3 passed (other suites 0)
  sbom.log: wrote sbom.cdx.json with 98 components
  artifacts: repro-out/sbom.cdx.json sha256=
     5797672cbbfcfc5d0326f685ae35c1025d05ba2ae573ede22a23710c8634ad1d
     (byte-identical SBOM hash to the attempt-1 worktree run);
     target/debug/quberon-secure-core-cli sha256=
     33eabdd644ef0ddcf0a30db665073b953a85078fb779699659cacc4870eb64cf
     (binary hash differs across build dirs - recorded, no
     byte-reproducible-binary claim is made)
  checklist status counts: EVIDENCE_PRESENT 11,
     NOT_CLONE_VERIFIABLE 5, TRACE_PRESENT_NO_CLASS_CLAIM 16,
     UNSUPPORTED_EXPLICIT 18, SUPPORTED_FOR_THIS_RUN 1 (total 51)

## Claim discipline

Generated checklist at attempt 1: 16 DILIGENCE rows (11
EVIDENCE_PRESENT, 5 NOT_CLONE_VERIFIABLE), 34 QIP rows (16
TRACE_PRESENT_NO_CLASS_CLAIM, 18 UNSUPPORTED_EXPLICIT), 1 repro-run
row. Explicitly not claimed: any QIP class, certification, legal
conclusion, live Meta inference, physical control/safety-rated
e-stop, manufacturer mappings (R10 gap), other-host results.

## Merge status

PR #33 (wave5/f7 -> main). CI on be6202f: dependency-review pass,
python-without-rust pass, rust-and-python pass (7m15s) - run
42123437563. Self-merge follows this progress update (which re-runs
CI on the final head); merged-main ancestry (`git merge-base
--is-ancestor <merge> origin/main` / merged head contained in
origin/main) is verified after merge and stated in the F7 final
report, not pre-claimed here.
