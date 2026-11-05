# tools/repro - reproducibility runner

Stdlib-only. No network access is needed by the runner itself
(`make setup` it invokes may install the pinned `requirements.txt`).

From a clean clone, at the repo root:

  python3 tools/repro/repro.py                    # full: make setup, pytest,
                                                  # cargo test, SBOM, hashes
  python3 tools/repro/repro.py --mode python-only # Python suite only
  python3 tools/repro/repro.py --mode record-only # manifest + checklist only;
                                                  # runs nothing, claims nothing
  python3 tools/repro/repro.py --skip-setup       # reuse an existing .venv

Outputs (default `repro-out/`, intentionally not committed):

  environment-manifest.json  commit/branch/dirty state, platform, Python and
                             tool versions, SHA-256 of pinned input files,
                             per-step status/exit/duration. No secrets and no
                             environment-variable dump.
  logs/<step>.log            raw output of every executed step (skipped steps
                             log their skip reason; a skip is never a pass).
  sbom.cdx.json              from the repo's own scripts/sbom.sh (cargo only;
                             absent cargo -> recorded as NOT GENERATED).
  artifact-hashes.json       SHA-256 + size of the SBOM and any built
                             secure-core CLI (target/debug|release), plus any
                             --artifact GLOB the caller adds.
  claim-to-evidence.json/.md checklist parsed from docs/DILIGENCE.md and the
                             QIP v0.1 S.11 traceability table, plus this run
                             as a row. See docs/assurance/.

Exit code is 0 only when every executed step exited 0.

Tests for the runner itself:

  python3 -m pytest tools/repro/tests/ -q

Limits: timestamps/durations in the manifest are a record of one run, not a
byte-reproducible artifact. A pass covers only the commit/host/Python/mode
recorded. It is not certification, standards conformance, a legal
conclusion, or physical-safety validation.
