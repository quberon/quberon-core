NODE: ind-3-cross-verifier
TIER: 1
BRANCH: node/ind-3-cross-verifier
COMMITS: 6b20360 test(evidence-bundle): second independent cross-verifier (ind-3); plus this progress commit (hash is the commit containing this file; verify with git log --oneline -2)
STATUS: pass

CHANGED:
- evidence-bundle-conformance/independent_verify.py (new): second, independent stdlib-only verifier for quberon-evidence-bundle v1, written from crates/quberon-evidence-bundle/SPEC.md without reading the Rust crate source (src/lib.rs / src/main.rs were not opened). It does not import, load, or shell out to tools/quberon-verify or to bundle_check.py; Ed25519 verification uses extended twisted-Edwards coordinates, a different formulation from both existing Python checkers. CLI: exit 0 PASS_LIMITED_CLAIMS, 1 REJECT (including missing file), 2 usage, JSON report on stdout.
- evidence-bundle-conformance/test_cross_verifier.py (new, 42 tests): F2-pattern differential suite from outside the Tier 2 component. Exact parity with tools/quberon-verify on both committed fixtures (verdict, exit code, checks, errors, supported_claims, unsupported_claims); verdict parity on a 29-mutation deterministic corpus (stored-ZIP repacks of the good fixture) plus garbage/empty/duplicate bundles; exact error+check parity on the 20-mutation curated subset; independence tests (stdlib-only imports, no dynamic loading of the reference).
- evidence-bundle-conformance/SPEC-DEFECTS.md (new): SD-1..SD-9. Disagreements and SPEC gaps are recorded as spec defects, not coded around and not asserted as desirable behaviour.
- evidence-bundle-conformance/README.md: section documenting the second verifier, the differential suite, and SPEC-DEFECTS.md.
- No path outside evidence-bundle-conformance/** and this file was modified. The Rust source was not read; no handoff line was needed.

EVIDENCE:
- command: python3 -m pytest evidence-bundle-conformance -q
  raw output path: /tmp/ind3-evidence/ (final-with-rust.log, final-without-rust.log); exit-gate output reproduced in TESTS below. Logs are session-local under /tmp and are NOT committed; rerunning the commands reproduces them.
- toolchain: system Python 3.9.6 (exit gate), venv Python 3.11.15 (make test), cargo 1.99.1 (5f94df478 2026-08-27), rustc 1.99.1 (58cf8f9c3 2026-10-13)
- host: Darwin arm64, macOS 15.3.1, Quberon1.local
- UTC: 2026-11-06T11:07:03Z (final full-suite runs)

TESTS:
- Exit gate, system Python 3.9.6: python3 -m pytest evidence-bundle-conformance -q -> 59 passed, 1 warning (expected zipfile Duplicate-name UserWarning from the duplicate-entry test), exit 0. Raw: 59 passed in 24.90s.
- Both modes, full suite (venv Python 3.11.15, make test with Rust on PATH): 241 passed, 12 skipped, 4 warnings, exit 0 (/tmp/ind3-evidence/final-with-rust.log).
- Both modes, full suite with Rust removed from PATH (PATH=.venv/bin:/usr/bin:/bin:/usr/sbin:/sbin, no cargo/rustc reachable): 241 passed, 12 skipped, 4 warnings, exit 0 (/tmp/ind3-evidence/final-without-rust.log).
- Fail-direction: independent_verify.py on tampered-replay.qeb -> exit 1 (REJECT); on a missing path -> exit 1 with errors [BUNDLE_EMPTY_OR_NOT_ZIP] and no traceback; mutation corpus asserts REJECT (never PASS) for all 29 mutations in both implementations.
- import side-effect check: PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -c "import app.main" in the worktree -> import-ok, git status before/after identical (ZERO_NEW_FILES).

STILL NOT TRUE:
- This verifier, like both existing ones, proves only internal consistency of a bundle for the key bundled inside it. It does NOT prove signer authority: a rebuilt, re-signed bundle with an attacker's own key passes bundled-key verification (SPEC-DEFECTS SD-9, SPEC.md unsupported list). No external trust anchor (pinned key/kid) is implemented in independent_verify.py; bundle_check.py's --pinned-key-hex remains the only such anchor in this directory.
- Exact error-code/check-name/supported-claims parity is parity with an existing implementation's observable output, not with SPEC.md text: SPEC.md does not define those strings (SD-1, SD-2). A future SPEC revision could legitimately change them and break exact parity without any verifier being wrong.
- The reference verifier still crashes on the SD-8 malformed-type inputs (audit object, manifest files as string, integer git_commit) as observed 2026-11-06; this node cannot fix that (tools/ is outside owned paths) and the differential suite deliberately does not enshrine the crash as expected behaviour.
- Attestation kid/domain fields remain unchecked by both verifiers (SD-5); manifest bindings sequence/decision_code/copper-log hashes are only indirectly protected via the attestation (SD-7); the audit-tip binding wording in SPEC.md does not match observable single-record-coincident behaviour for multi-record audits (SD-6) and no multi-record fixture exists to test it.
- No certification, physical-safety, physical STOP, latency, hardware/Pi execution, HSM/TPM custody, or regulatory-compliance claim is supported by anything in this node or this repository. A PASS is PASS_LIMITED_CLAIMS for a simulation bundle only.

NEEDS A HUMAN DECISION:
- Whether to revise crates/quberon-evidence-bundle/SPEC.md (outside owned paths) to close SD-1..SD-7: enumerate the supported-claims list, error/check strings, decision/attestation schemas, comparison.txt tokens, required manifest bindings, and attestation field checks, so a third implementer can be written from the spec alone.
- Whether to fix tools/quberon-verify (outside owned paths) to REJECT instead of crash on the SD-8 malformed-type inputs, and if so with which error codes.
