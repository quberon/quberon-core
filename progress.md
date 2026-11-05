# Progress

Assembled by N0 only, from progress/<node-id>.md files. No other node
edits this file. On resumption, read graph.md and this file first and
continue from the recorded next node.

Base: origin/main 66813358f351250ba6d690f850508ca26bc1fc67

## Nodes done / running / blocked

| Node | Status | Exact output paths | Notes |
|---|---|---|---|
| N0-housekeeping | done (pending PR, not merged) | graph.md; checks.md; progress.md; progress/N0-housekeeping.md; REPO-MAP.md; scripts/generate_repo_map.py; docs/plans/2026-11-02-overnight-prototype.md (banner) | See progress/N0-housekeeping.md for raw evidence. PR opened, CI waited on, not merged: N0 is not self-merge authorized. |
| N1-meta-live | blocked | integrations/meta.py; docs/evidence/meta-live.md | Blocked on credentials. |
| N2-lifecycle | ready | app/main.py; integrations/secure_core.py; scripts/ | May start after N0. |
| N3-copper | ready | spikes/copper-stop-path/** | Copper gate open (R1). May start after N0. Root MSRV must not be raised (R-IMM-5/R2). |
| N4-registry-dedup | ready | research/humanoids/** | May start after N0. |
| N5-adversarial | blocked | research/adversarial/** | Spec is on main, but per wave order N5 starts after N0 and after its owner picks it up; invariant checker must be proven able to fail first. |
| N6-profile-draft | blocked | docs/specs/intervention-profile/** | Depends on N4 matrix. |

## Decisions and why

- Planning surface: graph.md is the single planning index;
  docs/plans/2026-11-02-overnight-prototype.md is archived historical.
  Why: GRAPH-HARNESS.md Part 4 makes graph.md/checks.md/progress.md the
  shared state; a second active plan would compete with it.
- Progress ownership: each node writes only progress/<node-id>.md; N0
  alone assembles progress.md, checks.md, graph.md at wave close.
  Why: no shared writes removes file conflicts between parallel nodes.
- Branch cleanup: all nine named remote branches were confirmed
  ancestors of origin/main by git merge-base --is-ancestor, then
  deleted; their clean worktrees were removed. Other worktrees were
  preserved. Raw output in progress/N0-housekeeping.md.

## Open issues

- N1-meta-live credentials unavailable; verdict unresolved in checks.md.
- No other Wave-3 node has started; N0 was run alone first, as ordered.

## Next ready node

N2-lifecycle, N3-copper, and N4-registry-dedup are ready and share no
files; they may run in parallel. Each starts by reading graph.md and
progress.md, then creates its own progress/<node-id>.md.
