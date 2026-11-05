# Built during the hackathon — final pass (2026-11-05)

Starting point: public commit `c92f70777ca5bf0121d360a66a8c04adc4d511b8` on `feature/overnight-prototype` (the pre-existing Pi/e-ink + simulated STOP system; not rebuilt in this pass).

## New in this final pass (one commit on top of the starting point)

- **Fix A** (`app/main.py`): stale STOP idempotency replay no longer claims the simulator is currently stopped; response carries `historical_duplicate`, `current_stop_latched`, `current_observed_state`.
- **Fix B, tested subset** (`app/main.py`): global SQLite error handler fails closed (503, latch held in memory, `UNKNOWN`, `persistence_ok=false`); `/healthz` `ok` reflects persistence; simulation reset inhibited while degraded.
- **Fix C** (`integrations/meta.py`, `app/main.py`): type-safe plan validation with action↔capability mapping and bounded strings/lists; validation failures are structured results, never HTTP 500 tracebacks.
- **Fix E** (`integrations/meta.py`, `app/main.py`): missing live Meta config yields an explicit `UnavailableMetaProvider` instead of preventing app startup or silently posing as mock.
- **Fix F** (`app/main.py`): duplicate simulated-task keys converge to the previous result without re-invoking the adapter; conflicting reuse → 409.
- **Tests:** 12 → 17 passing (5 new tests: A, B, C, E, F). Exact output in `docs/evidence/pytest-final.txt`.
- **Docs:** this file, `docs/evidence/final-check.md`, `docs/evidence/meta-live.md`, `docs/INTERVENTION-INPUTS.md`, `docs/ISAAC-SIM-INTEGRATION.md`, and a reconciled README status table.

## Not built in this pass

Voice recognition, gesture recognition, Isaac Sim bridge, live Meta inference — all roadmap only, labelled as such.

## Human / tool contributions

- System design, hardware (Pi, e-ink, cellular, GNSS), deployment and all pre-`c92f707` code: Rasmus (project author), per project records.
- This final pass: implemented with AI development assistance (Muse Wonder 1.0 via Hermes, as reported by the user) — a **development-time** contribution. No AI system is claimed at runtime except the labelled mock planner / unverified live adapter.
- No chronology beyond this session is asserted; commit history is the record for earlier work.

## Frontier pass (theme: Pushing the Frontier — build for superintelligence)

- `integrations/interventions.py`: typed multimodal intervention events (BUTTON/VOICE_STOP/GESTURE_STOP/PANIC_CANDIDATE), source-status labels, staleness policy, deterministic transcript matcher (standalone STOP/STOPP; `nonstop` and negations rejected).
- `POST /interventions` requires operator capability + CSRF; stop kinds reuse the single `execute_stop` core (refactored from `/stop`, same behavior + tests); PANIC_CANDIDATE is audit-only.
- Fix D: dedicated planner concurrency limiter (2), `busy` response on saturation.
- UI: 2 s polling with STALE/UNCONFIRMED degradation, audit-event rendering, labelled synthetic intervention controls.
- `docs/FRONTIER.md`: the governance thesis — model proposes, deterministic law disposes.
- Tests: 17 → 21 passing.
