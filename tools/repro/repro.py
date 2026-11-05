#!/usr/bin/env python3
"""Reproducibility and assurance pack runner (stdlib only).

From a clean clone this script:
  1. records an environment manifest (no secrets, no full environment dump),
  2. optionally runs setup / Python tests / Rust tests / the repo SBOM script,
     capturing raw logs and exit codes,
  3. hashes build artifacts and the generated SBOM (SHA-256),
  4. emits a claim-to-evidence checklist parsed from docs/DILIGENCE.md and
     the QIP v0.1 traceability table (docs/specs/intervention-profile/
     QIP-v0.1.md), with unsupported / UNIMPLEMENTED / not-clone-verifiable
     claims listed explicitly.

A pass is evidence for exactly what ran, on exactly this host/commit.
It is NOT certification, NOT standards conformance, NOT a legal
conclusion, and NOT physical-safety validation (QIP-R11.2).

Usage:
  python3 tools/repro/repro.py [--out DIR] [--mode full|python-only|record-only]
                               [--skip-setup] [--timeout SECONDS]
                               [--artifact GLOB]...

Exit code: 0 only if every executed command exited 0; 1 if any executed
command failed; 2 on usage/setup errors. Skipped steps are recorded as
SKIPPED in the manifest, never as passes.
"""
import argparse
import glob
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "quberon-repro/1"
INPUT_FILES = [
    "requirements.txt", "Cargo.toml", "Cargo.lock", "Makefile",
    "scripts/sbom.sh", ".github/workflows/secure-core.yml",
    "docs/DILIGENCE.md", "docs/specs/intervention-profile/QIP-v0.1.md",
]
# Evidence-path tokens inside a DILIGENCE evidence cell.
PATH_RE = re.compile(
    r"(?<![\w./-])((?:docs|tests|app|research|spikes|scripts|conformance|"
    r"integrations|crates|adapters)/[\w./+@-]+|\.venv/bin/python)")
QIP_ROW_RE = re.compile(
    r"^\|\s*(QIP-R\d+\.\d+)\s*\|\s*([A-Z]+)\s*\|\s*([^|]+?)\s*\|\s*$")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_capture(argv, cwd, timeout=60):
    """Run argv; return (exit_code_or_None, combined_output, duration_s)."""
    start = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=str(cwd), timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, errors="replace")
        return p.returncode, p.stdout or "", round(time.monotonic() - start, 3)
    except (OSError, subprocess.TimeoutExpired) as exc:
        out = getattr(exc, "output", "") or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return None, "%sERROR: %s\n" % (out, exc), round(time.monotonic() - start, 3)


def tool_version(argv, cwd):
    if shutil.which(argv[0]) is None:
        return None
    rc, out, _ = run_capture(argv, cwd, timeout=30)
    line = out.strip().splitlines()[0] if out.strip() else ""
    return {"command": " ".join(argv), "exit_code": rc, "version": line or None}


def collect_environment(repo):
    def git(*args):
        rc, out, _ = run_capture(["git"] + list(args), repo, timeout=30)
        return out.strip() if rc == 0 else None

    inputs = {}
    for rel in INPUT_FILES:
        p = repo / rel
        if p.is_file():
            inputs[rel] = {"sha256": sha256_file(p), "size_bytes": p.stat().st_size}
        else:
            inputs[rel] = None  # missing input is recorded, not hidden

    status = git("status", "--porcelain")
    py = sys.executable
    venv_py = repo / ".venv" / "bin" / "python"
    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": ("Timestamps/durations make this manifest a record of one run, "
                 "not a byte-reproducible artifact. No environment variables "
                 "except PATH-presence of tools are recorded; no secrets."),
        "git": {
            "commit": git("rev-parse", "HEAD"),
            "branch": git("branch", "--show-current"),
            "dirty": bool(status),
            "dirty_entry_count": len(status.splitlines()) if status else 0,
        },
        "platform": {
            "system": platform.system(), "release": platform.release(),
            "machine": platform.machine(),
        },
        "python": {
            "executable": py, "version": platform.python_version(),
            "venv_python_present": venv_py.is_file(),
        },
        "tools": {
            "git": tool_version(["git", "--version"], repo),
            "make": tool_version(["make", "--version"], repo),
            "cargo": tool_version(["cargo", "--version"], repo),
            "rustc": tool_version(["rustc", "--version"], repo),
        },
        "input_files": inputs,
    }


def parse_diligence(text):
    """Rows of the DILIGENCE claim table: claim | evidence | command."""
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or line.count("|") < 4:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] in ("README claim",) or set(cells[0]) <= set("-: "):
            continue
        claim, evidence, command = cells
        paths = sorted(set(PATH_RE.findall(evidence)))
        rows.append({"claim": claim, "evidence_text": evidence,
                     "evidence_paths": paths, "command": command})
    return rows


def parse_qip(text):
    rows = []
    for line in text.splitlines():
        m = QIP_ROW_RE.match(line.strip())
        if m:
            rows.append({"requirement": m.group(1), "lowest_class": m.group(2),
                         "trace": m.group(3)})
    return rows


def build_checklist(repo, diligence_text, qip_text, run_results):
    """run_results: {step_name: record}. Statuses are explicit; nothing is
    rounded up: a traced QIP row is a trace, not a class/conformance claim."""
    runs_by_command_hint = run_results  # kept for provenance in the caller
    checklist = []
    for row in parse_diligence(diligence_text):
        missing = [p for p in row["evidence_paths"]
                   if not (repo / p.rstrip(".,;:)")).exists()
                   and not p.startswith(".venv/")]
        if row["command"].lower().startswith("none"):
            status, reason = "NOT_CLONE_VERIFIABLE", (
                "DILIGENCE records no clean-clone command (hardware/process/"
                "argument record). Unsupported from a clone by design.")
        elif missing:
            status, reason = "EVIDENCE_MISSING", "Missing paths: %s" % ", ".join(missing)
        else:
            status, reason = "EVIDENCE_PRESENT", (
                "Evidence path(s) exist at this commit. Whether the named "
                "command passed is in the run records, not inferred here.")
        checklist.append(dict(source="docs/DILIGENCE.md", kind="readme-claim",
                              status=status, reason=reason, **row))
    for row in parse_qip(qip_text):
        if "UNIMPLEMENTED" in row["trace"]:
            status, reason = "UNSUPPORTED_EXPLICIT", (
                "QIP traceability marks this UNIMPLEMENTED. Not claimed.")
        else:
            status, reason = "TRACE_PRESENT_NO_CLASS_CLAIM", (
                "Traced to N4 test id(s) %s. A trace is not a QIP class, "
                "conformance, or certification claim (QIP S.10/11, R11.2)."
                % row["trace"])
        checklist.append(dict(source="docs/specs/intervention-profile/QIP-v0.1.md",
                              kind="qip-requirement", status=status,
                              reason=reason, **row))
    # This run itself, as a claim row.
    failed = [n for n, r in run_results.items() if r["status"] == "FAIL"]
    passed = [n for n, r in run_results.items() if r["status"] == "PASS"]
    skipped = [n for n, r in run_results.items() if r["status"] == "SKIPPED"]
    checklist.append({
        "source": "tools/repro/repro.py (this run)", "kind": "repro-run",
        "claim": "Clean-clone build/test reproduction on this host",
        "evidence_paths": [], "command": "see environment-manifest.json run records",
        "status": "SUPPORTED_FOR_THIS_RUN" if passed and not failed else "UNSUPPORTED_EXPLICIT",
        "reason": ("Passed steps: %s. Skipped (not passes): %s. Failed: %s. "
                   "Valid only for the commit/host/mode in the manifest."
                   % (", ".join(passed) or "none", ", ".join(skipped) or "none",
                      ", ".join(failed) or "none")),
    })
    return checklist


def render_markdown(manifest, checklist, artifacts):
    out = []
    out.append("# Claim-to-evidence checklist (generated by tools/repro/repro.py)")
    out.append("")
    out.append("Schema: %s  Generated (UTC): %s  Commit: %s"
               % (manifest["schema"], manifest["generated_at_utc"],
                  (manifest["git"] or {}).get("commit")))
    out.append("")
    out.append("This checklist is evidence about what exists and what ran. It is")
    out.append("NOT certification, NOT standards conformance, NOT a legal")
    out.append("conclusion, and NOT physical-safety validation.")
    out.append("")
    out.append("## Runs")
    out.append("")
    for name, r in manifest["runs"].items():
        out.append("- %s: %s (exit=%s, %ss) log=%s"
                   % (name, r["status"], r["exit_code"], r["duration_s"], r["log"]))
    out.append("")
    out.append("## Artifacts (SHA-256)")
    out.append("")
    if artifacts:
        for a in artifacts:
            out.append("- %s  sha256=%s  size=%s" % (a["path"], a["sha256"], a["size_bytes"]))
    else:
        out.append("- none found (recorded explicitly; no artifact claim is made)")
    out.append("")
    out.append("## Checklist")
    out.append("")
    out.append("| Source | Item | Status | Command / trace | Reason |")
    out.append("|---|---|---|---|---|")
    for c in checklist:
        item = c.get("claim") or c.get("requirement", "")
        cmd = (c.get("command") or c.get("trace", "")).replace("|", "/")
        out.append("| %s | %s | %s | %s | %s |"
                   % (c["source"], item.replace("|", "/"), c["status"], cmd,
                      c["reason"].replace("|", "/").replace("\n", " ")))
    out.append("")
    out.append("## Unsupported / not-claimed (explicit)")
    out.append("")
    bad = [c for c in checklist
           if c["status"] in ("UNSUPPORTED_EXPLICIT", "NOT_CLONE_VERIFIABLE",
                              "EVIDENCE_MISSING")]
    if bad:
        for c in bad:
            out.append("- [%s] %s -- %s"
                       % (c["status"], c.get("claim") or c.get("requirement", ""),
                          c["reason"]))
    else:
        out.append("- none")
    out.append("")
    out.append("Additionally not claimed by this pack, regardless of checklist")
    out.append("rows: any QIP conformance class; certification or approval under")
    out.append("any machinery/robotics/functional-safety standard or law; live")
    out.append("Meta inference; physical robot control or a safety-rated e-stop;")
    out.append("Pi/Isaac-host test passes from a Mac/CI run; manufacturer-interface")
    out.append("mappings (QIP-R10 gap). EU legal topics, where present in")
    out.append("docs/assurance/, appear only as primary-source research questions.")
    out.append("")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reproducibility and assurance pack runner")
    ap.add_argument("--repo", default=".", help="repo root (default: cwd)")
    ap.add_argument("--out", default="repro-out", help="output dir, relative to repo")
    ap.add_argument("--mode", choices=["full", "python-only", "record-only"],
                    default="full")
    ap.add_argument("--skip-setup", action="store_true",
                    help="do not run `make setup` (use existing .venv/system python)")
    ap.add_argument("--timeout", type=int, default=1200, help="per-command timeout s")
    ap.add_argument("--artifact", action="append", default=[],
                    help="extra artifact glob (relative to repo); repeatable")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / "docs" / "DILIGENCE.md").is_file():
        print("error: %s does not look like the quberon repo root" % repo, file=sys.stderr)
        return 2
    out_dir = (repo / args.out).resolve()
    logs_dir = out_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    manifest = collect_environment(repo)
    runs = {}

    def step(name, argv_cmd, skip_reason=None):
        log_rel = "logs/%s.log" % name
        if skip_reason:
            (logs_dir / ("%s.log" % name)).write_text("SKIPPED: %s\n" % skip_reason)
            runs[name] = {"argv": argv_cmd, "status": "SKIPPED",
                          "exit_code": None, "duration_s": 0, "log": log_rel,
                          "reason": skip_reason}
            return
        rc, output, dur = run_capture(argv_cmd, repo, timeout=args.timeout)
        (logs_dir / ("%s.log" % name)).write_text(output)
        runs[name] = {"argv": argv_cmd, "status": "PASS" if rc == 0 else "FAIL",
                      "exit_code": rc, "duration_s": dur, "log": log_rel}

    cargo = shutil.which("cargo") is not None
    venv_py = repo / ".venv" / "bin" / "python"
    if args.mode == "record-only":
        for n in ("setup", "python_tests", "cargo_tests", "sbom"):
            step(n, [], skip_reason="record-only mode: not executed")
    else:
        if args.mode == "full" and not args.skip_setup:
            step("setup", ["make", "setup"])
        elif args.mode == "full":
            step("setup", ["make", "setup"], skip_reason="--skip-setup given")
        py = str(venv_py) if venv_py.is_file() else sys.executable
        step("python_tests", [py, "-m", "pytest", "-q"])
        if args.mode == "python-only":
            step("cargo_tests", [], skip_reason="python-only mode")
            step("sbom", [], skip_reason="python-only mode (no cargo SBOM run)")
        elif not cargo:
            step("cargo_tests", [], skip_reason="cargo not on PATH: NOT RUN, not a pass")
            step("sbom", [], skip_reason="cargo not on PATH: SBOM NOT GENERATED")
        else:
            step("cargo_tests", ["cargo", "test", "--workspace", "--all-features", "--locked"])
            step("sbom", ["sh", "scripts/sbom.sh", str(out_dir / "sbom.cdx.json")])

    manifest["runs"] = runs

    # Artifacts: generated SBOM + built secure-core CLIs + caller globs.
    candidates = [out_dir / "sbom.cdx.json",
                  repo / "target" / "debug" / "quberon-secure-core-cli",
                  repo / "target" / "release" / "quberon-secure-core-cli"]
    for pattern in args.artifact:
        candidates += [Path(p) for p in glob.glob(str(repo / pattern), recursive=True)]
    artifacts, seen = [], set()
    for p in candidates:
        p = Path(p)
        if p.is_file() and str(p) not in seen:
            seen.add(str(p))
            try:
                rel = str(p.relative_to(repo))
            except ValueError:
                rel = str(p)
            artifacts.append({"path": rel, "sha256": sha256_file(p),
                              "size_bytes": p.stat().st_size})
    artifacts.sort(key=lambda a: a["path"])
    manifest["artifacts"] = artifacts
    if runs.get("sbom", {}).get("status") == "PASS" and not any(
            a["path"].endswith("sbom.cdx.json") for a in artifacts):
        manifest["sbom_note"] = "SBOM step passed but no SBOM file found: recorded, not claimed."

    checklist = build_checklist(
        repo, (repo / "docs" / "DILIGENCE.md").read_text(errors="replace"),
        (repo / "docs/specs/intervention-profile/QIP-v0.1.md").read_text(errors="replace")
        if (repo / "docs/specs/intervention-profile/QIP-v0.1.md").is_file() else "",
        runs)

    (out_dir / "environment-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (out_dir / "artifact-hashes.json").write_text(
        json.dumps(artifacts, indent=2, sort_keys=True) + "\n")
    (out_dir / "claim-to-evidence.json").write_text(
        json.dumps(checklist, indent=2, sort_keys=True) + "\n")
    (out_dir / "claim-to-evidence.md").write_text(render_markdown(manifest, checklist, artifacts))

    failed = [n for n, r in runs.items() if r["status"] == "FAIL"]
    print("repro: commit=%s runs=%s artifacts=%d checklist=%d unsupported=%d out=%s"
          % ((manifest["git"] or {}).get("commit"),
             {n: r["status"] for n, r in runs.items()}, len(artifacts),
             len(checklist),
             sum(1 for c in checklist if c["status"] in
                 ("UNSUPPORTED_EXPLICIT", "NOT_CLONE_VERIFIABLE", "EVIDENCE_MISSING")),
             out_dir))
    if failed:
        print("repro: FAILED steps: %s (see logs/)" % ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
