# Wave 5 assembly — post-merge adversarial verification

Base assembled: `c19501c8b8e4008fcc6724964baa57be158f62bd`

## Wave 5 nodes merged

| Node | PR(s) | Result |
|---|---|---|
| F1 degraded conformance | #27, #35 | QIP-DEG-03 active; persistence-degraded and reachable-refusal injected; conformance 28 passed with core |
| F2 evidence-bundle vectors | #30 | Independent Python checker 17/17; cross-implementation parity; rebuild-and-resign limitation explicit |
| F3 STOP under load | #34 | Behavioral fail-direction held under simulated load; timing isolation negative, no latency claim |
| F4 safety inputs | #31, #36 | Synthetic voice/gesture boundaries with denominators; one known false trigger documented |
| F5 fleet latch | #28 | 18 deterministic simulation tests; local STOP never waits for consensus |
| F6 capability tuples | #32 | 78 tuples; observed 6, inferred 1, unknown 6, not_found 65; no promotion |
| F7 reproducibility | #33 | Clean-clone pack; 51-row claim checklist; SBOM byte-identical, binary not claimed reproducible |
| F8 Meta runner repair | #29 | Offline repair only; zero real calls; live Meta still unverified |

## Post-merge adversarial rerun

After PR #24 merged, the full deterministic template corpus was rerun on merged main:

- Results: 63,012
- Escapes: 0 (pre-hardening: 300 records / 200 payloads)
- S0 violations: 0
- Accepted in error: 0
- Benign false rejects: 0 / 22,692 acceptance-permitted results
- Invariant violations: 0 for I1–I10

Evidence: `research/adversarial/evidence/adversarial-postmerge.md`, raw log `postmerge-full-run.txt`, summary `research/adversarial/results/postmerge-summary.json`.

Mandatory limitation: the corpus remains deterministic templates authored in the same agent family as the validator. It does not prove robustness against an independent model adversary, live provider behavior, physical robots, or certification criteria.

## Remaining frontier blockers

- Human registry decisions for the 25 candidates remain pending; no promotion is authorized by the packets alone.
- QIP v0.1 still contains explicit UNIMPLEMENTED requirements; F1's DEG-03 pass requires a deliberate QIP amendment before R7 wording can change.
- Live Meta inference remains unverified. F8 repaired the runner offline; any new real call needs fresh explicit authorization and must preserve failed attempts.
- Physical hardware, Pi deployment, manufacturer integrations, and legal/certification conclusions remain out of scope without separate authorization and evidence.
