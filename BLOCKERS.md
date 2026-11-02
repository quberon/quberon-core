# Blockers

## High demo impact
1. **Phone onboarding not yet human-tested.** No phone participated overnight. AP join, CA trust and mobile browser login remain pending supervised tests. Do not claim phone login was tested. (E-ink panel identity was resolved 2026-11-02 morning: 7.5″ e-Paper HAT V2, 800×480; one supervised refresh displayed the control QR and the user physically confirmed it.)
2. **Pi camera aim/occlusion (found 2026-11-02 morning).** Three captures (normal, long-exposure, brightened/rotated) show only a dark blurred diagonal surface with a blue-purple patch. The camera is not aimed at the e-ink display, is too close to a surface, or is obstructed. Human action: reposition camera/lens (power off if handling), then one daytime capture. Until then the camera cannot corroborate display state.
3. **Pi AP activation needs Rasmus’s sudo at the Pi keyboard.** NetworkManager polkit denied profile creation over SSH (`Insufficient privileges`). Exact step: first `systemctl --user start quberon-ap-rollback.timer` (re-arms the 10-minute rollback), then `sudo ~/quberon-robot-interface/scripts/setup_ap.sh`. The rollback mechanism itself was exercised: the timer fired at 03:04 CET and client Wi-Fi/Ethernet/app health remained good. A second Wi-Fi client/phone is still needed to prove join/DHCP/app reachability from the phone segment.

## Medium
4. **Here+ not observed.** No distinct Here+ serial/USB device was found; RTK state is `NO_DEVICE` by available evidence. Need physical identification/transport and a correction source before any RTK claim.
5. **Cellular data not assumed usable.** Quectel EC25 USB hardware is present, but SIM/APN/registration/allowance were not established at inventory. Diagnostics must stay read-only/bounded and must not guess credentials/APN.
6. **Camera framing is not useful in the captured frame.** OV5647 responds, but the saved capture is nearly black and shows no display/label. Needs light/reposition/focus check by a human before it can debug the e-ink panel visually.

## Not blockers for the simulated demo
- Meta live API availability is optional; mocked, clearly labelled planning remains testable offline and STOP does not depend on it.
- Internet access is not required for local STOP against the simulator.
