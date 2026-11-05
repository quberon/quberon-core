#!/usr/bin/env python3
"""Stdlib-only validator for research/humanoids/.

This is NOT a general JSON Schema engine. It checks that the shipped schemas
are well-formed JSON Schema documents and enforces the registry invariants
that must never drift:

  * every seed name is preserved exactly, once, as a candidate + alias;
  * no candidate is marked verified/partially_verified without evidence
    source IDs, a named reviewer and a review timestamp;
  * canonical_name stays null until verification exists;
  * no API endpoint / dataset licence / compliance conclusion may be marked
    verified without source IDs (fabrication guard);
  * record IDs are unique and match their kind prefix;
  * the registry index never asserts a universe size (no 'exactly N
    companies' claim without evidence).

Exit code 0 = clean, 1 = violations. No network access is ever performed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILES = {
    "company": "company.schema.json",
    "source": "source.schema.json",
    "dataset": "dataset.schema.json",
    "api_surface": "api-surface.schema.json",
    "compliance_assessment": "compliance-assessment.schema.json",
    "provenance_claim": "provenance-claim.schema.json",
}
REGISTRY_FILES = {  # kind -> (file, id field, id prefix)
    "company": ("candidates.jsonl", "record_id", "cand-"),
    "source": ("sources.jsonl", "source_id", "src-"),
    "dataset": ("datasets.jsonl", "dataset_id", "ds-"),
    "api_surface": ("api-surfaces.jsonl", "api_id", "api-"),
    "compliance_assessment": ("compliance.jsonl", "assessment_id", "cmp-"),
    "provenance_claim": ("provenance-claims.jsonl", "claim_id", "claim-"),
}
UNVERIFIED = {"candidate_unverified"}
EVIDENCED = {"partially_verified", "verified"}


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records, errors = [], []
    if not path.exists():
        return records, [f"missing registry file: {path.name}"]
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}:{lineno}: invalid JSON: {exc}")
    return records, errors


def check_verification(rec: dict, label: str, errors: list[str]) -> None:
    ver = rec.get("verification")
    if not isinstance(ver, dict) or "status" not in ver:
        errors.append(f"{label}: missing verification.status")
        return
    if ver["status"] in EVIDENCED:
        if not ver.get("evidence_source_ids"):
            errors.append(f"{label}: {ver['status']} without evidence_source_ids (fabrication guard)")
        if not ver.get("reviewed_by") or not ver.get("reviewed_at"):
            errors.append(f"{label}: {ver['status']} without reviewed_by/reviewed_at")


def validate(root: Path = ROOT) -> dict:
    errors: list[str] = []
    schemas = {}
    for kind, fname in SCHEMA_FILES.items():
        path = root / "schemas" / fname
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - report, never crash
            errors.append(f"schema {fname}: unreadable: {exc}")
            continue
        schemas[kind] = doc
        if doc.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"schema {fname}: not a JSON Schema 2020-12 document")
        if not doc.get("$id") or not doc.get("required") or doc.get("type") != "object":
            errors.append(f"schema {fname}: missing $id/required/type=object")
    ids = [d.get("$id") for d in schemas.values()]
    if len(ids) != len(set(ids)):
        errors.append("schema $id values are not unique")

    all_ids: set[str] = set()
    counts: dict[str, int] = {}
    seed_names: list[str] = []
    for kind, (fname, id_field, prefix) in REGISTRY_FILES.items():
        records, errs = load_jsonl(root / "registry" / fname)
        errors.extend(errs)
        counts[kind] = len(records)
        for rec in records:
            rid = rec.get(id_field, f"<missing {id_field}>")
            label = f"{fname}:{rid}"
            if not str(rid).startswith(prefix):
                errors.append(f"{label}: id must start with {prefix!r}")
            if rid in all_ids:
                errors.append(f"{label}: duplicate record id")
            all_ids.add(rid)
            if kind != "provenance_claim":
                check_verification(rec, label, errors)
            if kind == "company":
                names = rec.get("candidate_names") or []
                seed_names.extend(names)
                if rec.get("verification", {}).get("status") in UNVERIFIED and rec.get("canonical_name") is not None:
                    errors.append(f"{label}: unverified candidate must keep canonical_name=null")
                if not set(names).issubset(set(rec.get("aliases") or [])):
                    errors.append(f"{label}: candidate_names must be preserved in aliases")
            if kind == "api_surface":
                for ep in rec.get("endpoints") or []:
                    if ep.get("status") != "candidate_unverified" and not ep.get("source_ids"):
                        errors.append(f"{label}: endpoint {ep.get('name_or_path')!r} evidenced without source_ids")
                safety = rec.get("safety") or {}
                if safety.get("deployment_status") != "research_only_no_physical_control":
                    errors.append(f"{label}: api surface must remain research_only_no_physical_control")
            if kind == "dataset":
                lic = (rec.get("license") or {}).get("status", "")
                if lic.startswith("verified") and not (rec.get("license") or {}).get("license_source_ids"):
                    errors.append(f"{label}: verified licence claim without license_source_ids")

    index_path = root / "registry" / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"registry/index.json unreadable: {exc}")
        index = {}
    if index.get("universe_size_claim") is not None:
        errors.append("index.json asserts a universe_size_claim without evidence (forbidden)")
    if index.get("candidate_count") != counts.get("company"):
        errors.append("index.json candidate_count does not match candidates.jsonl")
    expected_seeds = index.get("seed_names_preserved_exactly") or []
    if sorted(expected_seeds) != sorted(seed_names):
        errors.append("candidate_names in candidates.jsonl do not exactly match index seed list")
    if len(seed_names) != len(set(seed_names)):
        errors.append("duplicate seed names in candidates.jsonl")

    source_ids = {
        rec.get("source_id")
        for rec in load_jsonl(root / "registry" / "sources.jsonl")[0]
    }
    claim_ids = {
        rec.get("claim_id")
        for rec in load_jsonl(root / "registry" / "provenance-claims.jsonl")[0]
    }
    company_records = load_jsonl(root / "registry" / "candidates.jsonl")[0]
    company_ids = {rec.get("record_id") for rec in company_records}
    for rec in company_records:
        label = f"candidates.jsonl:{rec.get('record_id')}"
        missing_sources = set(rec.get("sources") or []) - source_ids
        missing_claims = set(rec.get("provenance_claim_ids") or []) - claim_ids
        if missing_sources:
            errors.append(f"{label}: unknown source references: {sorted(missing_sources)}")
        if missing_claims:
            errors.append(f"{label}: unknown claim references: {sorted(missing_claims)}")

    source_records = load_jsonl(root / "registry" / "sources.jsonl")[0]
    source_urls = [rec.get("url") for rec in source_records]
    if len(source_urls) != len(set(source_urls)):
        errors.append("duplicate official source URLs in sources.jsonl")

    claim_records = load_jsonl(root / "registry" / "provenance-claims.jsonl")[0]
    sources_by_id = {rec.get("source_id"): rec for rec in source_records}
    for rec in claim_records:
        label = f"provenance-claims.jsonl:{rec.get('claim_id')}"
        if not rec.get("source_ids"):
            errors.append(f"{label}: claim must reference at least one official source URL")
        missing_sources = set(rec.get("source_ids") or []) - source_ids
        if missing_sources:
            errors.append(f"{label}: unknown source references: {sorted(missing_sources)}")
        for sid in rec.get("source_ids") or []:
            src = sources_by_id.get(sid)
            if src is None:
                continue
            if src.get("source_type") not in {"official_site", "official_docs"}:
                errors.append(f"{label}: source {sid} is not an official source")
            if not str(src.get("url") or "").startswith("https://"):
                errors.append(f"{label}: source {sid} has no official https URL")
            if rec.get("status") == "supported_by_primary_source":
                if (src.get("provenance") or {}).get("evidence_strength") != "primary_official":
                    errors.append(f"{label}: supported claim source {sid} is not primary_official")
                if (src.get("access") or {}).get("method") in {None, "not_accessed"}:
                    errors.append(f"{label}: supported claim source {sid} was not accessed")
        subject = rec.get("subject_record_id")
        if subject != "registry:candidates" and subject not in company_ids:
            errors.append(f"{label}: unknown candidate subject: {subject!r}")
    for rec in source_records:
        label = f"sources.jsonl:{rec.get('source_id')}"
        missing_claims = set((rec.get("provenance") or {}).get("supports_claim_ids") or []) - claim_ids
        if missing_claims:
            errors.append(f"{label}: unknown supported claim references: {sorted(missing_claims)}")
    # Deterministic dedup/scope integrity: every candidate is classified by
    # at least one claim and one source; no two candidates share a normalized
    # seed name or an official source URL (proposals only, never promotion).
    for rec in company_records:
        label = f"candidates.jsonl:{rec.get('record_id')}"
        if not rec.get("provenance_claim_ids"):
            errors.append(f"{label}: candidate has no dedup/scope provenance claim")
        if not rec.get("sources"):
            errors.append(f"{label}: candidate has no official source")
    norm_names = [str((rec.get("candidate_names") or [""])[0]).strip().lower() for rec in company_records]
    if len(norm_names) != len(set(norm_names)):
        errors.append("duplicate normalized candidate names in candidates.jsonl")
    cand_urls = []
    for rec in company_records:
        for sid in rec.get("sources") or []:
            if sid in sources_by_id:
                cand_urls.append((sources_by_id[sid].get("url"), rec.get("record_id")))
    seen_url: dict = {}
    for url, cid in cand_urls:
        if url in seen_url and seen_url[url] != cid:
            errors.append(f"official source URL {url} shared by candidates {seen_url[url]} and {cid}")
        seen_url[url] = cid
    progress = index.get("discovery_progress") or {}
    if progress.get("official_source_records") != counts.get("source"):
        errors.append("index.json discovery_progress.official_source_records does not match sources.jsonl")
    if progress.get("provenance_claim_records") != counts.get("provenance_claim"):
        errors.append("index.json discovery_progress.provenance_claim_records does not match provenance-claims.jsonl")
    if progress.get("candidates_classified_for_human_review") != counts.get("company"):
        errors.append("index.json discovery_progress.candidates_classified_for_human_review does not match candidates.jsonl")

    # --- Wave 5 F6: manufacturer capability tuples (QIP R10) ---
    # Self-contained evidence (existing registry source_ids and/or newly
    # fetched official URLs recorded per tuple); never promotes an entity.
    from collections import Counter as _Counter
    cap_counts: dict = {}
    cap_dir = root / "capability-tuples"
    cap_path = cap_dir / "capability-tuples.jsonl"
    schema_path = cap_dir / "capability-tuple.schema.json"
    try:
        cap_schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if cap_schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" or not cap_schema.get("$id"):
            errors.append("capability-tuple.schema.json: not a JSON Schema 2020-12 document with $id")
        if cap_schema.get("$id") in ids:
            errors.append("capability-tuple.schema.json: $id duplicates an existing schema $id")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"capability-tuple.schema.json unreadable: {exc}")
    tuples, cap_errs = load_jsonl(cap_path)
    errors.extend(cap_errs)
    counts["capability_tuple"] = len(tuples)
    cap_counts = dict(sorted(_Counter(t.get("epistemic_status") for t in tuples).items()))
    companies_by_id = {r.get("record_id"): r for r in company_records}
    seen_tuples: set = set()
    covered: set = set()
    for t in tuples:
        label = f"capability-tuples.jsonl:{t.get('tuple_id')}"
        if not str(t.get("tuple_id", "")).startswith("cap-") or t.get("tuple_id") in seen_tuples:
            errors.append(f"{label}: tuple_id must be unique and start with 'cap-'")
        seen_tuples.add(t.get("tuple_id"))
        ent = t.get("entity") or {}
        cand = companies_by_id.get(ent.get("candidate_id"))
        if cand is None:
            errors.append(f"{label}: unknown candidate_id {ent.get('candidate_id')!r}")
            continue
        covered.add((ent.get("candidate_id"), t.get("capability")))
        if ent.get("seed_name") != (cand.get("candidate_names") or [None])[0]:
            errors.append(f"{label}: seed_name does not match candidate record (no promotion/renaming)")
        if ent.get("canonical_name") is not None or ent.get("entity_verification_status") != "candidate_unverified":
            errors.append(f"{label}: capability tuple must not promote entity (canonical_name=null, candidate_unverified)")
        qip = t.get("qip_r10") or {}
        if qip.get("mapping_claimed") is not False:
            errors.append(f"{label}: qip_r10.mapping_claimed must be false in this wave (QIP-R10.2)")
        ev = t.get("evidence") or {}
        if not str(ev.get("source_url") or "").startswith("https://"):
            errors.append(f"{label}: evidence.source_url must be an official https URL recorded with the tuple")
        for sid in ev.get("existing_registry_source_ids") or []:
            if sid not in source_ids:
                errors.append(f"{label}: unknown existing registry source {sid}")
        adapter = t.get("adapter") or {}
        status = t.get("epistemic_status")
        if status == "observed":
            if ev.get("evidence_strength") != "primary_official" or ev.get("access_method") in {None, "not_accessed", "metadata_only"}:
                errors.append(f"{label}: observed tuple requires primary_official evidence actually accessed")
            if not adapter.get("api_or_method") or not ev.get("locator"):
                errors.append(f"{label}: observed tuple requires adapter.api_or_method and evidence.locator")
        elif status == "inferred":
            if not adapter.get("api_or_method") or qip.get("mapping_status") != "inferred_not_claimed":
                errors.append(f"{label}: inferred tuple requires an observed manufacturer method and mapping_status=inferred_not_claimed")
        elif status in {"unknown", "not_found"}:
            if adapter.get("api_or_method") is not None:
                errors.append(f"{label}: {status} tuple must not name an api_or_method (fabrication guard)")
            if status == "not_found" and "not_found in recorded sources only" not in str(t.get("notes") or ""):
                errors.append(f"{label}: not_found must be scoped to recorded sources only")
            if status == "unknown" and not str(t.get("notes") or "").startswith("unknown:"):
                errors.append(f"{label}: unknown tuple must state the access reason in notes")
        else:
            errors.append(f"{label}: epistemic_status must be observed/inferred/unknown/not_found")
    for cid in companies_by_id:
        for cap in ("intervention_stop", "status_observation", "latch_reset"):
            if (cid, cap) not in covered:
                errors.append(f"capability-tuples.jsonl: candidate {cid} lacks an explicit {cap} tuple (unknown/not_found must be explicit, not omitted)")

    return {"ok": not errors, "errors": errors, "counts": counts,
            "capability_tuple_epistemic_counts": cap_counts,
            "verified_companies": 0 if index.get("verified_count") == 0 else index.get("verified_count")}


def main(argv: list[str]) -> int:
    report = validate(Path(argv[1]) if len(argv) > 1 else ROOT)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
