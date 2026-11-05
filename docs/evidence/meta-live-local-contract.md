# Live Meta inference — SYNTHETIC / LOCAL-CONTRACT evidence (offline)

Status: SYNTHETIC CONTRACT PASS — NOT A REAL META CALL

This file is offline, deterministic evidence from a local fake HTTP server.
It is NOT evidence of a real Meta/provider call, NOT live inference, and
must NOT be used to upgrade the README runtime-Meta claim.

- Evidence type: synthetic/local-contract (loopback fake HTTP server)
- Real provider calls made: 0
- Real credentials used: none (a fake test constant, already in
  tests/test_meta_live.py, is used; its value is never printed here)
- Authorization handling: the fake server receives the Authorization
  header in memory only; tests assert it never appears in captured
  stdout/stderr, returned proposals, errors, or any persisted file
- Code base at run time: a8d75288603b696b40404b82d7461c32468e8031 plus the
  uncommitted-at-run-time Lane C contract-test changes in this same lane
  (the commit containing this file is a later evidence/tests commit)
- UTC run date: 2026-11-05
- Test file: tests/test_meta_live.py (contract tests exercise the real
  LiveMetaProvider httpx network/JSON path against 127.0.0.1)

## Cases (each asserts the exact fake-server call count)

| Case | Fake-server calls | Result |
|---|---|---|
| One-call success (valid proposal; secret echoed in summary redacted; smuggled stop_latched/adapter_command fields stripped) | exactly 1 | PASS |
| Malformed JSON content | exactly 1 | PASS — MetaProviderError (JSONDecodeError type only), no fallback |
| HTTP 500 with secret-bearing body | exactly 1 | PASS — MetaProviderError (HTTPStatusError type only); secret absent from error/stdout/stderr |
| Schema-invalid proposal (MOVE_REAL_ROBOT / admin / no human confirmation / non-text summary) | exactly 1 | PASS — validator rejects (>=3 errors) |
| Timeout (server sleeps 11s; provider timeout 10s) | exactly 1 | PASS — MetaProviderError, no fallback |
| Unreachable endpoint (closed loopback port) | 0 reachable | PASS — MetaProviderError; get_provider() in live mode returns live/unavailable, never mock |
| Successful fake response through the app | exactly 1 | PASS — still cannot reset latch, grant capability, invoke adapter, or permit motion (simulated task HTTP 409, no audit events) |

Local run: .venv/bin/python -m pytest tests/test_meta_live.py -q
-> 16 passed (includes the 6 contract tests above; the timeout case
accounts for ~10s of the runtime).

## Distinction from real evidence

Real live evidence remains BLOCKED: see docs/evidence/meta-live.md
(Status: BLOCKED / FAILED, 0 provider calls, missing
META_API_URL/META_API_KEY/META_MODEL). That blocked status is unchanged
by this synthetic file. Live runtime Meta inference is NOT verified.
