# Diligence - README claim map (N7, Wave 4)

Sole README owner: N7. Rule (graph.md R-IMM-4): no claim ahead of
evidence; raw output required. Every README claim below maps to
evidence (full index: docs/evidence/README.md) and to the exact
clean-clone command a stranger can run. Unsupported claims were
removed from README or moved to roadmap wording below.

Clean-clone commands (from a fresh clone, Python 3.11 required):

  With Rust:    make setup && make test && cargo test --workspace
  Without Rust: make setup && make test   (cargo absent from PATH;
                keep python3.11 on PATH - hiding cargo by dropping
                Python 3.11 silently falls back to 3.9 and fails)

## Claim -> evidence -> command

| README claim | Evidence | Clean-clone command |
|---|---|---|
| Simulated STOP workflow; only SimulatedRobotAdapter enabled; not a safety-rated e-stop, no physical control | app code + tests/test_app.py, tests/test_secure_core.py; TEST-RESULTS rows 3-8 | make test |
| Physical Pi + Waveshare 7.5" V2 e-ink QR/LIVE badge working | TEST-RESULTS rows 22/29 (project records; phone scan NOT RUN in row 22) | none in clone - hardware record, not clone-verifiable |
| Authenticated STOP: roles, CSRF, latch, audit, simulator ACK | tests/test_app.py, tests/test_secure_core.py | make test |
| Phone onboarding works with certificate install; not zero-setup | TEST-RESULTS rows 17/23 (row 23 AP step BLOCKED at record time) - README keeps the qualified wording only | none - hardware record |
| Runtime Meta: mock by default; live adapter in code; live inference NOT verified | docs/evidence/meta-live.md (BLOCKED, 0 calls); meta-live-local-contract.md (synthetic only) | .venv/bin/python scripts/meta_live_evidence.py (exits non-zero when blocked) |
| Meta used in development via Hermes (separate from runtime) | docs/BUILT-DURING-HACKATHON.md | none - process record |
| Cellular Tele2 EC25 HTTP 200 data test; no failover claim | TEST-RESULTS row 28 (project record) | none - hardware record |
| GNSS reader present, NO_FIX indoors, no accuracy claim | TEST-RESULTS row 26; parser tests in tests/test_app.py | make test |
| Voice/gesture: deterministic recognizers, STOP-only API, no mic/camera capture | docs/INTERVENTION-INPUTS.md; tests/test_safety_inputs.py | make test |
| Isaac Sim: bridge contract + fail-closed adapter; Isaac Sim not installed/run, not runtime-enabled | docs/ISAAC-SIM-INTEGRATION.md; adapters/isaac_sim.py tests | make test |
| Frontier Phase 1 registry: 6 schemas, 25 unverified candidates, validator, roadmaps; no verified companies/universe claim | research/humanoids/; validator run "ok, 25/26/38, verified 0" (N7 re-ran it) | python3 research/humanoids/tools/validate_registry.py |
| Rust secure core Increment 2 (envelope, epoch, revocation scaffolding, audit anchor, fail-closed capacity, custody modes, rate limiting); STOP-only, simulation only, not certified/HSM/OTA/SLSA | docs/SECURE-CORE.md; tests/test_secure_core.py; cargo tests 14+3 | cargo test --workspace --all-features; make test |
| Degraded matrix: ACCEPTED / unavailable-UNSIGNED / reachable-REJECTED for STOP, task, reset | README matrix; docs/evidence/lane-a-p0/SUMMARY.md; wave3-n2 10x logs; named tests test_stop_executes_without_secure_core_but_reset_does_not, test_stop_rejected_by_secure_core_does_not_invoke_adapter | make test (both modes) |
| Frontier thesis "model proposes; deterministic law disposes" | docs/FRONTIER.md (thesis doc, labelled as such) | none - argument, not a result |
| Wave 3 adversarial pilot results | research/adversarial/evidence/adversarial-pilot.md - WITH CAVEAT: Wave 3 pilot cases are same-agent deterministic templates; this is weak evidence until an independent model adversary runs cases. 9 escapes (NaN 500, oversize echo) are routed, not fixed | .venv/bin/python -m pytest research/adversarial/tests/ -q |
| Copper STOP record/replay byte-identical | spikes/copper-stop-path/evidence/comparison.txt, verify.log | python3 spikes/copper-stop-path/verify.py (see spike README) |

## Test counts - reconciled, not universalised

Stale counts in repo and why none is "the" count: 11 (TEST-RESULTS,
early), 17/21 (final-check), 44 (old README), 48/37 (Lane A commit),
55+11 (N4 worktree), 65 (N6), 68 / 57+11 (N2 10x logs). Each was true
for its commit, host, Python, and Rust mode. README no longer prints a
single Latest-run count as a headline fact.

N7 verification at baa18a1 (this Mac, Python 3.11.15, 2026-11-05):
with Rust 80 passed; without Rust 69 passed + 11 skipped; Rust
17 passed (14 core + 3 CLI). Raw lines: progress/N7-diligence.md.
A Mac pass is not a Pi or Isaac-host pass; a Python 3.9 fallback run
failed 1 GNSS test, so Python 3.11 is part of the claim.

## Removed / downgraded in README by N7

- "44 passed" latest-run line: replaced by the reconciled wording above.
- cargo audit / cargo deny / SBOM (98 components) in the README
  latest-run line: no committed raw output in the evidence index;
  downgraded to the dated point-in-time record in docs/SECURE-CORE.md
  (not a standing README claim). CI runs these gates - CI output after
  Tier 1 settles is the place to re-claim them.
- Fuzz smoke: README previously said "not run (exit 77)"; kept only as
  not-run, no result claimed.
- test-evidence.svg embedding: removed from README; a graphic is not
  raw evidence (file itself not N7-owned, left in place).

## Roadmap (explicitly not claimed)

Live Meta inference; microphone/camera capture; Isaac Sim run;
physical humanoid control / certified e-stop; Pi deployment of the
secure-core gate; independent-model adversarial corpus (replacing the
same-agent deterministic-template pilot); manufacturer-interface
matrix for the intervention profile (N6 R10 gap); HSM, secure OTA,
SLSA provenance; failover/continuous cellular; RTK/accuracy GNSS.
