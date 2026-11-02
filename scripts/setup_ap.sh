#!/bin/sh
# Create/activate the isolated Quberon demo AP. Run on the Pi.
# Preconditions verified by the operator/agent before running:
#  - Ethernet SSH (10.77.0.2) reachable from the Mac (recovery anchor)
#  - ap_rollback.sh systemd user timer armed (quberon-ap-rollback.timer)
#  - AP_PASSWORD present in ~/.quberon-robot-interface-secrets.env (mode 600)
set -eu
SECRETS_FILE=${SECRETS_FILE:-/home/quberon1/.quberon-robot-interface-secrets.env}
set -a
. "$SECRETS_FILE"
set +a
SSID=${AP_SSID:-Quberon-Demo}
if nmcli -t -f NAME connection show | grep -qx Quberon-Demo-AP; then
  echo "Profile Quberon-Demo-AP already exists; activating"
else
  nmcli connection add type wifi ifname wlan0 con-name Quberon-Demo-AP autoconnect no \
    ssid "$SSID" wifi.mode ap wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$AP_PASSWORD" \
    ipv4.method shared ipv4.addresses 10.99.0.1/24
fi
nmcli connection up Quberon-Demo-AP
nmcli device status
ip -br addr
ip route
