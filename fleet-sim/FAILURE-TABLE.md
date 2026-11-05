# Failure table — fleet latch coherence simulation (Wave5 F5)

Verdicts are from fleet-sim/test_fleet_sim.py (see raw output in
progress/F5-fleet-latch.md). "Safe direction" = latch retained / motion
not permitted / explicit non-claim, per graph.md R-IMM-1/R-IMM-2.

| # | Scenario | Expected (rule) | Sim outcome | Safe direction |
|---|---|---|---|---|
| F1 | Total partition, no leader, STOP on isolated node | Latches locally, zero network (R-IMM-1/3) | LATCHED, network_calls delta 0 | Yes — peers visibly unaware, no false convergence |
| F2 | Exact duplicate STOP | Original outcome, adapter not re-invoked (QIP R4.1) | LATCHED again, invocations=1 | Yes |
| F3 | Event id reused, different content | Conflict rejected, no invocation (QIP R4.2) | CONFLICT_REJECTED, invocations=1 | Yes |
| F4 | Distinct STOP while already latched | No re-invocation | LATCHED_ALREADY, invocations=1 | Yes |
| F5 | Delayed pre-reset STOP delivered after reset | Stale, no re-latch (QIP R4.3) | STALE_REJECTED, motion permitted | Yes — reset not undone by old traffic |
| F6 | Reset, authority unavailable | Fail closed, distinct from refusal (QIP R7.3, R-IMM-2) | RESET_UNAVAILABLE_FAIL_CLOSED, latched | Yes |
| F7 | Reset, reachable authority refuses | Fail closed, latch retained (QIP R7.4 by analogy at fleet layer) | RESET_REFUSED_FAIL_CLOSED, latched | Yes |
| F8 | Reset authorised against superseded epoch (newer STOP since) | Stale reset rejected | STALE_RESET_REJECTED, epoch-2 latch retained | Yes |
| F9 | Duplicate reset | Idempotent original outcome | RESET_APPLIED returned twice | Yes |
| F10 | Partition STOP, then heal | Converges latched everywhere, one origin | All latched, single origin after gossip | Yes |
| F11 | Concurrent STOPs in two partitions | Coalesce deterministically to one epoch/origin | Epoch 1 everywhere, lexicographic origin | Yes |
| F12 | Authorised reset in one partition vs lagging latched copy | Reset of that epoch propagates on heal | All cleared at epoch 1 | Yes — no zombie latch |
| F13 | Reset then new STOP before heal | Newer epoch STOP survives merge | All latched at epoch 2 | Yes — reset cannot kill a newer STOP |
| F14 | Stale leader routes reset | Rejected; latch retained | STALE_LEADER_REJECTED | Yes |
| F15 | Stale (deposed) leader's node issues STOP | Still latches immediately — leadership not on STOP path | LATCHED | Yes |
| F16 | Conflicting observations STOPPED vs MOVING | Explicit CONFLICTED, never "stopped", latch unchanged (QIP R6) | CONFLICTED, still latched, motion denied | Yes |
| F17 | STOP latched, no observation source | Observed verdict UNKNOWN, not stopped (QIP R6.2/R6.3) | UNKNOWN | Yes — no inferred observation |
| F18 | Merge commutativity / idempotence | merge(a,b)=merge(b,a); merge(a,a)=a | Asserted on latch states | Yes |
| F19 | Scripted scenario replayed | Byte-identical trace + SHA-256 digest | Asserted across two runs | Reproducibility |

## NOT COVERED (explicit gaps — not passes)

| Gap | Why it matters | Needed before any production claim |
|---|---|---|
| Byzantine / malicious replica forging epochs or seen-sets | A forged high epoch could clear or block latches | Signed per-replica state + epoch provenance (QIP R8) |
| Persistence / restart of latch, seen-set, cleared_epoch | Restart amnesia re-opens F5/F8 | Durable store with the R5.1 restart test N4 lacks |
| Real transport: loss, reordering, duplication beyond scripted cases | Delivery order interacts with staleness checks | Transport-level replay/fuzz harness |
| Clock trust / freshness windows | issued_at_epoch is logical, not time-based | QIP R4.3 declared freshness bound + clock source |
| Multi-target and multi-fleet cross-talk | Tests use one target; scope pinning is per-target in code only | Wrong-target rejection tests (QIP R1.2) at fleet layer |
| Leader election safety under partition (split-brain terms) | Two partitions may hold different leaders; only stale-term reset is tested | Election model + partition-merge of terms |
| Physical observation latency / sensor truth | CONFLICTED is a label, not sensing | Real observation source (QIP R6, out of sim scope) |
| QIP conformance | These are simulation tests, not the conformance suite | conformance/ IDs appended only, never renumbered |
