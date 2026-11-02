#!/bin/sh
# Create and test the Tele2 (Sweden) EC25 data profile. Run WITH sudo on the Pi.
# APN internet.tele2.se is Tele2 Sweden's published consumer APN (MCC 240 / MNC 07,
# matching the registered PLMN 24007). No username/password.
# Safe defaults: autoconnect off, route metric worse than Wi-Fi, and the profile
# is left DOWN after the test unless KEEP_UP=1 is set.
set -eu
APN=${APN:-internet.tele2.se}
# NetworkManager can only use the QMI device once ModemManager manages it.
# ModemManager is not installed in the base image; install it if missing.
if ! systemctl cat ModemManager.service >/dev/null 2>&1; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq modemmanager
fi
systemctl enable --now ModemManager
# The modem was plugged in before ModemManager existed, so its ports never got
# ID_MM_* udev tags. Re-trigger udev for modem-related subsystems, then scan.
udevadm trigger --action=add --subsystem-match=tty --subsystem-match=usbmisc --subsystem-match=net 2>/dev/null || true
udevadm settle 2>/dev/null || true
mmcli --scan-modems 2>/dev/null || true
i=0
while [ $i -lt 30 ]; do
  if nmcli device status | grep -qiE 'gsm|cdc-wdm'; then break; fi
  i=$((i+1)); sleep 1
done
mmcli -L 2>/dev/null || true
nmcli device status
nmcli -t -f NAME,TYPE connection show > /tmp/nm-connections-before-cellular.txt
if nmcli -t -f NAME connection show | grep -qx Quberon-Tele2; then
  echo "Profile Quberon-Tele2 already exists"
else
  nmcli connection add type gsm ifname cdc-wdm0 con-name Quberon-Tele2 \
    gsm.apn "$APN" connection.autoconnect no \
    ipv4.route-metric 700 ipv6.method disabled
fi
nmcli connection up Quberon-Tele2
ip -br addr
ip route
ADDR=$(ip -4 -o addr show wwan0 2>/dev/null | awk '{print $4}' | cut -d/ -f1 || true)
echo "wwan IPv4: ${ADDR:-none}"
if [ -n "${ADDR:-}" ]; then
  echo "--- isolated-ish interface test (few small requests) ---"
  curl --interface wwan0 --max-time 15 -s -o /dev/null -w "example.com via wwan0: HTTP %{http_code} in %{time_total}s\n" https://example.com || echo "curl via wwan0 FAILED"
  cat /sys/class/net/wwan0/statistics/rx_bytes /sys/class/net/wwan0/statistics/tx_bytes 2>/dev/null || true
fi
if [ "${KEEP_UP:-0}" != "1" ]; then
  nmcli connection down Quberon-Tele2
  echo "Profile brought back down (KEEP_UP=1 to leave it up)."
fi
nmcli device status
