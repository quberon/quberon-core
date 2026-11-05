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

    return {"ok": not errors, "errors": errors, "counts": counts,
            "verified_companies": 0 if index.get("verified_count") == 0 else index.get("verified_count")}


def main(argv: list[str]) -> int:
    report = validate(Path(argv[1]) if len(argv) > 1 else ROOT)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
