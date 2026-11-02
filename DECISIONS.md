# Decisions

- **D1 — Simulation only.** The only enabled robot adapter is `adapters/robot_sim.py`. No GPIO, serial, CAN, ROS or vendor robot control path is implemented or exposed.
- **D2 — STOP means STOP request.** UI/API terminology avoids “certified emergency stop.” Successful simulated acknowledgement means the simulator recorded it, not that a physical robot stopped.
- **D3 — Fresh installs start latched.** Missing/corrupt persistent state must fail closed for simulated task acceptance.
- **D4 — HTTPS default.** A project-local CA and server certificate are generated on the Pi outside the repository. Phones must manually trust the CA before being told login is secure; no warning bypass is instructed.
- **D5 — No physical e-ink driving overnight.** Panel identity, wiring and SPI state are unverified, and unattended reboot for SPI is outside the brief. A mock renderer produces the intended layout/QR assets.
- **D6 — Preserve Ethernet recovery.** `10.77.0.2/24` Ethernet SSH is the management anchor. Wi-Fi changes must be protected by a Pi-local timed rollback until verified.
- **D7 — AP isolation by design.** Project AP uses `10.99.0.1/24`, chosen after observing Ethernet `10.77.0.0/24`, guest Wi-Fi `192.168.101.0/24` and Tailscale on the Mac. No intentional AP internet forwarding; phone access is for DHCP/DNS and the app only, subject to verification limits in `TEST-RESULTS.md`.
- **D8 — Meta is advisory only.** Meta output is schema-validated and then passed through deterministic local policy. It cannot reset the latch, grant capabilities, execute tools or command hardware. Mock responses are labelled as mock.
- **D9 — Demo accounts are local and throwaway.** Passwords are generated/stored outside the repo in a mode-0600 file. No real Rasmus credentials are reused.
