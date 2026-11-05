# F8 — Meta evidence runner repair (Wave 5, Tier 2, offline only)

Base: 35ee2aef6f7a2fcf17e51de40678aee97ba0b350 (origin/main at start)
Branch: wave5/f8
Owned files only: scripts/meta_live_evidence.py,
scripts/run_meta_live_evidence.sh (new), tests/test_meta_live.py,
docs/evidence/meta-live.md, progress/F8-meta-runner.md
No real provider call was made, no credentials were used, no secret
was printed. All network in tests is loopback (127.0.0.1) fake servers
with fake test constants only.

## Bugs fixed

1. Environment precedence / Authorization header mismatch
   - Before: meta_live_evidence.run(environ=...) checked and redacted
     the supplied mapping, but LiveMetaProvider() read os.environ, so
     a stale process environment silently selected a different
     endpoint/model and put a different key in the Authorization
     header than the evidence described.
   - Fix: _provider_environ() applies the supplied mapping to
     os.environ for provider construction and the single propose()
     call, then restores the process environment (even on failure).
   - Regression test (loopback, two fake servers): stale process env
     points at server A/key A; supplied environ points at server
     B/key B. Result: B receives exactly 1 call with
     "Authorization: Bearer <key B>" and model exact-test-model-1,
     A receives 0, neither key appears in evidence/stdout/stderr,
     and os.environ is restored afterwards.

2. Missing httpx handling
   - Before: LiveMetaProvider imports httpx inside propose(), before
     its own error wrapping, so a missing httpx surfaced as a bare
     ImportError and the runner had already counted a call; tests
     importing httpx failed hard instead of skipping.
   - Fix (runner only; integrations/meta.py is outside F8 ownership):
     preflight via importlib.util.find_spec("httpx") after the
     missing-env check and before any factory/provider call. Missing
     httpx now writes an honest BLOCKED record ("missing Python
     dependency 'httpx' ... No provider call was made and no
     Authorization header was sent."), calls=0, exit 1.
     run(..., httpx_available=False) injects the condition offline.
   - Tests: httpx-dependent tests use pytest.importorskip, so absence
     is a skip, never a fabricated pass.
   - Verified with the system interpreter (no httpx): wrapper run
     with a fake loopback URL/fake key blocked pre-call, calls=0.

3. Shell wrapper (new: scripts/run_meta_live_evidence.sh)
   - Interpreter precedence: $PYTHON > .venv/bin/python >
     python3.11 > python3. Configuration precedence: caller's
     exported environment only; sets no META_* defaults, sources no
     .env, prints no environment/headers. exec preserves the Python
     runner's exit code. `sh -n` passes.
   - Test: wrapper with no META_* exits 1 and writes BLOCKED, 0 calls.

## Failed attempts preserved (honest status)

- Prior evidence (2026-11-05T12:22:02Z, tested commit 96a5af2):
  BLOCKED / FAILED, 0 calls, missing META_API_URL/META_API_KEY/
  META_MODEL. Superseded in place by the regenerated file below;
  recorded here so the attempt is not erased.
- This run: docs/evidence/meta-live.md regenerated offline via
  `sh scripts/run_meta_live_evidence.sh` with no META_* set:
  BLOCKED / FAILED, 0 provider calls, exit 1, tested commit
  35ee2aef6f7a2fcf17e51de40678aee97ba0b350.
- Live runtime Meta inference remains NOT verified. No claim upgrade.

## Verification (raw counts)

- .venv/bin/python -m pytest tests/test_meta_live.py -q
  -> 19 passed (was 16; +3 F8 tests), 1 warning
- make test -> 134 passed, 13 skipped, 2 warnings
- sh -n scripts/run_meta_live_evidence.sh -> ok
- Missing-httpx wrapper probe (system python3, no httpx, fake values)
  -> BLOCKED, calls=0, exit 1
