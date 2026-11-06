NODE: advprov-postmerge-summary
TIER: 1
BRANCH: node/advprov-postmerge-summary
COMMITS: b57619bfb4ed50a134d8775b084cc1a2236fd1ca (code + initial report), plus the docs commit that records this hash (git log on this branch)
STATUS: complete (pending scheduler merge; PR opened by this worker, not merged by this worker)

CHANGED:
- research/adversarial/provenance.py (new): self-describing summary envelope.
  Tries ops.longrun (atomic_write_json, utcnow) when importable; otherwise a
  vendored fallback with the same tempfile+fsync+os.replace semantics, and
  records which source was used in provenance.source / LONGRUN_SOURCE.
  ops/longrun.py is not on origin/main (only on unmerged ops/installation)
  and ops/** is outside this node's owned paths, so no ops/ file was written.
- research/adversarial/backfill_provenance.py (new): backfills ONLY
  results/postmerge-summary.json, from committed evidence only
  (evidence/adversarial-postmerge.md + evidence/postmerge-full-run.txt).
  Refuses unless the log ends RC=0 and its total_results matches the
  summary. --check exits 1 if required fields are missing.
- research/adversarial/results/postmerge-summary.json: unchanged result
  keys/values (total_results=63012, escapes=[], s0_violations=[]) plus
  complete=true, citable=true, reason, commit=c19501c8b8e4008fcc6724964baa57be158f62bd,
  started_utc=null, finished_utc=null, toolchain (all null except
  git_commit), generator (script, evidence command with --mutations 50000,
  cases=56506), provenance (sources, results-jsonl SHA-256 from the
  evidence markdown, backfilled=true). Nulls are explicit: the committed
  postmerge evidence records no UTC timestamp and no toolchain, so none
  was invented.
- research/adversarial/run.py: every summary it writes is now enriched at
  write time (started/finished UTC, observed commit + toolchain, generator
  with argv/mutations/paths/cases, complete/citable) via provenance.py,
  written atomically; an S0 early stop now writes complete=false,
  citable=false with a WARNING instead of a bare count.
- research/adversarial/tests/test_postmerge_provenance.py (new, 5 tests).
- research/adversarial/evidence/postmerge-summary-provenance.txt: raw
  gate output (not a summary of it).

EVIDENCE (command, toolchain, host, UTC, raw output path):
- Raw output path: research/adversarial/evidence/postmerge-summary-provenance.txt
- Host: Quberon1.local, Darwin 24.3.0 arm64 (uname in raw file)
- UTC: 2026-11-06T14:21:40Z (in raw file; subsequent sections appended same session)
- Toolchain: Python 3.11.15 (.venv/bin/python), cargo 1.99.1, rustc 1.99.1 (in raw file)
- Commands (all in raw file, each followed by its RC):
  .venv/bin/python research/adversarial/backfill_provenance.py
  .venv/bin/python research/adversarial/backfill_provenance.py --check
  .venv/bin/python -m pytest research/adversarial/tests -q
  cargo build --workspace
  .venv/bin/python -m pytest -q                      (with Rust)
  <both named fail-direction tests>                  (with Rust)
  env PATH=<no cargo> .venv/bin/python -m pytest -q  (Rust removed from PATH)
  <both named fail-direction tests>                  (Rust removed from PATH)
  import app.main in an empty tmp dir                (zero files created)

TESTS (both modes):
- Exit gate: python -m pytest research/adversarial/tests -q -> 17 passed (raw file).
- With Rust (cargo build --workspace, RC=0): full suite 216 passed; both
  fail-direction tests (test_stop_executes_without_secure_core_but_reset_does_not,
  test_stop_rejected_by_secure_core_does_not_invoke_adapter) 2 passed.
- Rust removed from PATH (cargo on PATH: None): full suite 216 passed in
  the worktree (target/ binary still on disk there); in a clean clone of
  b57619b with no target/ built, the same mode gives 204 passed, 12 skipped
  and the exit gate gives 17 passed (raw file, clean-clone section).
  Both fail-direction tests 2 passed in the worktree without-Rust run.
- import app.main creating zero files: files_created: [] (raw file).

STILL NOT TRUE:
- The historical postmerge run's finished_utc and toolchain are NOT known
  and are NOT recovered by this node: they are null in the JSON. Only
  fields with a committed source (commit, command, cases, mutations,
  results SHA-256, RC=0 completion) were backfilled. Anyone needing a
  non-null finished_utc/toolchain must re-run the 63,012-result run;
  run.py now records them at write time, but that re-run was not done here.
- ops/longrun.py itself was NOT added or modified (outside owned paths;
  it exists only on the unmerged ops/installation branch). provenance.py
  prefers it when importable and otherwise uses its named vendored
  fallback; on this branch the fallback is what executed.
- run.py does NOT use ops.longrun.LongRun: there is no checkpoint/resume
  and no partial-summary-on-SIGTERM for the adversarial loop in this node.
  A killed future run can still leave no summary; only the S0-stop path
  writes a non-citable summary. LongRun integration is future work.
- The in-worktree without-Rust run removed cargo from PATH only, with a
  target/ binary on disk; the clean-clone section of the raw evidence
  (no target/ at clone time, 204 passed / 12 skipped) is the no-binary
  evidence, and it verified commit b57619b, not any later docs commit.
- The 63,012 count's underlying 26 MB results JSONL is not in this repo
  (per evidence/adversarial-postmerge.md it is reproducible from the
  recorded command); this node did not regenerate or re-verify it.
- No certification, physical-safety, latency, or regulatory-compliance
  claim is supported by this repository or by this change.

NEEDS A HUMAN DECISION:
- Land ops/longrun.py on main (Tier 2 ops/installation branch) so
  provenance.py's preferred path, not the vendored fallback, executes;
  and decide whether run.py should be migrated to LongRun
  (checkpoint/resume, partial-on-SIGTERM) as a follow-up node.
- Decide whether to re-run the full postmerge corpus to obtain a
  first-class (non-backfilled) summary with real finished_utc/toolchain,
  superseding the nulls recorded here.
