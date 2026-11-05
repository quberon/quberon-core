# Quberon — master plan and agent graph harness
**Issued:** 2026-11-05, against `main` @ `3f92e70`. Supersedes the wave-2 ordering, keeps all its rulings.

---

## Part 1 — What we are actually building

The pitch says "universal safety and control layer." True, but too broad to build against. The defensible asset underneath it is narrower and much harder for anyone else to copy:

> **Quberon is building the assurance-case infrastructure for human intervention over heterogeneous robots: a signed, replayable evidence chain running from sensor input → recognition → authorization decision → actuator outcome, that holds up to a safety engineer, a regulator and a court.**

The Pi, the e-ink QR, the web app and the simulator are the demonstrator. They are not the moat. The moat is the chain of custody:

| Already built | What it becomes |
|---|---|
| Ed25519 scope-pinned STOP envelope | Robot identity and delegated authority |
| Hash-chained SQLite audit log | Tamper-evident operational record |
| Fail-direction asymmetry (intervene vs. permit) | The safety argument nobody else is making |
| Type-safe allow-listed planner validator | The boundary between capable models and physical action |
| Deterministic replay (Copper spike) | Reproducible evidence a certifier can re-run |

Everything commercial in the pitch — fleets, delegation, RaaS, billing, revenue splits, shared ownership — is downstream of custody records that the assurance case requires anyway. Build the evidence chain and the business model falls out of it. Build the business model first and the evidence chain never gets built.

**The strategic consequence:** our competitor is not another startup. It is the status quo where every manufacturer ships its own incompatible stop button and nobody can audit any of it. You do not beat a status quo by shipping a product. You beat it by publishing a specification that makes the status quo look negligent, and then being the reference implementation.

---

## Part 2 — Rulings you asked for

**R1 — Copper gate: OPEN IT NOW.** The Lane C gate was about not claiming runtime Meta inference before evidence. The Copper spike makes no Meta claim at all. Blocking a determinism spike behind a credential you do not currently have is pure idle time. Lane D proceeds immediately.

**R2 — MSRV conflict: isolate, do not upgrade.** Copper 1.3.0 requires Rust 1.95; the root workspace is on 1.74. Do **not** raise the root MSRV, because the secure core is the one component whose toolchain stability matters most. Create `spikes/copper-stop-path/` as its own independent Cargo workspace, excluded from the root workspace members, with its own toolchain file. If the spike graduates, the MSRV decision gets made deliberately and separately.

**R3 — The M2 spec is not on main because it never left my machine.** That is my gap, not yours. Rasmus will commit `docs/specs/M2-ADVERSARIAL-CORPUS.md` and `docs/specs/GRAPH-HARNESS.md` to the repo. Until those files exist on main, Lane B stays unstarted. Do not reconstruct the spec from memory or from this document's summary.

**R4 — Parallelism: use the idle slots.** We have been running one lane at a time while every agent slot sat idle. From now on, nodes with no shared files run concurrently. The file-level conflict map is in Part 4. Two nodes may never edit the same file in the same wave.

---

## Part 3 — The master plan

### M0 — Truthful v0.1 (now → ~2 weeks)
*Goal: a repo and a written thesis that a safety engineer, a YC partner or a Meta screener can read without finding a single overstated claim.*

- Lane C: one real Meta call, evidenced. (Blocked only on credentials.)
- Lane P1: lifecycle and state-path security. No filesystem effects on import, explicit app factory, private state directories, hardened SQLite/WAL/sidecars.
- Lane D: Copper spike with deterministic replay as the acceptance criterion.
- Lane B: adversarial planner corpus, published with its escapes section.
- Close or formally accept the intermittent STOP-path non-determinism.

**Exit:** every README claim reproducible from a clean clone; `docs/evidence/` complete; one public write-up of the fail-direction argument.

### M1 — The Intervention Profile (≈ 2–6 weeks)
*This is the big move. Do not skip it for more code.*

- Lane F completes: dedup/scope pass, then the manufacturer intervention-interface matrix from official sources only.
- That matrix answers the thesis question: do humanoid manufacturers expose any documented emergency-stop or operator-authorization interface? If most do not, that absence **is** the market, and it is evidence, not opinion.
- Then publish **the Quberon Intervention Profile v0.1**: an open, vendor-neutral specification for what a manufacturer-independent intervention interface must expose — identity, authorization, intervention, state attestation, audit record format, fail-direction semantics. Apache-2.0 or CC-BY, versioned, with a conformance test suite derived directly from our existing test corpus.
- A solo founder cannot out-ship Figure or Tesla. A solo founder can absolutely write the spec that everyone later has to argue with. The conformance suite is the product wedge: run it against a robot, get a report.

**Exit:** matrix published, profile v0.1 published, conformance suite runnable against our own simulator.

### M2 — Hardware in the loop (≈ 6–12 weeks)
- One real platform end to end, under explicit approval per deployment. The RISE drone first because you have access; a humanoid when one is available.
- Recorded scenarios: latency, occlusion, false triggers, dropped frames, sensor degradation, contradictory voice and gesture signals.
- Signed evidence bundles tying sensor input → recognition → authorization → outcome, replayable by a third party.
- Begin an assurance-case document mapped against EU Machinery Regulation and AI Act obligations — **as a research map citing primary sources, never as legal advice or a compliance claim.**

### M3 — Fleet and custody (≈ 3–6 months)
- Multi-instance latch coherence (review item G): the step from one robot to a fleet.
- Lane E settlement: doc first, devnet-only anchoring of audit roots, EURC settlement intents.
- First design partner. One real operator with real robots beats ten letters of intent.

---

## Part 4 — The agent graph, instantiated

Adopting the graph harness. Three files live in the repo and are the shared state between every agent and every session:

- `graph.md` — nodes, edges, checks, and the rules each accepted result confirmed.
- `checks.md` — one row per requirement: `node | requirement | verdict | evidence`, verdict in {pass, fail, unresolved}, evidence as a file path or actual output. Missing evidence stays visible as `unresolved`.
- `progress.md` — nodes done/running/blocked, exact output paths, decisions and why, open issues, next ready node.

**On resumption, every agent reads `graph.md` and `progress.md` first and continues from the recorded next node.** That single rule removes most of the waste we have been paying for.

### Wave-3 nodes

| Node | Owns these files | Depends on | Gate (deterministic check first) |
|---|---|---|---|
| `N1-meta-live` | `integrations/meta.py`, `docs/evidence/meta-live.md` | credentials | One real call recorded with model ID, provider, UTC, prompt, redacted response, validator verdict, commit |
| `N2-lifecycle` | `app/main.py`, `integrations/secure_core.py`, `scripts/` | — | Import of `app.main` creates no file; state dirs 0700; both fail-direction tests still pass; 10 consecutive green runs per mode with raw output committed |
| `N3-copper` | `spikes/copper-stop-path/**` only | — | Record a run containing a STOP, replay it, show byte-identical task outputs. Replay is the acceptance criterion; latency is secondary |
| `N4-registry-dedup` | `research/humanoids/**` | — | Every `claim-*` has an official source URL; no status promotion without a human row in `checks.md` |
| `N5-adversarial` | `research/adversarial/**` | R3 spec committed | Invariant checker proven able to fail before any corpus is generated |
| `N6-profile-draft` | `docs/specs/intervention-profile/**` | N4 matrix | Every requirement traceable to either an observed manufacturer interface or a stated design decision |

N2, N3, N4 share no files and run **in parallel now**. N1 starts the moment credentials exist. N5 starts when the spec lands. N6 follows N4.

### Gate rules
- Deterministic check first, then the node's report, then the model's confidence last. Never accept a node on narrative.
- A failed gate returns the node to whoever produced it, with the reason, the evidence, and the scope "fix this node only". Three attempts, then it becomes a blocker and stops.
- After an accepted result, write the rule it confirmed into `graph.md` so the next run starts from it.
- Never weaken a gate to obtain a pass. If a gate is wrong, say so and change it deliberately, in its own commit.

---

## Part 5 — Making the Meta agents faster and cheaper

These come from observed waste in waves 1 and 2, not from theory.

1. **Refresh state as code, not as judgment.** Every node begins with `git fetch --prune && git log -1 --format=%H origin/main && gh pr list --state open`. Twice already a question was raised against stale remote state (PR #4 was merged before you asked what to do about it). A model should never *reason* about what the remote contains.
2. **Deterministic steps are code, never model calls.** Merging, sorting, deduping, counting, diffing, comparing files, validating schemas, checking hashes. A model call is for judgment only. This is the single largest token saving available and it also removes a class of errors.
3. **One node, one worktree, minimal context.** Pass the node spec, its inputs and its check. Do not load the whole repo. Maintain a generated `REPO-MAP.md` (paths plus one line each) and let nodes read that instead of walking the tree.
4. **Parallelise by file ownership, not by folder.** The conflict map in Part 4 is the authority. Two nodes never edit one file in a wave.
5. **Tier the models.** Cheap and fast for classification, extraction, dedup candidates, log triage and schema filling. Strong for architecture, safety reasoning, conflict resolution and anything touching `execute_stop`. Never route a deterministic step through a model at all.
6. **Budget every node.** A wall-clock and token cap, three attempts, then return a partial status with the exact steps left. Unbounded retry loops are how an overnight run produces nothing.
7. **Cache aggressively.** Committed corpora, offline replay, pinned toolchains. Any run that needs the network to reproduce is a run that cannot be reproduced.
8. **Report evidence, not confidence.** Twice the report ran slightly ahead of the evidence (21-passed figures that predated a merge; a 0-failed claim against an unreproduced flake). The format already asks for raw output — treat a summary line where raw output was requested as a failed gate, not a stylistic issue.
9. **Write the learning edge.** Every confirmed rule goes into `graph.md`. The fail-direction asymmetry, the blockchain prohibition, the MSRV isolation and the evidence-before-claim rule should all already be there, so no future session re-litigates them.

---

## Part 6 — Kickoff message for Quberon1

```
Wave 3. Adopting a graph harness. Read this fully before acting.

NEW SHARED STATE — create these on main first, in one commit:
- graph.md: nodes, edges, checks, and the rules confirmed so far. Seed it with the four standing rules: (1) intervention must not fail closed on attestation unavailability while permission must; (2) nothing on the control path may depend on a blockchain; (3) no claim ahead of its evidence; (4) secure-core MSRV is isolated from spike workspaces.
- checks.md: one row per requirement, node | requirement | verdict | evidence. Verdict is pass, fail or unresolved. Evidence is a file path or actual output. Missing evidence stays visible as unresolved.
- progress.md: nodes done/running/blocked, exact output paths, decisions and why, open issues, next ready node.
On any resumption, read graph.md and progress.md first and continue from the recorded next node.

RULINGS
R1. Copper gate is OPEN. It makes no Meta claim; do not block a determinism spike behind a credential we do not have. Start it now.
R2. Do not raise the root Rust MSRV. Create spikes/copper-stop-path/ as an independent Cargo workspace, excluded from root members, with its own toolchain file.
R3. The M2 spec was never committed — my gap. Rasmus is committing docs/specs/M2-ADVERSARIAL-CORPUS.md and docs/specs/GRAPH-HARNESS.md. Do not start Lane B until those files exist on main, and do not reconstruct the spec from memory.
R4. Use the idle slots. Run N2, N3 and N4 in parallel now; they share no files.

NODES THIS WAVE
N2-lifecycle    owns app/main.py, integrations/secure_core.py, scripts/
N3-copper       owns spikes/copper-stop-path/** only
N4-registry     owns research/humanoids/**
N1-meta-live    owns integrations/meta.py + docs/evidence/meta-live.md, starts when credentials arrive
N5-adversarial  starts when the spec lands
N6-profile      follows N4

Gates, verbatim: deterministic check first, then the node's report, then confidence last. A failed gate returns to the node that produced it with reason, evidence and the scope "fix this node only", capped at three attempts, then it becomes a blocker. Never weaken a gate to obtain a pass.

N3 acceptance is deterministic replay, not latency: record a run containing a STOP, replay it, show byte-identical task outputs, commit both logs and the comparison.
N2 acceptance includes: importing app.main creates no file, state directories are 0700, both fail-direction tests still pass, and ten consecutive green runs per mode with raw output committed.

EFFICIENCY RULES, now binding
- Start every node with git fetch --prune and gh pr list --state open. Never reason about remote state.
- Deterministic work is code, never a model call: merging, sorting, dedup, counting, diffing, schema validation, hashing.
- One node, one worktree, minimal context. Generate REPO-MAP.md and read that instead of walking the tree.
- Tier models: cheap for extraction and classification, strong for safety reasoning and anything touching execute_stop.
- Budget every node in wall-clock and tokens, three attempts, then return a partial status listing the exact steps left.
- Where raw output was requested, a summary line is a failed gate.

Report per node in the established format. Do not merge without approval. Do not deploy to the Pi. Do not self-authorize a node that is not in this wave.
```
