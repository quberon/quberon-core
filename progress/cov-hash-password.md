NODE: cov-app-main-py-hash-password
TIER: 1
BRANCH: node/cov-app-main-py-hash-password
COMMITS: see final message / git log on this branch (single commit adding the two owned files; hash recorded in PR)
STATUS: complete

CHANGED:
- tests/test_cov_hash-password.py (new, only test file added)
- progress/cov-hash-password.md (this report; owned path per task header)

Note on path discrepancy: the task header lists owned progress path as
progress/cov-hash-password.md, while the report/handoff paragraphs name
progress/cov-app-main-py-hash-password.md. Writing outside the owned list
is stated to be a failed node, so this report is written only to the
owned path progress/cov-hash-password.md and the full report is also
given as the final message.

TASK:
No test named app/main.py:hash_password() - coverage added, omission not
justified. hash_password (app/main.py:69-72) was only exercised
indirectly via Store.create_user/login in tests/test_app.py.

COVERAGE ADDED (10 tests, all direct calls to hash_password):
- format: "pbkdf2_sha256$260000$<b64 salt>$<b64 dk>", strict/canonical
  base64 (validate=True + re-encode equality), 16-byte salt, 32-byte dk
- derived key equals an independently recomputed
  hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
  for ordinary, $-containing, empty, unicode (UTF-8), and 4096-char
  passwords; a wrong password does not reproduce the stored dk
- random salt: two hashes of the same password differ (string and salt)
  and both independently verify
- output neither equals nor contains the plaintext password
- round-trip through verify_password: correct password True, wrong and
  empty passwords False; a bit-flipped derived key does not verify

EVIDENCE (command, toolchain, host, UTC, raw output path):
- Host: Darwin Quberon1.local 24.3.0 arm64 (macOS 15.3.1)
- Python: 3.11.15 (/Users/quberon1/quberon-robot-interface/.venv/bin/python;
  this worktree has no .venv of its own, system python3 3.9.6 lacks
  fastapi - observed ModuleNotFoundError: No module named 'fastapi')
- cargo 1.99.1 / rustc 1.99.1 (Homebrew)
- UTC run: 2026-11-06T12:41:35Z (tests run 12:38-12:41Z)
- Node gate: python -m pytest tests/test_cov_hash-password.py -q
  Raw output: /tmp/raw-cov-hash/node-gate.txt
  Raw output verbatim:
    ..........                                                               [100%]
    10 passed in 0.68s
  Exit: 0
- Full suite with Rust (after cargo build --workspace, exit 0):
  python -m pytest -q
  Raw output: /tmp/raw-cov-hash/with-rust.txt
  Verbatim tail: "221 passed, 2 warnings in 44.86s"  Exit: 0
- Full suite with Rust removed from PATH (PATH=/venv/bin:/usr/bin:/bin,
  cargo confirmed absent; previously built target/debug binary remains
  on disk, which is what tests/test_app.py's needs_rust file-check keys
  on):
  Raw output: /tmp/raw-cov-hash/without-rust.txt
  Verbatim tail: "221 passed, 2 warnings in 45.11s"  Exit: 0
  Earlier on this branch before the Rust build, the same full suite
  reported "209 passed, 12 skipped" (rust-gated tests skipped), exit 0.
- Fail-direction (mutants in scratch copies under /tmp, repo untouched):
  1. pbkdf2 rounds 260_000 -> 1_000 in copied app/main.py:
     pytest tests/test_cov_hash-password.py -> exit 1,
     "6 failed, 4 passed" (/tmp/raw-cov-hash/fail-direction-rounds.txt)
  2. random salt -> fixed b"\x00"*16 in copied app/main.py:
     pytest tests/test_cov_hash-password.py -> exit 1,
     "1 failed, 9 passed" - only the random-salt test fails, as expected
     (/tmp/raw-cov-hash/fail-direction-salt.txt)
- `import app.main` creating zero files: covered by the existing
  tests/test_app.py::test_import_app_main_is_filesystem_inert, which
  passed in both full-suite runs above (no files of mine affect it).

TESTS (both modes):
- With Rust: 221 passed, 0 failed (full suite); node file 10 passed.
- Without Rust on PATH: 221 passed, 0 failed (full suite; see binary
  caveat above); node file 10 passed. New tests have no Rust dependency.

STILL NOT TRUE:
- hash_password has no explicit behaviour contract for non-str inputs
  (bytes/None raise AttributeError from .encode()); these tests do not
  pin that, because app/main.py:69 annotates `password: str` and no
  caller passes non-str - pinning it would invent a contract.
- The salt-uniqueness test is probabilistic in principle: two 16-byte
  random salts could theoretically collide; not observed, and the
  collision probability (2^-128 per pair) was not measured here.
- Timing side-channel resistance, password-strength policy, and any
  security certification of PBKDF2 parameters are NOT established by
  these tests or by anything in this repository. No certification,
  physical-safety, latency, or regulatory-compliance claim is made.
- The without-Rust full-suite run still had the cargo-built
  target/debug/quberon-secure-core-cli binary on disk; a truly clean
  clone without Rust was not reproduced in this worktree (ops/gate.sh
  runs that on a clean clone). The new test file itself imports only
  app.main and stdlib, so it passes identically either way (verified:
  10 passed before the Rust build existed).

NEEDS A HUMAN DECISION:
- Reconcile the progress-path discrepancy noted above
  (progress/cov-hash-password.md owned vs
  progress/cov-app-main-py-hash-password.md named in the report text)
  if the scheduler expects the latter filename.
