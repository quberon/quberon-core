NODE: cov-app-main-py-token-hash
TIER: 1
BRANCH: node/cov-app-main-py-token-hash
COMMITS: 8e148ff test: add coverage for app.main token_hash; plus the commit containing this progress file (its own hash is not knowable from inside the file)
STATUS: complete
CHANGED:
  - tests/test_cov_token-hash.py (new, owned): 16 tests naming token_hash directly
  - progress/cov-token-hash.md (this file, owned)
  - No file outside the owned paths was changed. app/main.py was mutated only
    transiently in the working tree for fail-direction checks and restored;
    git diff on app/main.py verified empty before commit.

WHAT WAS UNTESTED AND IS NOW COVERED:
  app/main.py:84-85 token_hash(token) = hashlib.sha256(token.encode()).hexdigest()
  It had no test naming it (search at base found only its definition and its
  three Store call sites). It is the sessions-table primary key: create_session
  stores token_hash(token), get_session/delete_session recompute it, so the
  raw session token must never be what is stored and the digest must be
  deterministic and unsalted.
  Tests added:
  - Hardcoded SHA-256/UTF-8 known answers (empty, "abc", "hello world",
    a password-shaped string, non-ASCII "stopp-å-✓" pinning UTF-8, an
    embedded-NUL token, and "a"*10000). Expected values are literals in the
    test, not recomputed with hashlib, so changing digest, encoding, salt,
    truncation or case fails.
  - Format: str, 64 chars, lowercase hex, parses as hex.
  - Deterministic/unsalted across repeated calls (session lookup depends on it).
  - Distinct digests for near-identical tokens (case, surrounding space,
    newline, NUL, one-char change, empty).
  - Digest differs from and does not contain a recognisable raw token.
  - Non-str inputs (None, bytes, int, list) raise AttributeError, the current
    str-only .encode() contract; the test comment says to update it deliberately
    if a TypeError guard is ever added, and never to accept bytes silently.
  - Store integration on a tmp SQLite DB: the sessions row equals
    token_hash(token) and not the token; get_session finds the exact token,
    rejects token+"x", "" and None; delete_session removes the row.

EVIDENCE (command, toolchain, host, UTC, raw output path):
  Host: Quberon1.local, Darwin 24.3.0 arm64; Python 3.11.15 (.venv from
  requirements.txt, pytest 8.3.4); cargo 1.99.1 / rustc 1.99.1 (Homebrew)
  for the with-Rust run. Times: 2026-11-06T12:39Z-12:41Z (UTC, `date -u`).
  Raw outputs (scratch, not committed):
    /tmp/cov-token-hash-evidence/targeted-with-rust.txt
    /tmp/cov-token-hash-evidence/full-with-rust.txt
    /tmp/cov-token-hash-evidence/targeted-without-rust.txt
    /tmp/cov-token-hash-evidence/full-without-rust.txt
    /tmp/cov-token-hash-evidence/fail-direction-plaintext.txt
    /tmp/cov-token-hash-evidence/fail-direction-utf16.txt
    /tmp/cov-token-hash-evidence/clean-clone-full-without-rust-binary.txt
  Raw summary lines observed:
    targeted (exit gate): "16 passed in 0.10s", exit 0
    clean clone targeted: "16 passed in 0.34s", exit 0

TESTS (both modes):
  With Rust (cargo build --workspace built target/debug/quberon-secure-core-cli):
    .venv/bin/python -m pytest tests/test_cov_token-hash.py -q  -> 16 passed
    .venv/bin/python -m pytest -q                               -> 227 passed, 2 warnings in 41.38s
  Without Rust (binary moved aside, PATH=/usr/bin:/bin:/usr/sbin:/sbin):
    .venv/bin/python -m pytest tests/test_cov_token-hash.py -q  -> 16 passed
    .venv/bin/python -m pytest -q                               -> 215 passed, 12 skipped, 2 warnings in 39.25s
    (skips are the pre-existing needs_rust tests; token_hash needs no core)
  Clean clone (fresh clone of this branch at 8e148ff, fresh .venv, no Rust binary):
    .venv/bin/python -m pytest tests/test_cov_token-hash.py -q  -> 16 passed
    .venv/bin/python -m pytest -q                               -> 215 passed, 12 skipped, 2 warnings in 39.63s
  Fail-direction (both exit 1, as required):
    token_hash mutated to `return token` (plaintext):
      14 failed, 2 passed -- /tmp/cov-token-hash-evidence/fail-direction-plaintext.txt
    token_hash mutated to sha256(token.encode("utf-16")):
      7 failed, 9 passed  -- /tmp/cov-token-hash-evidence/fail-direction-utf16.txt
    app/main.py then restored; git diff empty; targeted suite green again.
  Import inertness: HOME=<empty probe> PYTHONDONTWRITEBYTECODE=1
    python -c "import app.main" -> "import ok", 0 files created in probe HOME
    (also covered by the pre-existing test_import_app_main_is_filesystem_inert
    in the full suite above).

STILL NOT TRUE:
  - These tests do not prove SHA-256 collision or preimage resistance; they
    only pin token_hash to published/known digests for the sampled inputs.
    No finite test set can prove a hash function collision-free.
  - No claim that storing SHA-256 session digests is, by itself, a complete
    session-security design: token entropy comes from secrets.token_urlsafe
    at create_session (not exercised for entropy here), and expiry, cookie
    flags, CSRF and rate limiting are covered (or not) by other tests, not this file.
  - The non-str AttributeError is pinned current behaviour, not an endorsed
    API design; a future deliberate TypeError/ValueError guard would need a
    test update and human review.
  - Nothing here certifies any physical-safety, latency, or regulatory
    property; token_hash is an in-process string function plus one SQLite
    store/lookup/delete round-trip on a temporary database. No real
    deployment, database, or session traffic was tested.
  - The with-Rust full run used a locally built debug binary; no claim is
    made about the Rust core from these Python tests.

NEEDS A HUMAN DECISION: none for this node. (If maintainers prefer non-str
input to raise TypeError instead of AttributeError, that is a deliberate
app/main.py change outside this node's owned paths and should be its own node.)
