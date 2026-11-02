#!/bin/sh
set -eu
BASE=${1:-https://10.77.0.2:8443}
CA=${2:-/etc/quberon-robot-interface/ca.crt}
curl --fail --silent --cacert "$CA" "$BASE/healthz"
echo
systemctl is-active quberon-robot-interface.service
