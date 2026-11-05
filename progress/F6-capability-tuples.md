# Wave 5 F6 — Manufacturer capability tuples

Status: complete (attempt 1 of 3; attempts 2-3 not needed)
Base: 35ee2aef6f7a2fcf17e51de40678aee97ba0b350 (35ee2ae)
Branch: wave5/f6
Tier: 1
Owned files only: research/humanoids/** and progress/F6-capability-tuples.md
Not edited: checks.md, graph.md, progress.md, registry candidate/source/
claim records, registry/index.json (universe_size_claim remains null).

## Inputs read

- docs/specs/intervention-profile/QIP-v0.1.md, esp. QIP-R10.1/R10.2
  (declare supported/unsupported kinds; no manufacturer stop/status/
  reset mapping claim unless observed in manufacturer material recorded
  with its source; at v0.1 every such mapping was UNIMPLEMENTED) and
  QIP-R6.1-R6.3, QIP-R11.2.
- research/humanoids/DECISION-PACKET.md (unsigned recommendations only;
  no promotion without a human row in checks.md — none exists).
- docs/specs/intervention-profile/PRIOR-ART.md (N4 api-surfaces gap).
- research/humanoids/registry/{candidates,sources,provenance-claims}.jsonl,
  registry/index.json (25 candidates, 26 sources, 38 claims, all
  candidate_unverified, canonical_name=null, universe_size_claim=null).

## Deliverable

research/humanoids/capability-tuples/
  capability-tuple.schema.json  JSON Schema 2020-12. One tuple =
    entity{candidate_id, seed_name, canonical_name=null,
    entity_verification_status=candidate_unverified} + product +
    capability + adapter{type,name,api_or_method,transport} +
    firmware_or_docs_version + environment{os,language,
    network_or_domain,notes} + evidence{evidence_strength,
    existing_registry_source_ids, source_url, source_title, source_type,
    access_method, accessed_at, locator} + epistemic_status +
    qip_r10{mapping_claimed=false, mapping_status, declaration_status}.
    (Schema lives in capability-tuples/, not schemas/, because the
    pre-existing registry test pins schemas/ to exactly six files and
    this node may not edit tests/.)
  capability-tuples.jsonl  78 tuples, sorted by tuple_id, unique ids.
  README.md  Vocabulary, QIP-R10 discipline, source rule.
research/humanoids/tools/validate_registry.py  Extended (additive):
  schema check, unique cap- ids, candidate/seed match, no-promotion
  guard, mapping_claimed=false guard, observed requires primary_official
  actually-accessed evidence + api_or_method + locator, inferred requires
  mapping_status=inferred_not_claimed, unknown/not_found must not name
  an api_or_method, not_found must carry "not_found in recorded sources
  only", every candidate must have explicit intervention_stop,
  status_observation and latch_reset tuples. Prints capability_tuple
  count + capability_tuple_epistemic_counts.
research/humanoids/tests/test_capability_tuples.py  4 tests, including
  two fail-first fabrication guards (observed-without-method rejected;
  mapping_claimed=true rejected) run against a copied tree.
research/humanoids/README.md  Layout pointer only.

## Population rule and epistemic counts (deterministic, validator output)

Only official sources: (a) already in registry/sources.jsonl, referenced
by existing_registry_source_ids, or (b) newly fetched official pages
recorded verbatim per tuple (URL + locator + accessed_at
2026-11-05T22:32:01Z). New sources were NOT appended to sources.jsonl
(its 26/38 counts are pinned by pre-existing N4 tests; appending would
be an out-of-scope registry change). No candidate was promoted; every
tuple has canonical_name=null and mapping_claimed=false.

Validator raw output (attempt 1):
  python3 research/humanoids/tools/validate_registry.py  -> exit 0
  {"ok": true, "errors": [], "counts": {"company": 25, "source": 26,
   "dataset": 0, "api_surface": 0, "compliance_assessment": 0,
   "provenance_claim": 38, "capability_tuple": 78},
   "capability_tuple_epistemic_counts": {"inferred": 1,
   "not_found": 65, "observed": 6, "unknown": 6},
   "verified_companies": 0}

By capability: intervention_stop=25, status_observation=25,
latch_reset=25, sdk_adapter_availability=3. Total 78.

Observed (6):
- cap-unitree-status: Unitree G1 unitree_sdk2_python LocoClient
  GetFsmId()/GetFsmMode() (official github.com/unitreerobotics repo,
  fetched raw file). Not a QIP observed-stop (R6.3).
- cap-fourier-stop: Fourier GR-3 SDK Overview lists GR-Controller
  "emergency stop" capability (method not named on that page).
- cap-fourier-status: Fourier AuroraClient get_fsm_state()/
  get_fsm_name()/set_fsm_state() (GR-3 v3.0.2 docs).
- cap-{unitree,fourier,ubtech}-sdk: official SDK existence
  (Unitree sdk2/sdk2_python; Fourier Aurora fourier-aurora-client
  ==0.2.1, DDS domain 123; UBTech Walker Tienkung SDK ROS2,
  docs V2.0.4.x, Ubuntu 22.04).

Inferred (1):
- cap-unitree-stop: LocoClient.StopMove()=SetVelocity(0,0,0) and
  Damp()=SetFsmId(1) are observed manufacturer motion commands; their
  equivalence to a QIP STOP is inferred_not_claimed, mapping_claimed=false.

Unknown (6): Tesla Optimus (3) — recorded source not_accessed;
LimX Dynamics (3) — recorded source metadata_only. Neither presence
nor absence asserted.

Not_found (65): all remaining stop/status/reset tuples. Meaning is
scoped: the candidate's recorded official source(s) describe no such
interface. It is not a claim none exists elsewhere (validator enforces
the scoped wording and forbids naming an api_or_method). Boston
Dynamics tuples explicitly note the Spot SDK was excluded as a
different (quadruped) product, not Atlas evidence.

latch_reset: no manufacturer latch/reset semantic was observed for any
candidate in recorded/fetched sources; all 25 are unknown (Tesla/LimX)
or not_found. This preserves the QIP-R10.2 gap honestly rather than
rounding Damp/FSM transitions up to "reset".

## Verification (attempt 1)

- python3 research/humanoids/tools/validate_registry.py -> ok, above.
- python3 -m pytest research/humanoids/tests/test_capability_tuples.py
  tests/test_humanoid_registry.py -q -> 12 passed.
- make test (after make setup; .venv absent at start, no tracked files
  affected) -> 147 passed, 1 skipped.
- git status: only owned paths changed (research/humanoids/README.md,
  research/humanoids/tools/validate_registry.py,
  research/humanoids/capability-tuples/**,
  research/humanoids/tests/test_capability_tuples.py, this file).

Gate attempts: attempt 1 passed locally and (recorded in PR) in CI.
Attempts 2-3 were not needed; no gate was weakened.

## Exact report

Schema defined; 78 tuples populated from official sources only;
observed=6, inferred=1, unknown=6, not_found=65; no promotion,
canonical_name=null everywhere, mapping_claimed=false everywhere,
universe_size_claim=null untouched, checks.md untouched. QIP-R10
manufacturer mapping therefore remains formally UNIMPLEMENTED as a QIP
claim (per R10.2), now with an explicit per-candidate evidence matrix
instead of an unexamined gap. Raw counts are the validator JSON above;
confidence is stated last and adds nothing beyond that evidence.
