NODE: viz-1-evidence-renderers
TIER: 1
BRANCH: node/viz-1-evidence-renderers
COMMITS: see PR (single commit on 7fd9ea5 base; hash recorded in final report / PR)
STATUS: complete (pending scheduler merge; author did not merge)

CHANGED (owned paths only):
- viz/evidence/render.py - deterministic stdlib renderer + CLI
  (python3 viz/evidence/render.py --repo-root . --out viz/evidence)
- viz/evidence/__init__.py
- viz/evidence/fleet-timeline.svg - (a) fleet-sim scenario trace timeline,
  trace_sha256 bc00d02757b140236eff8687b4934a3cb373aee72759281b1f87087d13e79eb0
  (computed fresh from scripted_scenario(), matches fleet-sim/run.py output),
  observed_verdict CONFLICTED. Band SIMULATED.
- viz/evidence/loadtest-percentiles.svg - (b) median/p95/p99 per scenario for
  all 3 attempts (colour per attempt, median->p99 line per attempt, attempt-1
  numeric triples printed and test-checked against attempt1.json). Band
  MEASURED-ON-HOST, with the source claim_scope caveat in the figure/README.
- viz/evidence/adversarial-summary.svg, adversarial-postmerge.svg,
  adversarial-hand.svg - (c) one figure per
  research/adversarial/results/*summary*.json (all 3 files): per-class
  violations bar, cases/rejected/accepted_in_error/worst, escape counts
  counted from escapes[] by class (summary.json: 300 escapes =
  malformed-nonobject-json 200 + oversize-resource 100). Band SYNTHETIC.
- viz/evidence/qip-traceability.svg - (d) QIP-v0.1.md section-11 grid:
  34 requirements, 18 UNIMPLEMENTED each marked in-row
  "GAP - UNIMPLEMENTED (NOT TESTED)". Band NOT TESTED.
- viz/README.md - figures, provenance, determinism proof, limits
- viz/tests/test_render.py - 12 tests
- progress/viz-1-evidence-renderers.md - this file

Every SVG embeds (metadata + visible header): source path(s), source
sha256 of bytes actually read, git commit, UTC (committer date of that
commit in UTC, not wall clock - that is what makes twice-rendering
byte-identical), and an evidence band.

EVIDENCE:
- command: python3 viz/evidence/render.py --repo-root . --out viz/evidence
  toolchain: Python 3.9.6 (system) for render+viz tests; Python 3.11.15
  (borrowed sibling-worktree .venv, this worktree has no .venv) for full suite
  host: Darwin Quberon1.local 24.3.0 arm64 (macOS 15.3.1)
  UTC: 2026-11-06T11:33:59Z (report time; figures embed commit UTC
  2026-11-06T09:42:56Z from HEAD 7fd9ea5)
  raw output: renderer stdout (hashes below) reproduced in PR body;
  determinism raw check: rendered to /tmp/viz-a and /tmp/viz-b,
  (cd /tmp/viz-a && shasum -a 256 *.svg > /tmp/viz.sha) then
  (cd /tmp/viz-b && shasum -a 256 -c /tmp/viz.sha) -> all 6 OK,
  CLI stdout of both runs diff-identical; committed SVGs match a fresh
  render at the same commit (diff of renderer stdout: identical).
  SVG sha256 (committed):
    af675f1b3415be900b986f27e5315bb82f788fdb4a7fcf028e3081da8a6228fb  adversarial-hand.svg
    262fbabf6b5d1dc5259911da106ee52c14fcca2aa0a69ac1cf283eafda4d4ee4  adversarial-postmerge.svg
    7e7ef1af0235b83bf1064eae0f1e9a1f3c2cf5dc23cb87ac2328abc879493b6c  adversarial-summary.svg
    16b58682bf0c6201441fb64a3438f72a258bf9819b3f26852a8d54ee1ff7ea68  fleet-timeline.svg
    ee7eda43680efa3cea2fe0ce1dc5d68b546f5bfc9d46d83a62b9313c626e2adc  loadtest-percentiles.svg
    cdc5894893c4af6e15b7d63ee7479a1d3c4c1e3f7aa055f9b3696ac1c8ca752c  qip-traceability.svg
  All 6 SVGs also parsed as well-formed XML (ElementTree) after rendering.

TESTS:
- exit gate: python3 -m pytest viz/tests -q -> 12 passed in 0.06s (raw above in session)
- with Rust toolchain present (cargo 1.99.1 on PATH, core CLI not built in
  this worktree): borrowed-venv python -m pytest -q -> 211 passed, 12 skipped
- without Rust: not honestly reproduced locally - the "no-cargo PATH"
  attempt still had cargo discoverable via the parent PATH and no core
  CLI is built in this worktree, so Rust-dependent tests skip either way
  (211 passed, 12 skipped). The universal gate (ops/gate.sh, run by ops)
  is the authority for both modes and the fail-direction tests; claim
  here is only what was observed locally.
- import app.main creating zero files: verified - git status --porcelain
  identical before/after import (only pre-existing ?? viz/ ).

STILL NOT TRUE:
- No figure is evidence of anything beyond its cited source: fleet is a
  simulation, loadtest is simulated-adapter HTTP on one Mac, adversarial
  is a same-author synthetic template corpus, QIP traced rows are traces
  not passes. No certification, physical-safety, latency, real-time or
  regulatory-compliance claim is supported.
- Committed SVGs embed the commit they were rendered at (7fd9ea5); after
  this node commits, HEAD differs, so a re-render changes only the
  git_commit/UTC header. Byte-identity is claimed at fixed commit+evidence,
  which is what the tests pin (explicit commit/utc, plus default-git
  twice-render identity).
- Adversarial hand-summary.json (12 results) and postmerge-summary.json
  (0 escapes, post-hardening schema) are not comparable runs to
  summary.json; the figures show each file separately and do not merge them.
- QIP: 18 of 34 requirements remain UNIMPLEMENTED gaps; nothing in the
  grid closes them.

NEEDS A HUMAN DECISION:
- None for this node. Future evidence updates only require re-running
  the renderer; whether to automate that in CI is an ops decision
  outside the owned paths.
