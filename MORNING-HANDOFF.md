# Morning Handoff — Quberon Robot Interface (overnight prototype)

## What exists now
An authenticated mobile web prototype for a **simulated** robot STOP-request workflow, deployed on the Raspberry Pi and verified end-to-end over the direct Ethernet cable. No physical robot, GPIO, serial robot control, or e-ink hardware was driven.

- Mac workspace: `/Users/quberon1/quberon-robot-interface`
- Git: branch `feature/overnight-prototype`, local commit created at the end of the run (see `git log --oneline -1` in the workspace). Nothing pushed.
- Pi deployment: `quberon1@10.77.0.2`, code at `~/quberon-robot-interface`, state DB at `~/.local/share/quberon-robot-interface/quberon.db`
- Service: systemd **user** service `quberon-robot-interface.service` (enabled, linger on). The preferred system service in `systemd/` + `scripts/deploy_pi.sh` still needs an interactive sudo session to install.
- Robot identity: `quberon-demo-001`, `adapter_mode=SIMULATION`, fresh state starts STOP-latched.

## Reachable URLs (verified)
- From this Mac over Ethernet, with CA trust: `https://10.77.0.2:8443/robots/quberon-demo-001`
- Health: `https://10.77.0.2:8443/healthz`
- Public CA certificate (safe to copy to a phone for manual trust): `artifacts/quberon-ca.crt` in the workspace, or on the Pi at `~/.config/quberon-robot-interface/ca.crt`. CA/server private keys stay on the Pi (mode 600) and are not in git.
- Intended phone URL after AP activation: `https://10.99.0.1:8443/robots/quberon-demo-001` (already in the server cert SANs and the URL QR). **Not yet live** — see blockers.

## Credentials (locations only, no passwords in this file)
- Mac: `/Users/quberon1/.quberon-robot-interface-secrets.env` (mode 600)
- Pi copy: `/home/quberon1/.quberon-robot-interface-secrets.env` (mode 600)
- Demo accounts: `viewer1` (read), `operator1` (STOP/task/plan), `admin1` (+ simulation reset). Passwords are the `*_PASSWORD` values in that file. These are throwaway prototype accounts.

## Commands
Run tests (Mac):
```sh
cd /Users/quberon1/quberon-robot-interface && .venv/bin/python -m pytest -q
```
Deploy safely (user service, no sudo):
```sh
cd /Users/quberon1/quberon-robot-interface && scripts/deploy_user_pi.sh
```
Inspect health/logs on the Pi:
```sh
ssh quberon1@10.77.0.2 'systemctl --user status quberon-robot-interface.service; curl -s --cacert ~/.config/quberon-robot-interface/ca.crt https://10.77.0.2:8443/healthz'
```
Rollback: see `ROLLBACK.md` (app removal, AP rollback, Ethernet anchor must stay).

## Verified (evidence in TEST-RESULTS.md)
- 11/11 tests pass on Mac and on the Pi.
- Live: login → STOP acknowledged by simulator → audit event; admin reset does not start a task; operator task after reset; STOP again.
- Service restart preserves the STOP latch.
- STOP software latency, Mac→Pi Ethernet/HTTPS, 30 samples: median 21 ms, p95 25 ms. Not a physical stopping time.
- QR PNGs decode (OpenCV) to the configured SSID/PSK payload and the exact control URL. Wi-Fi QR is a git-ignored local artifact because it encodes the PSK.
- Cellular: Quectel EC25 (`EC25EFAR06A03M4G`), SIM READY, registered on Tele2 LTE Band 3, CSQ 22. No data session started (no APN/profile verified).
- Two real bugs were found and fixed during the night: (1) CA without key-usage extensions rejected by strict TLS verifiers; (2) systemd linger off made the user service die at SSH logout, causing intermittent connection refusals.

## Simulated / mocked / not tested — do not overclaim
- Robot: simulated only. “ACKNOWLEDGED” means the simulator recorded the request.
- E-ink: mock PNG only (`artifacts/display-mock.png`, git-ignored). Panel model/wiring unknown, SPI disabled, camera captures were nearly black. No physical refresh, no real phone scan of a panel.
- Meta: mock provider only, clearly labelled `provider: mock`. No Meta API config/keys exist on this Mac, so no live model call was made. STOP never depends on it.
- Phone onboarding: not tested with a real phone.
- Guest-Wi-Fi client-to-client isolation still (correctly) prevents reaching the Pi over home Wi-Fi from another Mac. The direct Ethernet link is the verified management path.

## Blockers ranked by demo impact (details in BLOCKERS.md)
1. **AP activation needs your sudo at the Pi keyboard** (NetworkManager polkit). Run:
   ```sh
   sudo ~/quberon-robot-interface/scripts/setup_ap.sh
   ```
   Then tell Hermes “AP is up” for verification (Ethernet SSH check, SSID scan, isolation checks). Until then, re-arm the rollback timer first:
   ```sh
   systemctl --user start quberon-ap-rollback.timer
   ```
2. **E-ink panel label/wiring verification** by a human, power-off, before any driver/SPI change.
3. **Real phone test**: join AP, trust CA, scan QRs, log in, STOP.
4. **Cellular data**: needs a verified Tele2 APN/profile and your go-ahead before any data session.
5. **Here+**: no device observed; needs physical identification/transport and a correction source before any RTK claim.
6. **Supervised reboot test** of the Pi to confirm user-service + AP behaviour across reboot.

## Two-minute demo script (once AP + phone steps are done)
1. Show the e-ink mock/photo and explain: simulated robot, not an emergency stop.
2. Phone scans Wi-Fi QR → joins `Quberon-Demo`.
3. Phone scans control QR → opens `https://10.99.0.1:8443/robots/quberon-demo-001` (after CA trust).
4. Log in as `operator1`; show status: SIMULATION, latch state, observed state.
5. Request a Meta (mock) plan; show validation and that the latch blocks tasks.
6. Admin resets simulation; request simulated task; then press **STOP request**.
7. Show `ACKNOWLEDGED / SIMULATED_STOPPED` plus the audit event.
8. Explain STOP worked locally with no internet/Meta/GNSS/display dependency.

## Supervised next-day checklist
- [ ] Run the sudo AP command above; verify with Hermes.
- [ ] Photograph e-ink panel + HAT labels; confirm wiring against the exact schematic.
- [ ] Phone: CA trust, AP join, QR scans, login, STOP.
- [ ] Optional supervised Pi reboot; re-verify Ethernet SSH, service, latch.
- [ ] Only after that: specify any real robot adapter separately, with manufacturer docs and hazard assessment. No real motion is authorized by this prototype.
