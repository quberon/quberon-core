# LIMITATIONS — what is not true

Canonical statement, assembled 2026-11-06 from the limitation, NOT TESTED,
claim-discipline, unsupported, and roadmap sections already in
`progress/*.md` and `docs/DILIGENCE.md`. This file is the single place to
check before repeating any claim about this repository. It does not add
new evidence and it upgrades nothing.

Append-only thereafter: never edit, delete, shorten, or silently rewrite
an entry below. If an entry stops being true, append a dated supersession
entry at the end that names the old entry, the new evidence path, the
commit, host, toolchain, and clean-clone command that retire it. If an
entry is wrong, append a dated correction; do not erase the original.

No certification, physical-safety, latency, or regulatory-compliance
claim is ever supported by this repository. That sentence is not
qualified by any test pass in any mode.

## 1. Physical control and safety

- This system does not control physical robot hardware. Only
  `SimulatedRobotAdapter` is enabled. (README.md status table;
  docs/DILIGENCE.md claim map)
- It is not a safety-rated emergency stop and no certified e-stop exists.
  (README.md; progress/N3-evidence-bundle.md; progress/F2-bundle-vectors.md)
- No physical stopping time, physical response time, physical reset,
  real-controller restart/reconnect, or physical state after a STOP has
  been measured or shown. (progress/N4-conformance.md;
  progress/F1-degraded-conformance.md; progress/F3-stop-load.md)
- There is no independent physical-state sensing and no bound on
  observation latency. Simulated `SIMULATED_STOPPED` / `UNKNOWN`
  vocabulary is not physical observation. (progress/N4-conformance.md;
  progress/F1-degraded-conformance.md)
- Software latency figures in project records are not physical stop
  times, and an e-ink LIVE badge refresh does not prove robot-connection
  freshness. (README.md "Known limitations")
- Fleet latch work is simulated replicas only: no real transport,
  persistence/restart, Byzantine replicas, clock trust, election safety
  under split-brain, or physical observation. It is not physical-safety
  evidence. (progress/F5-fleet-latch.md)
- The single-process app is not multi-instance safe: the in-memory latch
  cache is documented as single active instance only. Fleet coherence
  above is a simulation design, not a deployed settlement.
  (README.md "Known limitations"; progress/F5-fleet-latch.md)

## 2. Latency, load, and real-time behaviour

- No latency claim is made. STOP-under-load numbers are local Mac
  simulation observations for relative comparison inside one run only:
  timing isolation on that host failed calibration, the host was shared,
  and tails were unstable across attempts. (progress/F3-stop-load.md)
- Those numbers are not Pi figures, not hardware figures, not a deadline,
  not a starvation bound, and not a network-partition result.
  (progress/F3-stop-load.md)
- Still unmeasured: successful-task lock contention, network partition,
  Rust-core subprocess under load, Pi execution, and any
  deadline/starvation bound. (progress/F3-stop-load.md)
- Planner saturation not blocking simulated STOP in that run is
  best-effort isolation, not a real-time guarantee.
  (README.md "Known limitations"; progress/F3-stop-load.md)
- Copper record/replay is simulated tasks, one iteration, mock clock:
  byte-identical replay is shown, latency is not.
  (progress/N3-copper.md)

## 3. Certification, standards, and legal conformity

- No standards conformance is claimed: not PL, not SIL, not a completed
  hazard analysis, not legal conformity. Conformance-suite passes are
  for this simulator's scope and are not standards conformance (R11).
  (progress/N4-conformance.md; progress/F1-degraded-conformance.md;
  progress/N5-qip-v01.md)
- No QIP class is claimed in QIP v0.1, and no QIP class claim is made
  anywhere in the assurance pack. (progress/N5-qip-v01.md;
  progress/F7-repro-assurance.md)
- EU Machinery Regulation and AI Act material in the assurance pack is
  unresolved research questions only: no applicability or compliance
  conclusion. (progress/F7-repro-assurance.md)
- Paywalled prior art marked `scope and abstract reviewed; full text not
  reviewed` supports no detailed clause or threshold claim.
  (progress/N6-profile-draft.md; progress/N5-qip-v01.md)

## 4. Secure core, signing, and custody

- The Rust secure core is simulation-only, STOP-authorisation-only, and
  not externally reviewed, audited, or certified. (README.md;
  docs/DILIGENCE.md claim map)
- There is no HSM, no TPM custody claim, no secure OTA, and no SLSA
  provenance claim. Production/development key-custody modes in code are
  not HSM custody. (README.md; progress/N3-evidence-bundle.md;
  docs/DILIGENCE.md "Roadmap")
- Bundled-key verification proves internal consistency only, never signer
  authority. A rebuilt bundle re-signed with an attacker's own bundled
  key passes as `PASS_LIMITED_CLAIMS` in both checkers; only an externally
  pinned key rejects it. (progress/F2-bundle-vectors.md;
  progress/N3-evidence-bundle.md)
- Evidence-bundle PASS supports only: internal SHA-256 integrity, audit
  hash-chain linkage, envelope signature for the bundled key, an ACCEPTED
  simulation STOP decision, Copper replay byte-identity, and that a STOP
  was recorded. Nothing else. (progress/N3-evidence-bundle.md;
  progress/F2-bundle-vectors.md)
- Real Rust rejection of a signed envelope, signed-attestation
  verification, and sequence/epoch handling under refusal were not
  exercised by the F1 conformance injection: it used a stub authority and
  no signing. (progress/F1-degraded-conformance.md)
- Without the Rust binary, STOP is unsigned by design and must never be
  reported as signed; reset and simulated task stay blocked in that mode.
  (README.md degraded-mode matrix)
- Runtime DB failure fails closed in the tested paths, but authentication
  also depends on the DB, so this is not an always-available
  emergency-stop path. (README.md "Known limitations")

## 5. Degraded mode, persistence, audit, and conformance gaps

- Real disk/SQLite persistence failure and restart recovery from it are
  not tested: F1 injection flips the app's degraded flag, it does not
  corrupt storage. (progress/F1-degraded-conformance.md)
- Adapter non-invocation under refusal is inferred from UNKNOWN / latch /
  audit outcomes, not counted on a real adapter.
  (progress/F1-degraded-conformance.md)
- QIP requirements traced UNIMPLEMENTED stay UNIMPLEMENTED until the
  profile owner's own amendment procedure runs. F1's injected DEG-03 pass
  does not by itself amend QIP-R7.1/QIP-R7.4, and F3 load evidence does
  not promote QIP-R3.1/R3.2. (progress/F1-degraded-conformance.md;
  progress/F3-stop-load.md; progress/Wave5-assembly.md)
- Audit coverage is in-app event existence/dedup/auth only: no retention,
  clock trust, export, tamper-evidence, or custody claim.
  (progress/N4-conformance.md; progress/F1-degraded-conformance.md)
- The earlier N4 shortfalls superseded in part by F1/F3/F5 work are not
  deleted here; the surviving gaps are the ones in this section and
  sections 1-2. Historical per-node wording remains in those files.

## 6. Live models, planners, and adversarial evidence

- Live runtime Meta inference is NOT verified. The recorded attempt is
  BLOCKED with 0 provider calls; the runner repair was offline only, and
  any new real call needs fresh explicit authorisation.
  (docs/DILIGENCE.md claim map; progress/F8-meta-runner.md;
  progress/Wave5-assembly.md)
- Mock is the default planner; offline fake-server contract tests show no
  real provider call, live inference, or production credential handling.
  (docs/evidence/README.md; progress/N4-conformance.md)
- Adversarial corpora are deterministic templates authored in the same
  agent family as the validator. Even at full scale with 0 escapes, that
  is weak evidence: it does not prove robustness against an independent
  model adversary, a live provider, novel human attacks, physical
  robots, or certification criteria. A real-model adversary is BLOCKED
  (no application provider credentials). (progress/N2-full-adversarial.md;
  progress/N5-adversarial.md; progress/Wave5-assembly.md;
  docs/DILIGENCE.md claim map)
- Adversarial detection walks are bounded (4096 nodes / 32 path depth);
  string-form non-finite detection covers exact tokens and numeric
  strings that overflow float, nothing broader is claimed.
  (progress/N1-adversarial-hardening.md)

## 7. Voice, gesture, and other intervention inputs

- Voice/gesture results are synthetic only: no sensor, microphone,
  camera, speaker, person, field, or learned-model qualification exists.
  There is no microphone/camera capture. (progress/F4-input-qualification.md;
  README.md; docs/DILIGENCE.md claim map)
- Known synthetic limits stay documented, including one false trigger
  (`V-NEG-08`, "the bus stop is near") and high deliberate-abstention
  missed-trigger rates at boundaries. (progress/F4-input-qualification.md)
- Stale/replayed voice inputs are stopped by harness freshness/replay
  layers, not by the recognizer alone. (progress/F4-input-qualification.md)
- QIP-R9.1 traceability is unchanged and UNIMPLEMENTED in profile terms;
  no sensor qualification follows from the harness.
  (progress/F4-input-qualification.md)
- The Wave 6 gesture dataset protocol is a protocol and synthetic
  examples only: no Pi/camera access, no model training, no sensor
  qualification claim. (progress/Gesture-dataset-protocol.md)

## 8. Isaac Sim and external simulators

- Isaac Sim is not installed, not run, and its adapter is not
  runtime-enabled. What exists is a versioned bridge contract,
  deterministic local transport, and a fail-closed adapter.
  (README.md; docs/DILIGENCE.md claim map)

## 9. Manufacturers, registry, and QIP R10

- No verified company exists in the humanoid registry: 25 candidates are
  all `candidate_unverified`, `canonical_name=null`, verified count 0,
  and `universe_size_claim` is null. No universe-size claim is made.
  (progress/N6-registry-decisions.md; progress/F6-capability-tuples.md;
  docs/DILIGENCE.md claim map)
- Dedup, scope, and entity classifications are proposals for human
  decision only; signing a packet authorises recording a decision, it
  does not itself change any registry record. Human decisions for all 25
  candidates remain pending. (progress/N4-registry-dedup.md;
  progress/N6-registry-decisions.md; progress/Wave5-assembly.md)
- QIP R10 manufacturer mapping remains formally UNIMPLEMENTED as a QIP
  claim: of 78 capability tuples, observed 6, inferred 1, unknown 6,
  not_found 65, `mapping_claimed=false` everywhere, and no manufacturer
  latch/reset semantic was observed for any candidate. `not_found` means
  only "not in the recorded sources", never "does not exist".
  (progress/F6-capability-tuples.md)
- Tesla Optimus is unassessed (source not accessed) and LimX Dynamics is
  metadata-only; neither presence nor absence of an interface is asserted
  for them. (progress/F6-capability-tuples.md;
  progress/N6-registry-decisions.md)
- A full normative manufacturer-grounded profile remains blocked on the
  manufacturer-interface matrix and its review.
  (progress/N6-profile-draft.md)

## 10. Pi, phone, cellular, GNSS, and deployment

- A Mac test pass is not a Pi pass and not an Isaac-host pass. The
  read-only Pi inspection on record found the deployed Pi app contains
  no secure-core gate and no secure-core CLI, so the gate is not deployed
  on the Pi. (README.md; docs/DILIGENCE.md claim map)
- Wave 6 Pi readiness is a runbook and read-only probe only: Pi success
  path, camera capture, health endpoint, and deployed inventory are NOT
  RUN, and no deploy is authorised by that prep. Prior Pi facts in it are
  dated hypotheses to re-verify. (progress/Pi-readiness.md)
- Phone onboarding is not zero-setup and is not claimed as frictionless:
  it works with certificate install. (README.md;
  docs/DILIGENCE.md claim map)
- Cellular evidence is a project-recorded HTTP 200 data test only: no
  failover and no continuous-service claim. (README.md;
  docs/DILIGENCE.md claim map)
- GNSS is a reader with NO_FIX indoors: no RTK and no accuracy claim.
  (README.md; docs/DILIGENCE.md claim map)
- Pi/e-ink, phone, and cellular rows are project records, not
  clean-clone-verifiable evidence. (docs/DILIGENCE.md claim map)

## 11. Counts, reproducibility, and standing claims

- No test count is universal. Every count is valid only for its commit,
  host, Python version, and Rust mode; a PATH that silently falls back to
  Python 3.9 fails, so Python 3.11 is part of every count claim.
  (docs/DILIGENCE.md "Test counts"; progress/N7-diligence.md)
- cargo audit, cargo deny, and SBOM figures are dated point-in-time
  records in docs/SECURE-CORE.md, not standing claims; CI output is the
  place to re-claim them. (docs/DILIGENCE.md "Removed / downgraded")
- Fuzz smoke is not run and no result is claimed for it.
  (README.md; docs/DILIGENCE.md "Removed / downgraded")
- A generated SBOM hash was byte-identical across two runs, but the built
  secure-core binary hash differed across build directories: no
  byte-reproducible-binary claim is made. (progress/F7-repro-assurance.md)
- A graphic (docs/assets/test-evidence.svg) is not raw evidence and was
  removed as a README claim surface. (docs/DILIGENCE.md;
  docs/evidence/README.md)
- Historical counts and snapshots (44/48/68/65 and similar) outside their
  commit-and-mode context are stale and must not be quoted as current.
  (progress/n7-requests.md; docs/DILIGENCE.md)

## 12. Roadmap items explicitly not claimed

From docs/DILIGENCE.md "Roadmap (explicitly not claimed)", still not true:

live Meta inference; microphone/camera capture; an Isaac Sim run;
physical humanoid control; a certified e-stop; Pi deployment of the
secure-core gate; an independent-model adversarial corpus replacing the
same-agent template pilot; a manufacturer-interface matrix for the
intervention profile (R10 gap); HSM; secure OTA; SLSA provenance;
failover/continuous cellular; RTK/accuracy GNSS.

## Sources assembled

docs/DILIGENCE.md (all sections); progress/F1-degraded-conformance.md;
progress/F2-bundle-vectors.md; progress/F3-stop-load.md;
progress/F4-input-qualification.md; progress/F5-fleet-latch.md;
progress/F6-capability-tuples.md; progress/F7-repro-assurance.md;
progress/F8-meta-runner.md; progress/Gesture-dataset-protocol.md;
progress/N1-adversarial-hardening.md; progress/N2-full-adversarial.md;
progress/N3-copper.md; progress/N3-evidence-bundle.md;
progress/N4-conformance.md; progress/N4-registry-dedup.md;
progress/N5-adversarial.md; progress/N5-qip-v01.md;
progress/N6-profile-draft.md; progress/N6-registry-decisions.md;
progress/N7-diligence.md; progress/Pi-readiness.md;
progress/Wave5-assembly.md; progress/n7-requests.md; README.md
"Known limitations" and degraded-mode matrix (quoted, not edited by
this node). progress/N0-housekeeping.md and progress/N2-lifecycle.md
contain no additional not-true claim beyond the fail directions and
Python 3.11 requirement already covered above.

## Append-only log

- 2026-11-06: file created by node w5-n6-limitations from the sources
  above. No entry below this line existed at creation. Append new
  entries below, dated, with evidence paths; never edit entries above.
