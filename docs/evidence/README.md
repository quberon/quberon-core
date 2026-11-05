# Evidence index (N7, Wave 4)

This index points to evidence wherever it already lives. Nothing was
relocated, renamed, or copied by N7. Every item states what it shows
and, with equal weight, what it does NOT show. A test count in any item
is valid only for the commit, host, interpreter, and mode recorded in
that item; no count here is a universal count (see docs/DILIGENCE.md).

Base for N7 verification: baa18a1522aeb9dc5865afbbfffe89fc94de2ece
(origin/main at N7 start, after Wave 3 merged).

## Committed evidence

| Location | Shows | Does NOT show |
|---|---|---|
| docs/evidence/final-check.md + pytest-final.txt | Early final pass on Mac/Python 3.11: 17 then 21 passed at that commit; fixes A/B/C/E/F verified by named tests | Current suite size or pass at HEAD; any Pi, phone, live-model, or robot run |
| docs/evidence/lane-a-p0/SUMMARY.md | Lane A degraded-mode semantics; fresh-clone runs at ca8cd4d: 48 passed with Rust, 37 passed + 11 skipped without, Rust 17 passed; flake root cause (orphaned uvicorn) | Counts at HEAD (suite has since grown); a Pi pass; that the secure-core gate is deployed on the Pi (it records the opposite) |
| docs/evidence/lane-a-p0/fresh-clone-with-rust.log, fresh-clone-without-rust.log | Raw fresh-clone output for the two modes at that commit | HEAD behaviour; counts transferable to other hosts/Python versions |
| docs/evidence/lane-a-p0/main-fresh-clone-with-rust-python311.log | Same, on merged main at that time (48 passed) | HEAD counts |
| docs/evidence/lane-a-p0/main-fresh-clone-without-rust-python311.log | Without-Rust merged-main run (37 passed, 11 skipped) | HEAD counts; behaviour under Python != 3.11 |
| docs/evidence/lane-a-p0/main-fresh-clone-with-rust-python39-failed.log | Python 3.9 failure (1 failed, 47 passed): Python 3.11 is required in practice | That the suite is broken on the documented Python 3.11 |
| docs/evidence/lane-a-p0/pi-readonly-inspection.log | Read-only Pi inspection: deployed Pi app has no secure-core gate/CLI | Any Pi test pass for current code; permission to deploy |
| docs/evidence/lane-a-p0/flake-diagnosis.md | Diagnosis of intermittent port-8000 leakage and its fix | That no other flake exists |
| docs/evidence/wave3-n2/with-rust-10x.log | Wave 3 N2: 10/10 consecutive runs, 68 passed each, at that commit, with Rust | HEAD counts; without-Rust behaviour |
| docs/evidence/wave3-n2/without-rust-10x.log | 10/10 runs, 57 passed + 11 skipped each, without Rust, at that commit | HEAD counts; with-Rust behaviour |
| docs/evidence/meta-live.md | One-shot live Meta attempt: BLOCKED, 0 provider calls, missing META_API_URL/META_API_KEY/META_MODEL | That live Meta inference works (it explicitly does not show this) |
| docs/evidence/meta-live-local-contract.md | Offline fake-server contract tests pass (exactly-one-call, redaction, advisory boundary) | A real Meta/provider call; live inference; credential handling in production |
| research/adversarial/evidence/adversarial-pilot.md (+ full-run.txt, generate.txt, hand-run.txt, invariant-failing-fixtures.txt, nan-root-cause.txt; results/ beside it) | Wave 3 N5 pilot: 5,206 deterministic-template cases, 5,412 results, 0 S0, 9 escape records (NaN HTTP 500; oversize echo) routed to app owner. MANDATORY CAVEAT: the pilot cases are same-agent deterministic templates, so this is weak evidence until an independent model adversary generates/runs cases | Robustness against an independent adversary, a live model, or novel human attacks; that the two escapes are fixed (they are routed, not fixed, in N5) |
| spikes/copper-stop-path/evidence/ (comparison.txt, verify.log, *.bin, *.copper) | Copper spike: recorded STOP replayed with byte-identical task outputs (39 bytes) and keyframes | Production integration, latency guarantees, Pi/physical behaviour; Copper is a spike workspace, root MSRV untouched |
| research/humanoids/ (registry/, tools/validate_registry.py) + progress/N4-registry-dedup.md | 25 unverified seed candidates, 38 provenance claims, validator ok, 0 verified companies; dedup/scope are proposals only | Any verified company, universe size, legal-entity conclusion, or applied dedup/scope |
| docs/specs/intervention-profile/ (PRIOR-ART, OUTLINE, TRACEABILITY) + progress/N6-profile-draft.md | Gate-zero prior art and R1-R11 traceability to named tests or explicit gaps | Standards conformity, physical safety validation, manufacturer-interface grounding (api-surfaces is empty; R10 is a gap) |
| TEST-RESULTS.md (rows 1-29, repo root) | Dated project records incl. Pi/e-ink (rows 22/29), cellular HTTP 200 (row 28), Pi flows, latency (software only) | Re-runnable raw logs for most rows; current-code Pi results; physical stop times. Rows are records, not committed raw output, unless a row says otherwise |
| progress/N0..N6-*.md | Per-node Wave 3 reports with raw snippets and ownership | Independent review; N0 assembly of graph/checks/progress at wave close is still pending in those files |
| docs/assets/test-evidence.svg | An illustration embedded in README historically | Evidence. It is a graphic, not raw output; N7 removed its README embedding as a claim surface (file left in place, not owned by N7) |

## N7's own verification (recorded in progress/N7-diligence.md, not new evidence files)

Clean clones of baa18a1 on this Mac (Python 3.11.15): with Rust
80 passed; without Rust (Python 3.11 kept, cargo hidden) 69 passed +
11 skipped; cargo test 17 passed (14+3); fmt/clippy clean. A PATH that
silently fell back to Python 3.9 failed 1 GNSS test - exactly why no
count is universalised. These runs are N7 session output, preserved in
progress/N7-diligence.md; they are not a substitute for CI or for a
stranger's clean-machine run after Tier 1 settles.
