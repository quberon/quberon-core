# Blockers

## High demo impact
1. **NEEDS PANEL LABEL / PHYSICAL WIRING VERIFICATION.** The e-ink panel model/revision and driver-board wiring are not identified; SPI is disabled and no `/dev/spidev*` exists. Physical display refresh and phone scan from the real panel are therefore NOT RUN. Human next step: photograph/read the panel and HAT labels and confirm wiring power-off against the exact schematic before any driver is run.
2. **Phone onboarding not yet human-tested.** No phone participated overnight. AP join, QR scan, CA trust and mobile browser login remain pending supervised tests. Do not claim phone login was tested.
3. **Pi AP activation needs Rasmus’s sudo at the Pi keyboard.** NetworkManager polkit denied profile creation over SSH (`Insufficient privileges`). Exact step: first `systemctl --user start quberon-ap-rollback.timer` (re-arms the 10-minute rollback), then `sudo ~/quberon-robot-interface/scripts/setup_ap.sh`. The rollback mechanism itself was exercised: the timer fired at 03:04 CET and client Wi-Fi/Ethernet/app health remained good. A second Wi-Fi client/phone is still needed to prove join/DHCP/app reachability from the phone segment.

## Medium
4. **Here+ not observed.** No distinct Here+ serial/USB device was found; RTK state is `NO_DEVICE` by available evidence. Need physical identification/transport and a correction source before any RTK claim.
5. **Cellular data not assumed usable.** Quectel EC25 USB hardware is present, but SIM/APN/registration/allowance were not established at inventory. Diagnostics must stay read-only/bounded and must not guess credentials/APN.
6. **Camera framing is not useful in the captured frame.** OV5647 responds, but the saved capture is nearly black and shows no display/label. Needs light/reposition/focus check by a human before it can debug the e-ink panel visually.

## Not blockers for the simulated demo
- Meta live API availability is optional; mocked, clearly labelled planning remains testable offline and STOP does not depend on it.
- Internet access is not required for local STOP against the simulator.
