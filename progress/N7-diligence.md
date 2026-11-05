# Progress - N7-diligence (Wave 4, Tier 1, sole README owner)

Owner: N7 alone. Owns ONLY: README.md, docs/evidence/README.md,
docs/DILIGENCE.md, progress/N7-diligence.md, progress/n7-requests.md.
No evidence was relocated. Base: baa18a1522aeb9dc5865afbbfffe89fc94de2ece
(git fetch --prune first; origin/main verified at that hash;
gh pr list --state open: none).

## Attempts (max 3)

- Attempt 1: evidence/claim audit + stranger clean-clone gate (below).
  Docs written from that audit. No code touched.
- Attempt 2: unused unless CI/rebase after Tier 1 settles requires fixes.
- Attempt 3: unused.

## Deterministic check first (raw, this Mac, Python 3.11.15)

Clean clone n7-clean1 of baa18a1, with Rust:
  make setup (cargo build ok) ; make test ->
  80 passed, 1 warning in 23.62s
  cargo test --workspace --all-features --locked ->
  14 passed / 0, 3 passed / 0 (17 total)
Clean clone n7-clean3, without Rust (python3.11 shimmed on PATH,
cargo absent; exact setup message printed:
"secure core not built - STOP will run with unsigned attestation; see docs/SECURE-CORE.md"):
  make test -> 69 passed, 11 skipped, 1 warning in 20.17s
Failed variant (instructive, kept): restricting PATH to /usr/bin:/bin
silently fell back to Python 3.9.6 -> 1 failed (GNSS dataclass
TypeError), 68 passed, 11 skipped. This is why counts are never
universalised and Python 3.11 is part of every count claim.
cargo fmt --all --check: FMT_OK. clippy --workspace --all-targets
--all-features -D warnings: clean.
Registry validator re-run: ok, company 25, source 26, claim 38,
verified_companies 0.

## What changed

- README.md: removed test-evidence.svg embedding (graphic != raw
  evidence); removed stale "44 passed" + unlogged audit/deny/SBOM
  standing claims (downgraded to dated SECURE-CORE.md records);
  counts replaced with reconciled, scoped wording; added mandatory
  Wave 3 pilot caveat (same-agent deterministic templates = weak
  evidence until an independent model adversary); links to
  docs/DILIGENCE.md and docs/evidence/README.md.
- docs/evidence/README.md (new): index of every evidence location in
  the repo, each with Shows / Does-NOT-show. No relocation.
- docs/DILIGENCE.md (new): every README claim -> evidence -> exact
  clean-clone command; removed/downgraded list; roadmap (not claimed).
- progress/n7-requests.md (new): requests R1-R4 to Tier 1 siblings and
  N7's four-step merge gate.

## Merge status: NOT MERGED (by design)

wave4/n1-n6, n8 were all still at baa18a1 with no commits and no open
PRs at N7 start: Tier 1 / evidence nodes have not settled. Per the
Wave 4 order, N7 will fetch/rebase after they merge, re-run the
stranger clean-clone gate on the rebased tip, require CI green, and
only then merge. This branch is pushed as a PR for review in the
meantime; merging it now would violate that gate.
