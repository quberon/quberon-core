#!/usr/bin/env python3
"""Deterministically generate REPO-MAP.md from git ls-files --cached.

One line per tracked (staged/cached) path, sorted bytewise, with a
rule-based concise description. No model, no network, no timestamps.
Run: python3 scripts/generate_repo_map.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "REPO-MAP.md"

BY_SUFFIX = {
    ".py": "Python source",
    ".rs": "Rust source",
    ".md": "Markdown document",
    ".toml": "TOML configuration",
    ".json": "JSON data",
    ".jsonl": "JSON Lines data",
    ".yml": "YAML configuration",
    ".yaml": "YAML configuration",
    ".sh": "Shell script",
    ".png": "PNG image",
    ".jpg": "JPEG image",
    ".svg": "SVG image",
    ".txt": "Text file",
    ".crt": "Certificate file",
    ".lock": "Lock file",
}


def describe(path: str) -> str:
    name = Path(path).name
    if name == "Makefile":
        return "Make build/test entry points"
    if name == "Cargo.toml":
        return "Cargo manifest"
    if name == "Cargo.lock":
        return "Cargo lock file"
    suffix = Path(path).suffix
    return BY_SUFFIX.get(suffix, "Tracked file")


def main() -> int:
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached"], cwd=ROOT, text=True
    ).splitlines()
    # Always include the generator and its output so regeneration is
    # idempotent whether or not they are already staged.
    paths = sorted(set(p for p in paths if p) | {"REPO-MAP.md", "scripts/generate_repo_map.py"})
    lines = [
        "# REPO-MAP",
        "",
        "Generated deterministically by scripts/generate_repo_map.py",
        "from `git ls-files --cached`, sorted. Do not hand-edit.",
        "Regenerate: python3 scripts/generate_repo_map.py",
        "",
        f"Tracked paths: {len(paths)}",
        "",
    ]
    lines += [f"- `{p}` - {describe(p)}" for p in paths]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {len(paths)} tracked paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
