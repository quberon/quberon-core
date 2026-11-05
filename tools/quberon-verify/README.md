# quberon-verify

Offline, stdlib-only verifier for quberon-evidence-bundle v1.
A third party needs only this directory's `quberon-verify` file and a
bundle — no network, no pip packages, no Rust toolchain.

  python3 tools/quberon-verify/quberon-verify <bundle.qeb>
  # JSON report on stdout; exit 0 = PASS_LIMITED_CLAIMS, 1 = REJECT, 2 = usage
  python3 -m pytest tools/quberon-verify/tests/test_verify.py -q
  # or: python3 -m unittest discover -s tools/quberon-verify/tests

Checks: ZIP/manifest integrity (SHA-256+size of every payload),
hash-chained audit, secure-core Ed25519 envelope + bundle attestation
signatures (pure-Python RFC 8032 verification), Copper replay
determinism (task outputs and unified logs byte-identical), STOP
recorded, environment-manifest completeness, and exact
supported/unsupported claims lists. A pass never claims a physical
stop, certification, signer authority beyond the bundled
self-asserted key, or hardware execution. Format: see
crates/quberon-evidence-bundle/SPEC.md.

tests/fixtures/simulated-stop.qeb — real simulated STOP bundle: actual
committed Copper record/replay evidence (Wave 3 N3) plus an envelope
signed and authorized by the real secure-core CLI at build time.
tests/fixtures/tampered-replay.qeb — same bundle with one flipped byte
in replay-task-outputs.bin; must REJECT with
HASH_MISMATCH:copper/replay-task-outputs.bin and
REPLAY_TASK_OUTPUTS_MISMATCH.
