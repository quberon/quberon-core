#!/bin/sh
# Emergency/manual rollback: restore the pre-existing Wi-Fi client profile.
set -eu
nmcli connection down Quberon-Demo-AP 2>/dev/null || true
nmcli connection up aiwifi
nmcli device status
ip route
