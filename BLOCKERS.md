# Blockers

## High demo impact
1. **Phone onboarding not yet human-tested.** No phone participated overnight. AP join, CA trust and mobile browser login remain pending supervised tests. Do not claim phone login was tested. (E-ink panel identity was resolved 2026-11-02 morning: 7.5″ e-Paper HAT V2, 800×480; one supervised refresh displayed the control QR and the user physically confirmed it.)
2. **Pi camera aim/occlusion (found 2026-11-02 morning).** Three captures (normal, long-exposure, brightened/rotated) show only a dark blurred diagonal surface with a blue-purple patch. The camera is not aimed at the e-ink display, is too close to a surface, or is obstructed. Human action: reposition camera/lens (power off if handling), then one daytime capture. Until then the camera cannot corroborate display state.
3. **Pi AP activation needs Rasmus’s sudo at the Pi keyboard.** NetworkManager polkit denied profile creation over SSH (`Insufficient privileges`). Exact step: first `systemctl --user start quberon-ap-rollback.timer` (re-arms the 10-minute rollback), then `sudo ~/quberon-robot-interface/scripts/setup_ap.sh`. The rollback mechanism itself was exercised: the timer fired at 03:04 CET and client Wi-Fi/Ethernet/app health remained good. A second Wi-Fi client/phone is still needed to prove join/DHCP/app reachability from the phone segment.

## Medium
4. **GNSS fix not yet obtained (device found night 2).** The Here+/u-blox receiver streams NMEA on `/dev/ttyACM0` and the reader service runs, but indoors it reports NO_FIX (0 satellites used). Needs sky view (window/outdoors) for first coordinates; RTK additionally needs a correction source that is not configured, so no RTK claim.
5. **Cellular data: DONE 2026-11-03** (was: needs sudo line). Profile creation is polkit-denied over SSH. Run `sudo ~/quberon-robot-interface/scripts/setup_cellular.sh` via the Mac one-liner in MORNING-HANDOFF. SIM/registration/signal were already proven; subscription data allowance remains unproven until that test runs.
6. **Cellular: SOLVED 2026-11-03.** EC25 data works (Tele2, `internet.tele2.se`, HTTP 200 via wwan0). Profile `Quberon-Tele2` exists with autoconnect off; bring it up deliberately with `sudo nmcli connection up Quberon-Tele2`. Failover policy (backup-only vs primary) is a future product decision, not yet configured.
7. **Camera framing is not useful in the captured frame.** OV5647 responds, but the saved capture is nearly black and shows no display/label. Needs light/reposition/focus check by a human before it can debug the e-ink panel visually.

## Not blockers for the simulated demo
- Meta live API availability is optional; mocked, clearly labelled planning remains testable offline and STOP does not depend on it.
- Internet access is not required for local STOP against the simulator.
