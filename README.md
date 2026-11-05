# Quberon Robot Interface (quberon-core)

![Tests](https://img.shields.io/badge/tests-21%20passed-16a34a)
![Python](https://img.shields.io/badge/python-3.11-3776ab)
![Mode](https://img.shields.io/badge/robot-SIMULATION-b91c1c)
![Meta runtime](https://img.shields.io/badge/meta%20runtime-mock%20(advisory)-ea580c)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20%2B%20e--ink-9333ea)

Authenticated mobile web prototype for a **simulated** robot STOP-request workflow on a Raspberry Pi with an e-ink display. It is **not** a safety-rated emergency stop and does **not** control physical robot hardware. Only `SimulatedRobotAdapter` is enabled.

![System architecture](docs/assets/architecture.svg)

![Final-pass test evidence](docs/assets/test-evidence.svg)

## Current status (2026-11-05)

| Capability | Status |
|---|---|
| Public code, app + simulator + scripts + tests | ✅ In this repo |
| Physical Pi + Waveshare 7.5" V2 e-ink (QR / LIVE badge) | ✅ Working (project records, TEST-RESULTS rows 22/29) |
| Authenticated STOP (viewer/operator/admin, CSRF, persistent latch, audit log, simulator ACK) | ✅ Implemented against the **simulator** |
| Physical humanoid control / certified e-stop | ❌ Not implemented, no such claim |
| Phone onboarding (private CA + local AP) | ⚠️ Works with certificate install; not zero-setup, not claimed as frictionless |
| Runtime Meta planning | ⚠️ Mock by default; live adapter exists in code, **live inference not verified** (see `docs/evidence/meta-live.md`) |
| Meta use in development | ✅ Development assistance via Hermes — separate from runtime claims (see `docs/BUILT-DURING-HACKATHON.md`) |
| Cellular (Tele2 EC25) | ✅ Project-recorded HTTP 200 data test (row 28); no failover/continuous claim |
| GNSS | ⚠️ Reader present, NO_FIX indoors, no RTK/accuracy claim |
| Voice / gesture interventions | 🧪 Experimental event path implemented: typed events + transcript matcher (STOP/STOPP) + synthetic fixtures through the ONE STOP service; **no microphone/camera recognition** (`docs/INTERVENTION-INPUTS.md`) |
| Isaac Sim | 📋 Design only, not run (`docs/ISAAC-SIM-INTEGRATION.md`) |

## 🌌 Pushing the Frontier — Building for Superintelligence

**The model proposes; deterministic law disposes.** quberon-core is a governance layer for increasingly capable AI: untrusted planners and multimodal signals (voice transcripts, gesture fixtures, future Isaac Sim bridges) may *propose*, but only authenticated, allow-listed, idempotent, audit-logged services may *act* — and a human can always intervene. Full thesis: [`docs/FRONTIER.md`](docs/FRONTIER.md).

## Run locally

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

Latest verified run: **21 passed** on Python 3.11.15 (Mac) — exact output in `docs/evidence/pytest-final.txt`, context in `docs/evidence/final-check.md`. A Mac test pass is not a Pi test pass.

## Deploy (from Mac, preserves Ethernet SSH at 10.77.0.2)

```sh
DRY_RUN=1 scripts/deploy_pi.sh
scripts/deploy_pi.sh
scripts/healthcheck.sh https://10.77.0.2:8443 /etc/quberon-robot-interface/ca.crt  # run on Pi, or copy the public CA cert to the Mac first
```

Demo passwords are never stored in this repo (external secrets file, mode 600).

## Known limitations (honest list)

- Single process / single active instance only (review item G, documented): the in-memory latch cache is not multi-instance safe.
- Planner concurrency is capped by its own limiter (review item D, fixed): a saturated planner returns `busy` and cannot starve STOP. This is best-effort isolation, not a real-time guarantee.
- Runtime DB failure now fails closed (503, latch held in memory, `persistence_ok=false`), but authentication also depends on the DB — this is not an always-available emergency-stop path.
- Software latency figures in project records are not physical stop times. The e-ink LIVE badge proves display refresh, not robot-connection freshness.

Historical notes live in `MORNING-HANDOFF.md`, `BLOCKERS.md`, `DECISIONS.md`, `TEST-RESULTS.md` — dated snapshots, superseded by the table above where they conflict.
