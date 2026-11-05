# Checks

One row per requirement. Verdict is pass, fail, or unresolved.
Evidence is a file path or actual output. Missing evidence stays
visible as unresolved. Only N0 updates this file (see graph.md
assembly rule).

| node | requirement | verdict | evidence |
|---|---|---|---|
| N0-housekeeping | graph.md, checks.md, progress.md created exactly per docs/specs/GRAPH-HARNESS.md Part 4 | pass | graph.md; checks.md; progress.md |
| N0-housekeeping | Immutable rules R-IMM-1 to R-IMM-5 seeded in graph.md | pass | graph.md section "Immutable confirmed rules" |
| N0-housekeeping | docs/plans reconciled, no competing planning surface, choice stated | pass | graph.md section "Planning-surface decision"; docs/plans/2026-11-02-overnight-prototype.md status banner |
| N0-housekeeping | Per-node progress/<node-id>.md ownership and final N0 assembly rule established, no shared writes | pass | graph.md section "Per-node progress ownership and assembly rule"; progress/N0-housekeeping.md |
| N0-housekeeping | REPO-MAP.md covers every tracked repository path with one concise line, deterministic generation only | pass | REPO-MAP.md; scripts/generate_repo_map.py; progress/N0-housekeeping.md regeneration output |
| N0-housekeeping | Merged ancestry confirmed before deleting remote branches lane-c-live-meta, lane-e-settlement, lane-f-registry-a, lane-f-registry-b, lane-f-registry-c, lane-f-registry-d, meta/frontier-phase1-20261105-070059, meta/secure-core-hardening-20261105-082758, meta/secure-core-rust-20261105-073231 | pass | progress/N0-housekeeping.md raw merge-base --is-ancestor output (all True) |
| N0-housekeeping | Dormant worktrees behind deleted branches pruned; worktrees with unmerged work or user artifacts preserved | pass | progress/N0-housekeeping.md raw git worktree list output |
| N1-meta-live | One real call recorded with model ID, provider, UTC, prompt, redacted response, validator verdict, commit | unresolved | docs/evidence/meta-live.md (blocked on credentials; no real call evidenced yet) |
| N2-lifecycle | Import of app.main creates no file | unresolved | no raw output committed yet |
| N2-lifecycle | State dirs 0700 | unresolved | no raw output committed yet |
| N2-lifecycle | Both fail-direction tests still pass | unresolved | no raw output committed yet |
| N2-lifecycle | 10 consecutive green runs per mode with raw output committed | unresolved | no raw output committed yet |
| N3-copper | Run containing a STOP recorded, replayed, byte-identical task outputs, both logs and comparison committed | unresolved | spikes/copper-stop-path/** not yet present |
| N4-registry-dedup | Every claim-* has an official source URL | unresolved | research/humanoids/** not yet checked by N4 |
| N4-registry-dedup | No status promotion without a human row in checks.md | unresolved | no promotion proposed yet |
| N5-adversarial | Invariant checker proven able to fail before any corpus is generated | unresolved | research/adversarial/** not yet present |
| N5-adversarial | Corpus >=6,500 generated and >=50,000 mutated, deduplicated; run.py reproduces results.jsonl offline (docs/specs/M2-ADVERSARIAL-CORPUS.md section 5) | unresolved | research/adversarial/** not yet present |
| N6-profile-draft | Every requirement traceable to an observed manufacturer interface or a stated design decision | unresolved | depends on N4 matrix |
