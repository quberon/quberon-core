# Manufacturer capability tuples (Wave 5 F6, QIP R10)

Machine-readable capability tuples for the 25 registry candidates.
This directory is the F6 deliverable; it does not edit the registry
records in ../registry/, does not promote any candidate, and keeps
registry/index.json universe_size_claim=null (index.json untouched).

Files:
  capability-tuple.schema.json  JSON Schema 2020-12 for one tuple.
  capability-tuples.jsonl       One tuple per line, sorted by tuple_id.

Tuple shape (schema is normative for this directory):
  entity (candidate_id, seed_name, canonical_name=null,
          entity_verification_status=candidate_unverified)
  + product + capability + adapter {type, name, api_or_method, transport}
  + firmware_or_docs_version + environment {os, language,
    network_or_domain, notes}
  + evidence {evidence_strength, existing_registry_source_ids,
    source_url, source_title, source_type, access_method, accessed_at,
    locator}
  + epistemic_status + qip_r10 {mapping_claimed=false, ...} + notes

Capability vocabulary (QIP-v0.1 R10-aligned):
  intervention_stop, status_observation, latch_reset (explicit tuple
  for every candidate, even when unknown/not_found),
  sdk_adapter_availability (extra, only where observed).

Epistemic vocabulary (never conflated, QIP-R6/R10 spirit):
  observed   Manufacturer method/capability was seen in manufacturer
             material fetched/recorded for this tuple, with locator.
             Observed manufacturer motion commands are NOT thereby a
             QIP observed-stop (QIP-R6.3).
  inferred   A manufacturer method was observed, but its equivalence
             to the QIP capability is an inference by us. Always
             mapping_status=inferred_not_claimed.
  unknown    The recorded official source was not_accessed or
             metadata_only, so neither presence nor absence is asserted.
  not_found  The recorded official source(s) for that candidate were
             reviewed and describe no such interface. Scoped wording
             is mandatory: "not_found in recorded sources only" — never
             a claim that no interface exists anywhere.

QIP R10 discipline:
  QIP-R10.1: unsupported kinds are declared unsupported (not_found /
  unknown tuples above), never approximated.
  QIP-R10.2: qip_r10.mapping_claimed is false for every tuple in this
  wave. Where a manufacturer stop/status method was observed, the
  tuple records the method and marks the QIP mapping
  observed_manufacturer_command_not_qip_claimed or inferred_not_claimed.
  No QIP class, certification, or physical-safety claim is made
  (QIP-R11.2). Research only; no physical control was attempted.

Sources: only (a) official sources already in ../registry/sources.jsonl
(referenced by existing_registry_source_ids) or (b) official pages/repos
newly fetched in this wave and recorded verbatim per tuple (source_url
+ locator + accessed_at). New sources were NOT appended to
sources.jsonl: that file's counts are pinned by the signed-off N4
registry tests, and appending would be a registry change outside the
no-promotion rule for this node.

Validate: python3 research/humanoids/tools/validate_registry.py
(enforces the tuple guards and prints capability_tuple counts.)
