NODE: viz-2-truth-map
TIER: 1
BRANCH: node/viz-2-truth-map
COMMITS: see final message / git log on this branch (base 7fd9ea5)
STATUS: complete (node exit gate passes locally; universal gate not run here — see TESTS)

CHANGED:
- viz/truthmap/generate.py — stdlib-only generator. Parses QIP-v0.1.md section 11
  table (fails closed if missing) and requires the CLAIM-TO-EVIDENCE.md status
  vocabulary. Component status: trace_present / partial / gap.
- viz/truthmap/tests/test_truthmap.py + conftest.py — 12 tests pinning the
  observed section 11 counts, gap rendering, legend wording, XML validity,
  on-disk generated file matching the generator, and hand-drawn file retention.
- viz/truthmap/README.md — records the single regeneration command (see
  NEEDS A HUMAN DECISION for its location), what is/isn't generated, reading guide.
- viz/truthmap/evidence-truthmap.txt — raw local output.
- docs/assets/architecture-truth-map.svg — GENERATED truth map (do not hand-edit).
- docs/assets/architecture.svg — UNCHANGED (hand-drawn, kept; see below).

EVIDENCE:
- command: python3 -m viz.truthmap.generate && python3 -m pytest viz/truthmap/tests -q
- toolchain: Python 3.9.6, pytest 8.4.2 (system python on this host; generator is stdlib-only)
- host: Darwin Quberon1.local 24.3.0 arm64
- UTC: 2026-11-06T11:31:45Z
- raw output path: viz/truthmap/evidence-truthmap.txt
- observed counts derived from QIP section 11: 34 requirements, 16 traced,
  18 UNIMPLEMENTED; components: 2 trace_present (R4, R6), 6 partial
  (R1, R2, R5, R7, R8, R9), 3 gap (R3, R10, R11). Legend states plainly:
  "A gap means not built or not tested."

SUPERSEDE DECISION:
- docs/assets/architecture.svg is NOT superseded. The generated map covers
  QIP R1–R11 only; the hand-drawn diagram shows system layout (Phone UI,
  Raspberry Pi FastAPI, Rust Secure Core, SimulatedRobotAdapter, Meta
  Planner, e-ink, planned items) that QIP section 11 + CLAIM-TO-EVIDENCE.md
  cannot colour without inventing status. Both are kept, and
  viz/truthmap/README.md plus the generated SVG state which is generated.

TESTS (both modes):
- viz/truthmap tests with cargo on PATH: 12 passed in 0.01s (raw in evidence file)
- viz/truthmap tests with PATH=/usr/bin:/bin:/usr/sbin:/sbin (no cargo/rustc):
  12 passed in 0.01s. Generator/tests are pure stdlib, so Rust presence is
  irrelevant to them — stated, not universalised to the repo suite.
- Full repo suite / universal gate (with Rust, without Rust, fail-direction,
  import app.main zero-files): NOT RUN on this host — no .venv, system
  python3 lacks fastapi, collection of tests/test_app.py fails with
  ModuleNotFoundError. ops/gate.sh does not exist in this tree. This is
  recorded as not run, not as a pass; the scheduler gate must run it.

STILL NOT TRUE:
- No QIP class (OBSERVE/INTERVENE/AUTHORIZE/EVIDENCE) is claimed; a section 11
  trace is TRACE_PRESENT_NO_CLASS_CLAIM, not conformance or certification.
- R3 (stop priority), R10 (adapter/manufacturer mapping), R11 (verification/
  lifecycle) have zero traced requirements: not built or not tested per section 11.
- 18 of 34 QIP requirements are UNIMPLEMENTED, including R7.1/R7.4
  (QIP-DEG-03 skipped — a skip is NOT TESTED, not a pass), R5.1 restart
  persistence, R8.1/R8.3/R8.4 evidence completeness/replay/no-blockchain.
- The generator does not re-run N4 tests; it reports the committed section 11
  trace status. A stale trace in that table would be faithfully (and wrongly)
  rendered until the table is amended under its own rule.
- No certification, physical-safety, latency, real-robot, manufacturer-interface,
  live-Meta, Pi-host, or regulatory-compliance claim is supported by this map
  or by this repository.
- Hand-drawn architecture.svg components (Phone, Pi, e-ink, Meta live) have no
  evidence colour in the generated map; their presence in the hand-drawn file
  is not evidence.

NEEDS A HUMAN DECISION:
- README location: the brief said "viz/README.md" but owned paths are
  viz/truthmap/**, so the regeneration command is recorded in
  viz/truthmap/README.md. A human may move/copy it to viz/README.md outside
  this node's owned paths if that exact path is required.
- Whether to later colour the hand-drawn system components (Phone/Pi/e-ink/
  Meta) from DILIGENCE.md rows so architecture.svg can be superseded; this
  node did not, because the brief named only QIP section 11 and
  CLAIM-TO-EVIDENCE.md as sources.
