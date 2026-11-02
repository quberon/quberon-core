# Inventory

Captured: 2026-11-02 overnight session (Pi clock reported Mon Nov 2 01:35 UTC 2026; Mac/Pi clocks may be set to a future test date).

## Measured facts

### Raspberry Pi
- Model: Raspberry Pi 3 Model B Plus Rev 1.3 (`/proc/device-tree/model`).
- OS: Debian GNU/Linux 13 (trixie), Debian 13.7, kernel `6.18.50+rpt-rpi-v8`, aarch64.
- Hostname/user: `quberon-pi` / `quberon1` (uid 1000; groups include sudo, gpio, i2c, spi, video, dialout, netdev).
- RAM/swap: 905 MiB RAM, 904 MiB swap. Root filesystem 117 GB, 110 GB available at inventory.
- Temperature 46.2 C; `vcgencmd get_throttled` returned `0x0` (no throttling/undervoltage flags observed at that moment).
- Management route preserved: Ethernet `eth0 = 10.77.0.2/24`, Mac peer `10.77.0.1`; SSH key login verified before this project and again during deployment checks recorded in `TEST-RESULTS.md`.
- Existing default route before AP work: Wi-Fi `wlan0 = 192.168.101.222/24` via `192.168.101.1`; Ethernet has no gateway and `ipv4.never-default=yes` on profile `eth0`.
- NetworkManager and SSH active; ModemManager, dhcpcd and systemd-networkd inactive at inventory.
- Listening ports before project deployment: SSH 22 and mDNS 5353 only (plus ephemeral UDP).

### Camera
- libcamera/rpicam detects camera 0: OmniVision OV5647, 2592x1944, CSI.
- `rpicam-still` captured `/tmp/quberon-camera.jpg` on the Pi; a copy is stored as `artifacts/camera-eink-view.jpg` (99 KB).
- Visual inspection of that capture: almost entirely black/blurred dark blue; no e-ink display, panel label, HAT, wiring or readable text is visible. Therefore the camera proves the sensor/software path responds, but does not identify the display and does not prove useful framing/focus in current darkness/position.

### E-ink / GPIO / SPI
- No `/dev/spidev*` devices present.
- `/boot/firmware/config.txt`: SPI line is commented out (`#dtparam=spi=on`); overlays present include `vc4-kms-v3d`, `dwc2,dr_mode=host`, and `[pi5] dtoverlay=nospi10`.
- `pinctrl get` shows GPIO8/10/11 and candidate display GPIOs 17/18/24/25 as inputs with no active alternate SPI function at inventory. This is not wiring verification.
- Panel model/label, Waveshare driver-board revision, pin mapping and power requirements are **not identified** from available evidence. Physical display driving is therefore blocked; mock display only.

### Cellular / Sixfab-related hardware
- USB detects Quectel EC25 LTE modem (`2c7c:0125`) via Sixfab-style USB path; interfaces include `option` serial ports `/dev/ttyUSB0`–`ttyUSB3` and `qmi_wwan`/`cdc_wdm` (`/dev/cdc-wdm0`, `wwan0` DOWN).
- Sixfab HAT revision itself was not read from a label or EEPROM; do not claim a revision.
- Bounded read-only AT diagnostics on `/dev/ttyUSB2` (2026-11-02 overnight): `ATI` → Quectel EC25, revision `EC25EFAR06A03M4G`; `AT+CPIN?` → `READY` (SIM present, no PIN lock observed); `AT+CREG?/AT+CGREG?/AT+CEREG?` → stat `1` (registered, home network); `AT+CSQ` → `22,99`; `AT+QNWINFO` → FDD LTE, PLMN `24007`, LTE Band 3; `AT+COPS?` → Tele2 (Sweden), LTE.
- No GSM/NetworkManager modem connection profile exists and ModemManager is inactive, so **no cellular data session was started and no data test was run**. Registration/signal is not proof of an active data plan/APN allowance.

### Here+ GNSS
- No distinct Here+ USB/serial device was observed. `/dev/serial/by-id` entries all belong to the Quectel modem (`Android_Android` interfaces). No `/dev/ttyACM*` device.
- Here+ state at inventory: `NO_DEVICE` observed by this inspection path. A device attached through an unpowered/other transport cannot be excluded.

## Assumptions not treated as facts
- The e-ink panel is not assumed to be a specific Waveshare size/revision.
- EC25 presence does not prove an active SIM, APN, registration or data allowance.
- OV5647 camera presence does not prove it is aimed usefully at the display in current lighting.
- `quberon-demo-001` is a software identity for the simulated robot, not a physical robot serial number.
