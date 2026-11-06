NODE: ind-1-adversary-split
TIER: 1
BRANCH: node/ind-1-adversary-split
COMMITS: 1e26741 (plus the report-hash commit on this branch); PR #47 https://github.com/quberon/quberon-core/pull/47 ; base origin/main 7fd9ea5
STATUS: complete for the exit gate below; independent real-model adversary still BLOCKED (see STILL NOT TRUE)

CHANGED (owned paths only: research/adversarial/**, progress/ind-1-adversary-split.md)
- research/adversarial/adversary.py (new): split adversary generator. Stdlib only, imports no defender code, consumes ONLY public_interface.json + the QIP document named by it. load_public_context() rejects source-code suffixes, implementation directories, non-allowlisted files, interfaces pointing at implementation material, and a fake QIP, before use. validate_artefact()/classify_artefact() are fail-direction stamp checkers.
- research/adversarial/public_interface.json (new): defender-published public interface only -- proposal fields/types/bounds, allowed action->capability mapping, public acceptance rules, target robot id, attack-class taxonomy, QIP reference. No implementation path, source, or validator symbol.
- research/adversarial/corpus/independent.jsonl (new): 52 artefacts (13 classes x 4), deterministic, deduped by payload SHA-256. EVERY artefact carries generator.model="none-programmatic-templates" and generator.sees_implementation=false, plus generator.lineage and per-input {role,name,sha256} for the two public inputs actually consumed. Expectations derive only from the stated public rules (every reject breaks at least one public rule).
- research/adversarial/provenance.json (new): inventory of prior corpora. Prior corpora keep their existing honest generator.model labels verbatim (class-*: "BLOCKED-no-real-model-template-corpus", mutations: "none-deterministic-mutation", hand-written: "hand-written"), are classified legacy-prior-corpus, counts and file SHA-256 recorded (15 files, 56,506 cases). They are NOT relabelled or restamped as independent.
- research/adversarial/ADVERSARY.md (new): split description, allowed inputs, stamp schema, honest-label rule, reproduce commands, non-claims.
- research/adversarial/generate.py: marked LEGACY/pre-split (superseded by adversary.py for new adversarial work); future GEN stamp now records model="none-programmatic-templates" and sees_implementation=false with an explicit shared-author-lineage caveat.
- research/adversarial/mutate.py: future mutation stamps likewise record model="none-programmatic-templates" and sees_implementation=false with the legacy-lineage caveat. Prior mutations.jsonl on disk is untouched.
- research/adversarial/tests/test_adversary_split.py (new, 8 tests): AST import ban on defender modules, runtime rejection of implementation inputs (fail direction), input-hash verification against the actual interface/QIP files, every independent artefact stamped, stamp checker proven to fail on sees_implementation=true / missing model / non-public input, determinism, prior corpora keep verbatim legacy labels and classify as legacy, legacy code paths stamp new artefacts.
- research/adversarial/evidence/ind-1-adversary-split.txt: raw pytest output.

EVIDENCE
- command: /Users/quberon1/quberon-robot-interface/.venv/bin/python -m pytest research/adversarial/tests -q
  toolchain: Python 3.11.15 (venv at /Users/quberon1/quberon-robot-interface/.venv), cargo 1.99.1 / rustc 1.99.1 present for the with-Rust run
  host: Darwin Quberon1.local 24.3.0 arm64 (macOS 15.3.1)
  UTC: 2026-11-06T10:58:24Z (run window 10:54-10:58Z)
  raw output path: research/adversarial/evidence/ind-1-adversary-split.txt
  raw output (verbatim): ".................... [100%] 20 passed in 0.18s" (exit 0)
- Independent corpus through the real harness: python research/adversarial/run.py --corpus research/adversarial/corpus/independent.jsonl --out /tmp/ind1-evidence/ind-results.jsonl --summary /tmp/ind1-evidence/ind-summary.json -> "cases=52 unique_payloads=52 paths=direct,endpoint", total_results=104, escapes=0, overblocked=0, benign false_reject_rate=0.0, s0=0, exit 0. (Scratch output in /tmp, not committed; the committed corpus is the artefact.)
- import check: in empty /tmp/ind1-importcheck, PYTHONPATH=<worktree> python -c "import app.main" printed import-ok and created zero files (ls total 0).

TESTS (both modes)
- With Rust (cargo 1.99.1 on PATH): research/adversarial/tests = 20 passed (exit 0, raw file above); full suite = 207 passed, 12 skipped (exit 0).
- Without Rust (env PATH=/usr/bin:/bin:/usr/sbin:/sbin): research/adversarial/tests = 20 passed (exit 0); full suite = 207 passed, 12 skipped (exit 0).
- System python3 (3.9.6, pytest but no fastapi) also passes research/adversarial/tests (20 passed); full-suite collection there fails on missing fastapi, which is an environment gap the universal gate's venv setup covers -- not used as evidence above.

STILL NOT TRUE
- No independent real-model adversary exists. The split adversary is programmatic templates (model=none-programmatic-templates); no separately provisioned model, agent, or external red team has generated any case. Restamping this label to a model id before that happens would be false.
- Prior corpora (56,506 cases) were authored in the same lineage as the validator. They are weak, same-author evidence; this node preserves their labels and does not retroactively make them independent.
- The public interface declaration was written from the defender's public surface in this node; an adversary operated by a genuinely separate party/agent has not yet run. The split enforced here is structural (code path, input allowlist, provenance stamp, fail-direction tests), not a completed organisational separation.
- adversary.py's runtime input restriction cannot prove a human operator never showed a generator implementation material outside this code path; it proves the generator program, as committed, reads only the two recorded public inputs (hashes on every artefact).
- No certification, physical-safety, latency, or regulatory-compliance claim is supported by this repository or by this node.

NEEDS A HUMAN DECISION
- Provision (or explicitly refuse) an application credential for a genuinely independent model/agent to generate a future corpus; until then all adversarial evidence stays programmatic-template grade.
- Decide whether the 52-case independent corpus should be scaled up (per-class counts) before being quoted alongside the legacy 56,506-case results.
