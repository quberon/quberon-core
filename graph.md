# Quberon agent graph

Shared state for every agent and session. On resumption, every agent reads
graph.md and progress.md first and continues from the recorded next node.

Sources: docs/specs/GRAPH-HARNESS.md, docs/specs/M2-ADVERSARIAL-CORPUS.md
Base: origin/main 66813358f351250ba6d690f850508ca26bc1fc67

## Planning-surface decision

Choice: graph.md is the single planning index.

docs/plans/2026-11-02-overnight-prototype.md is an archived historical plan.
It is linked from here for provenance only; it is not an active planning
surface and must not be updated as one. No competing planning surface is
created. Active nodes, edges, checks, and confirmed rules live in this file;
requirement verdicts live in checks.md; status lives in progress.md.

## Immutable confirmed rules

R-IMM-1: Intervention does not fail closed on attestation unavailability,
  while permission does. Intervention (STOP) proceeds with unsigned
  attestation when the secure core is unavailable; permission-gated actions
  (simulated task, latch reset) fail closed in that condition.
R-IMM-2: Unreachable authority differs from reachable refusal. An
  unreachable authority is unavailability; a reachable authority that
  refuses is a refusal. They must be reported and handled distinctly.
R-IMM-3: No blockchain on the control path. Nothing on the control path
  may depend on a blockchain. Settlement/anchoring, if any, is off the
  control path and downstream of custody records.
R-IMM-4: No claim ahead of evidence, and raw output is required. Where raw
  output was requested, a summary line is a failed gate. Deterministic
  check first, then the node report, then model confidence last.
R-IMM-5: Secure-core / root MSRV is isolated from spike workspaces. Do not
  raise the root Rust MSRV (1.74 in Cargo.toml workspace.package) for a
  spike. Spikes use an independent Cargo workspace, excluded from root
  members, with their own toolchain file. If a spike graduates, the MSRV
  decision is made deliberately and separately.

## Standing gate rules (from GRAPH-HARNESS.md Part 4)

- Deterministic check first, then the node report, then confidence last.
  Never accept a node on narrative.
- A failed gate returns the node to whoever produced it, with the reason,
  the evidence, and the scope "fix this node only". Three attempts, then
  it becomes a blocker and stops.
- After an accepted result, write the rule it confirmed into graph.md.
- Never weaken a gate to obtain a pass. If a gate is wrong, say so and
  change it deliberately, in its own commit.
- Two nodes may never edit the same file in the same wave.
- Deterministic steps are code, never model calls: merging, sorting,
  deduping, counting, diffing, comparing files, validating schemas,
  checking hashes.
- Every node starts with: git fetch --prune, git log -1 --format=%H
  origin/main, gh pr list --state open. Never reason about remote state.

## Nodes

| Node | Owns these files | Depends on | Gate (deterministic check first) |
|---|---|---|---|
| N0-housekeeping | graph.md, checks.md, progress.md, REPO-MAP.md, scripts/generate_repo_map.py, progress/N0-housekeeping.md, docs/plans/2026-11-02-overnight-prototype.md (status banner only) | origin/main 66813358f351250ba6d690f850508ca26bc1fc67 | Harness files exist per spec; REPO-MAP.md regenerated deterministically covers every tracked path; merged-ancestry proof before any branch deletion |
| N1-meta-live | integrations/meta.py, docs/evidence/meta-live.md | credentials | One real call recorded with model ID, provider, UTC, prompt, redacted response, validator verdict, commit |
| N2-lifecycle | app/main.py, integrations/secure_core.py, scripts/ (except scripts/generate_repo_map.py, owned by N0) | - | Import of app.main creates no file; state dirs 0700; both fail-direction tests still pass; 10 consecutive green runs per mode with raw output committed |
| N3-copper | spikes/copper-stop-path/** only | - | Record a run containing a STOP, replay it, show byte-identical task outputs. Replay is the acceptance criterion; latency is secondary |
| N4-registry-dedup | research/humanoids/** | - | Every claim-* has an official source URL; no status promotion without a human row in checks.md |
| N5-adversarial | research/adversarial/** | R3 spec committed (docs/specs/M2-ADVERSARIAL-CORPUS.md on main) | Invariant checker proven able to fail before any corpus is generated |
| N6-profile-draft | docs/specs/intervention-profile/** | N4 matrix | Every requirement traceable to either an observed manufacturer interface or a stated design decision |

## Edges

- N0-housekeeping -> all other nodes: harness must exist before other
  Wave-3 nodes start. N0 finishes first (this node, alone).
- credentials -> N1-meta-live
- N4-registry-dedup -> N6-profile-draft
- docs/specs/M2-ADVERSARIAL-CORPUS.md (on main) -> N5-adversarial
- N2-lifecycle, N3-copper, N4-registry-dedup: no shared files; may run in
  parallel after N0.

## Checks

checks.md is the verdict table: one row per requirement,
node | requirement | verdict | evidence, verdict in {pass, fail,
unresolved}. Missing evidence stays visible as unresolved.

## Per-node progress ownership and assembly rule

- Each node writes only progress/<node-id>.md, using its node slug above
  (for example progress/N2-lifecycle.md). A node owns that file alone.
- No shared writes: no node edits graph.md, checks.md, progress.md, or
  another node's progress/<node-id>.md.
- Final assembly is N0's alone: at wave close (or on request) N0 reads
  every progress/<node-id>.md, and only N0 updates graph.md (confirmed
  rules), checks.md (verdicts), and progress.md (assembled status).
  Conflicts are resolved by N0 from raw evidence, not by editing another
  node's file.
- REPO-MAP.md is generated, never hand-edited: run
  python3 scripts/generate_repo_map.py and commit its exact output.
