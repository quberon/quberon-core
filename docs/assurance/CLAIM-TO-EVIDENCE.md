# Claim-to-evidence method (generated checklists)

Per-run checklists are emitted by `tools/repro/repro.py` as
`repro-out/claim-to-evidence.{json,md}`. They are generated from two
committed sources, never hand-edited, so a stale hand count cannot
drift ahead of evidence:

1. `docs/DILIGENCE.md` - every README claim row (claim, evidence,
   clean-clone command).
2. `docs/specs/intervention-profile/QIP-v0.1.md` S.11 - every
   QIP-R<n>.<m> requirement and its trace or UNIMPLEMENTED marker.
3. The run itself - one row summarising which steps passed, skipped,
   or failed on that commit/host/mode.

## Status vocabulary (exact meanings)

| Status | Meaning |
|---|---|
| EVIDENCE_PRESENT | Evidence path(s) named in DILIGENCE exist at this commit. Pass/fail of the named command is read from the run records, not inferred from existence. |
| EVIDENCE_MISSING | A named evidence path does not exist. Listed under unsupported. |
| NOT_CLONE_VERIFIABLE | DILIGENCE records `none` as the clone command (hardware, phone, cellular, process, or thesis records). Unsupported from a clean clone by design; the underlying record may exist elsewhere, but this pack does not re-claim it. |
| TRACE_PRESENT_NO_CLASS_CLAIM | QIP row traces to an N4 test ID. A trace is not a QIP class, conformance, certification, or safety claim (QIP S.10/11, R11.2). |
| UNSUPPORTED_EXPLICIT | QIP row is UNIMPLEMENTED, or the repro run itself passed nothing. Listed verbatim under "Unsupported / not-claimed". |
| SUPPORTED_FOR_THIS_RUN | Repro-run row only: executed steps passed and none failed, for the recorded commit/host/Python/mode only. Skips are named in the same row. |

## Standing unsupported categories (always explicit in generated output)

- Every QIP requirement whose S.11 trace is UNIMPLEMENTED (at base
  35ee2ae these include, among others, R2.3, R3.1-R3.3, R5.1, R7.1,
  R7.4, R8.1, R8.3, R8.4, R9.1, R9.3, R10.1, R10.2, R11.1-R11.3; the
  generated checklist is authoritative, not this summary).
- DILIGENCE rows whose command is `none`: physical Pi/e-ink, phone
  onboarding, cellular, Meta-in-development, frontier thesis.
- Any step the runner skipped or could not execute (no cargo, no
  SBOM, record-only mode): a skip is recorded as SKIPPED with its
  reason and is never counted as a pass.
- Claims never made by this pack regardless of rows: any QIP class;
  certification/approval; live Meta inference (`docs/evidence/
  meta-live.md` records BLOCKED, 0 calls at base); physical robot
  control or a safety-rated e-stop; manufacturer-interface mappings
  (QIP-R10 gap); Pi/Isaac-host results inferred from another host.

If a future run changes any of this, it changes because the committed
sources or the raw run logs changed - the generator will show it.
