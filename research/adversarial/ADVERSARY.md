Adversary / defender split (ind-1)
==================================

Problem
-------
Before this node, the corpus generator and the validator under test were
authored in the same lineage. A template corpus can only find failures
its author already imagined, so those results are weak evidence about a
real adversary (this warning already stood in generate.py, run.py, and
the Wave 4 evidence).

Split
-----
Adversary side (may generate cases):
  adversary.py            the split generator. Stdlib only. Imports no
                          defender code and reads no defender files.
  public_interface.json   the ONLY machine-readable input besides QIP:
                          proposal fields/types/bounds, allowed
                          action->capability mapping, public acceptance
                          rules, target robot id, attack-class taxonomy.
  corpus/independent.jsonl  artefacts produced by adversary.py
                          (52 cases: 13 classes x 4, deterministic,
                          deduplicated by payload SHA-256).

Defender / harness side (executes cases, never feeds generation):
  run.py, invariants.py, and the code under test itself. adversary.py
  contains no reference to them; tests enforce this by AST import scan
  and by refusing implementation-shaped inputs at runtime.

Inputs the adversary is given -- and nothing else
-------------------------------------------------
1. public_interface.json (this directory)
2. docs/specs/intervention-profile/QIP-v0.1.md (named by the interface)

load_public_context() rejects, before use: any source-code suffix, any
path under an implementation directory, any non-allowlisted filename,
an interface that points at implementation material, and a QIP-named
file that is not the QIP document. Expectations in the independent
corpus are derived only from the public acceptance rules: every reject
case breaks at least one stated public rule, so no expectation depends
on a defender-side quirk.

Provenance stamp (every new artefact)
-------------------------------------
generator.model               = "none-programmatic-templates"
generator.provider            = "none-offline-templates"
generator.sees_implementation = false
generator.lineage             = "ind-1-adversary-split/programmatic-templates/public-interface+QIP-only"
generator.inputs[]            = {role, name, sha256} for each public
                                input actually consumed

adversary.validate_artefact() is the fail-direction checker: a stamp
with sees_implementation != false, a missing model, a missing input
hash, or a non-public input name is invalid. Unit tests prove it fails.

Honest model label / prior corpora
----------------------------------
No independent real model is provisioned, so the honest label stays
model=none-programmatic-templates -- for the new adversary exactly as
for prior corpora. Do not upgrade this label until a real, separately
provisioned model generates cases, then record its exact model id.

Prior corpora (corpus/class-*.jsonl, corpus/hand-written.jsonl,
corpus/mutations.jsonl; 56,506 cases) are NOT relabelled and NOT
restamped as independent. Their existing generator.model values are
preserved verbatim and inventoried in provenance.json as
legacy-prior-corpus. They remain weak, same-lineage evidence.

What this does not claim
------------------------
- That a real independent model adversary exists (it does not yet).
- That programmatic templates authored for this node are equivalent
  to an external red team; they are a structurally separated,
  input-restricted generator, which is a weaker claim.
- Any certification, physical-safety, latency, or regulatory claim.

Reproduce
---------
  python research/adversarial/adversary.py
  python -m pytest research/adversarial/tests -q
