# Test Results

Environment: Mac (Python 3.11 venv) and Raspberry Pi 3B+ (Python 3.13 venv, Debian 13). Pi tests are slower mainly due to PBKDF2 password hashing on ARM.

| # | Test | Result | Evidence |
|---|---|---|---|
| 1 | Local unit/integration suite | PASS | `pytest -q` on Mac: **11 passed** |
| 2 | Pi unit/integration suite | PASS | `pytest -q` on Pi: **11 passed** (36 s) |
| 3 | Unauthenticated/viewer STOP rejected; operator STOP allowed; cross-robot 404 | PASS | Covered in `tests/test_app.py` |
| 4 | CSRF missing rejected; login rate limit after 5 failures | PASS | Covered in tests |
| 5 | Idempotent STOP duplicate converges; conflicting key 409 | PASS | Covered in tests |
| 6 | Fresh state latched; simulated task blocked while latched; admin reset does not start a task | PASS | Covered in tests + live Pi flow below |
| 7 | Adapter failure yields `UNKNOWN`, not a stopped claim | PASS | Covered in tests (`adapter_fail=True`) |
| 8 | Restart persistence (unit level) | PASS | Covered in tests (new app instance, same DB) |
| 9 | Meta mock + prompt-injection text cannot reset latch; bad schema rejected; live provider unconfigured raises cleanly | PASS | Covered in tests |
| 10 | QR payload escaping; no login terms in Wi-Fi QR payload | PASS | Covered in tests |
| 11 | QR image decoding | PASS | OpenCV QRCodeDetector decoded both PNGs after switching to error-correction Q. Wi-Fi QR decoded to the configured SSID with PSK present; URL QR decoded exactly to `https://10.99.0.1:8443/robots/quberon-demo-001`. The Wi-Fi QR image itself is a local artifact and is git-ignored because it encodes the PSK. |
| 12 | Deployed health over Ethernet HTTPS | PASS | `curl --cacert artifacts/quberon-ca.crt https://10.77.0.2:8443/healthz` → `{"ok":true,"robot_id":"quberon-demo-001","adapter_mode":"SIMULATION","persistence_ok":true}` |
| 13 | Live login → status → STOP → audit event | PASS | Operator login 303; STOP 200 `ACKNOWLEDGED / SIMULATED_STOPPED`; top audit event `STOP / ACKNOWLEDGED / operator1` |
| 14 | Live admin reset → operator simulated task → STOP | PASS | Reset 200 (`task_started:false`); task 200 `SIMULATED_TASK_ACTIVE`; STOP 200 `ACKNOWLEDGED` |
| 15 | Service restart persistence on Pi | PASS | `systemctl --user restart`; after restart status showed `stop_latched=true, SIMULATED_STOPPED` |
| 16 | STOP latency (Mac → Pi Ethernet, HTTPS, authenticated) | PASS | `scripts/measure_latency.py`, 30 samples: **median 21.07 ms, p95 24.72 ms, min 19.57 ms, max 49.83 ms**. Software latch latency only; not a physical stopping time. |
| 17 | TLS CA strict verification | PASS after fix | Initial CA lacked key-usage extensions and Python rejected it; CA/server cert regenerated with `CA:TRUE` + key usage and SANs (`quberon-pi.local`, 10.77.0.2, 10.99.0.1). Old certs backed up on Pi under `~/.config/quberon-robot-interface/backup-20261102025020/`. |
| 18 | User-service survival after SSH logout | PASS after fix | Root cause of intermittent refusals: systemd linger was off, so logind stopped the user service at SSH logout. `loginctl enable-linger quberon1` → `Linger=yes`; service then stayed active with no SSH session. Recorded in deploy script. |
| 19 | Camera capture | PASS (sensor) / BLOCKED (display ID) | OV5647 detected; two captures saved. Both are nearly black; no display/label/wiring visible. |
| 20 | Cellular diagnostics | PASS (registration) / NOT RUN (data) | EC25 `EC25EFAR06A03M4G`, SIM READY, registered Tele2 LTE Band 3, CSQ 22. No modem data profile/APN verified, so no data session was started. |
| 21 | Here+ GNSS | BLOCKED | No distinct device observed; state `NO_DEVICE` by available evidence. |
| 22 | Physical e-ink refresh / phone scan of real panel | PASS (display) / NOT RUN (phone scan) | 2026-11-02 morning, supervised: panel identified from box label '7.5inch e-Paper HAT' + user-read 'V2' → Waveshare 7.5″ V2 (800×480, official `epd7in5_V2`, pins RST17/DC25/CS8/BUSY24/PWR18 confirmed in official code commit `d28b3c4`). SPI enabled by user via sudo + reboot; `/dev/spidev0.0` present. `scripts/show_qr_display.py` under an external 90 s timeout with a 180 s refresh lock → `DISPLAY_REFRESH_DONE`; user physically confirmed the QR is on the panel. Pi camera could not corroborate: three captures (normal/long-exposure/brightened) show only a dark blurred diagonal surface — camera not aimed at the display or obstructed/too close. Phone scan of the real panel not done yet; the QR target also needs AP activation. |
| 23 | Wi-Fi AP activation + phone join | BLOCKED (human sudo step) | AP profile creation requires admin polkit rights. Rollback timer was armed and fired at 03:04 CET, restoring/keeping client Wi-Fi; Ethernet SSH and app health remained good afterwards. Awaiting `sudo ~/quberon-robot-interface/scripts/setup_ap.sh` at the Pi keyboard, then verification. |
| 24 | Pi reboot persistence | PASS | Supervised reboots 2026-11-02 morning (user-requested restart + SPI-enable reboot): user service returned active automatically (enabled + linger), health OK, STOP latch persisted, `throttled=0x0`. |
| 25 | Secret scan of repo working tree | PASS | No demo/AP password values found in tracked files (SSID is public by design). Private values live only in mode-0600 files outside git and in the git-ignored Wi-Fi QR artifact. |
