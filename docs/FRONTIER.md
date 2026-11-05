# Pushing the Frontier — Building for Superintelligence

**Hackathon theme mapping for quberon-core.**

Superintelligence will not arrive as a single model call. It will arrive as
powerful, fallible proposers connected to tools, robots and people. The
frontier problem is therefore not "can the model act?" — it is:

> **How do we let increasingly capable systems propose, while deterministic,
> auditable law decides — and a human can always intervene?**

quberon-core is a small, honest prototype of that governance layer, built on a
Raspberry Pi at the edge, where a physical display meets whoever is standing
in front of the robot.

## The architecture of control

```
UNTRUSTED PROPOSERS                DETERMINISTIC LAW                 EFFECT
─────────────────                  ─────────────────                 ──────
Meta planner (mock/live)    ──▶    Type-safe validator        ──▶    Proposals only.
Voice transcript (matcher)  ──▶    Auth + CSRF + capability   ──▶    One STOP service:
Gesture fixture (synthetic) ──▶    Idempotency + stale checks ──▶    latch · audit · ACK/UNKNOWN
Panic label                 ──▶    Audit-only, never a trigger
Future Isaac Sim bridge     ──▶    Wrong-robot/replay rejection ──▶  Simulated adapter today
```

Five frontier principles, implemented and tested (not slogans):

1. **The model proposes; the law disposes.** Planner output is untrusted data.
   It passes a type-safe, allow-listed validator (`integrations/meta.py`) and
   can never reset a latch, grant a capability, or command hardware — even
   when it asks to (tested with injection prompts).
2. **Every modality converges on one intervention path.** Button, voice
   transcript, synthetic gesture and future sensors all enter
   `execute_stop` — the single authenticated, idempotent, persistent,
   audit-logged stop service (`integrations/interventions.py`). No modality
   gets a weaker back door, and none can clear a latch.
3. **Labels are not authority.** A client claiming "the camera saw a palm" or
   "the user is panicking" proves nothing. Authority comes from the session;
   provenance is recorded as a label. `PANIC_CANDIDATE` is audit-only by
   design — a superintelligent system must know what it does *not* know.
4. **Failure fails closed, and says so.** Database failure → 503, latch held,
   observed state `UNKNOWN`, health reflects degradation. Adapter failure →
   `UNKNOWN`, never a green "stopped". A stale replay is history, never a
   claim about the present. A saturated planner returns `busy` instead of
   starving STOP. Uncertainty is a first-class output.
5. **The edge stays human-legible.** The e-ink display shows a QR code and a
   LIVE badge to the person physically present — no app install, no cloud
   round-trip — while the phone UI polls status every 2 s and degrades to
   `STALE / UNCONFIRMED` rather than guessing.

## Why this matters for superintelligence

- **Capability without custody is the failure mode.** As proposers get
  stronger (better planners, real speech/gesture recognizers, Isaac Sim
  world models, physical humanoids), the custody layer — allow-lists,
  idempotency, latch supremacy, audit, fail-closed semantics — is what must
  *not* get weaker. This repo is that layer, at prototype scale.
- **Simulation is the proving ground, honestly labelled.** Isaac Sim is the
  planned next adapter (contract in `docs/ISAAC-SIM-INTEGRATION.md`), behind
  the same acknowledgement semantics: no observed state, no "stopped" claim.
- **Development itself is part of the demo.** This system was built with a
  Meta AI agent (Hermes / Muse Wonder) writing and reviewing code against a
  deterministic test suite — 21 tests that every claim in this document must
  survive. The runtime planner remains mock until a live call is evidenced
  (`docs/evidence/meta-live.md`).

## The road forward

Experimental voice/gesture inputs → common intervention path → Isaac Sim
validation on a GPU host → supervised, manufacturer-specific humanoid
integration. Each step inherits the same law. That is how you push the
frontier without pushing past the human.

*SIMULATED ROBOT — NOT AN EMERGENCY STOP. No physical robot is controlled by
this software today, and no claim in this document says otherwise.*
