# Quberon Robot Interface Implementation Plan

> **For Hermes:** Implement task-by-task with tests at each milestone. Do not enable physical robot control.

**Goal:** Deploy an authenticated, persistent simulated STOP-request prototype on the Raspberry Pi with QR onboarding assets, safe network isolation, bounded Meta planning, and evidence-based handoff.

**Architecture:** Python 3/FastAPI/SQLite on the Pi; deterministic local state machine and simulated adapter only. HTTPS by default with a local CA created outside the repo. Mock display because the physical panel is not identified and SPI is disabled.

**Tech Stack:** FastAPI, Uvicorn, SQLite, qrcode/Pillow, pytest/httpx, systemd, NetworkManager.

---

### Task 1: Inventory and safety foundations
- Create `INVENTORY.md`, `DECISIONS.md`, `BLOCKERS.md`, `ROLLBACK.md`.
- Record measured Pi, network, modem, camera, SPI/GPIO facts separately from assumptions.
- Verification: SSH remains reachable at `10.77.0.2`; `vcgencmd get_throttled` returns `0x0`.

### Task 2: Core state, auth and STOP API
- Create `app/main.py`, `adapters/robot_sim.py`, `integrations/meta.py`.
- Implement PBKDF2 password hashing, server-side sessions, CSRF, role checks, login throttling, SQLite audit/idempotency, latched simulated STOP, simulated task and admin-only simulation reset.
- Test first with `tests/test_app.py` covering auth, CSRF, roles, idempotency, persistence and Meta injection boundaries.

### Task 3: Mobile UI and QR assets
- Implement server-rendered UI in `app/main.py` and assets under `static/`.
- Create `scripts/generate_qr.py`; generate Wi-Fi and control URL QR PNGs with quiet zones.
- Verify QR decoding in tests with OpenCV if available or decoder-independent payload assertions plus image geometry checks.

### Task 4: Pi deployment
- Create `scripts/deploy_pi.sh`, `systemd/quberon-robot-interface.service`.
- Stage to `/opt/quberon-robot-interface`, state in `/var/lib/quberon-robot-interface`, secrets outside repo with mode 0600.
- Verify `/healthz`, login, STOP and restart persistence over Ethernet using the local CA.

### Task 5: Display and camera
- Keep `adapters/display.py` mock backend; render a full e-ink layout PNG.
- Use camera capture only as evidence; do not drive unknown panel hardware while panel label/wiring and SPI are unverified.

### Task 6: Wi-Fi AP with rollback
- Back up NetworkManager state; arm a systemd timed rollback that reactivates the prior Wi-Fi client profile.
- Create isolated `Quberon-Demo` WPA2 AP on `10.99.0.1/24`, no intentional internet forwarding, app-only firewall where verifiable.
- Verify Ethernet SSH twice after activation; cancel rollback only after checks. Mark real phone join pending if no phone participates.

### Task 7: Sixfab and Here+ diagnostics
- Read-only USB/ModemManager/serial inventory. Do not guess APN/PIN or open ports owned by a manager.
- Record `NO_DEVICE` for Here+ if no distinct device is observed.

### Task 8: Final evidence and handoff
- Run full tests locally and on Pi, measure STOP latency, inspect git diff/secrets.
- Complete `TEST-RESULTS.md`, `BLOCKERS.md`, `ROLLBACK.md`, `MORNING-HANDOFF.md`; commit locally without push.
