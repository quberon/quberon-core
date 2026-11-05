#!/bin/sh
# Generate a minimal CycloneDX SBOM from `cargo metadata` (no extra tool
# required). Usage: scripts/sbom.sh [output.json]
set -eu
OUT="${1:-sbom.cdx.json}"
python3 - "$OUT" <<'PY'
import json, subprocess, sys
meta = json.loads(subprocess.check_output(["cargo", "metadata", "--format-version", "1"]))
components = []
for p in sorted(meta["packages"], key=lambda p: (p["name"], p["version"])):
    comp = {"type": "library", "name": p["name"], "version": p["version"],
            "purl": f"pkg:cargo/{p['name']}@{p['version']}"}
    if p.get("license"):
        comp["licenses"] = [{"license": {"name": p["license"]}}]
    if p.get("checksum"):
        comp["hashes"] = [{"alg": "SHA-256", "content": p["checksum"]}]
    components.append(comp)
sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"component": {"type": "application", "name": "quberon-secure-core"}},
        "components": components}
with open(sys.argv[1], "w") as f:
    json.dump(sbom, f, indent=2)
print(f"wrote {sys.argv[1]} with {len(components)} components")
PY
