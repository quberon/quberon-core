#!/bin/sh
# pi_readiness_check.sh - READ-ONLY first-session probe for the Quberon Pi.
#
# What it does:
#   0. Checks local checkout artifacts (no network).
#   1. Pings the Ethernet management address (default 10.77.0.2).
#   2. If reachable, runs ONE BatchMode SSH session of read-only inventory.
#   3. Detects the camera stack (rpicam-still / libcamera-still) by name only.
#
# What it NEVER does:
#   - No install, apt, pip, rsync, deploy, systemctl start/stop/restart/enable,
#     nmcli mutation, sudo, reboot, file write on the Pi, or camera capture.
#   - Camera capture is a separate manual step in docs/pi-readiness/README.md
#     because it writes a file to /tmp on the Pi.
#   - Never prints secrets: it never cats *.env, *.key, secret files or tokens.
#     It only reports presence/permissions of expected paths via test/stat.
#
# Usage (from repo checkout on the Mac):
#   scripts/pi_readiness_check.sh
#   PI=quberon1@10.77.0.2 scripts/pi_readiness_check.sh
#
# Exit codes:
#   0  SSH inventory completed (warnings may still be printed, e.g. no camera)
#   2  local prerequisite missing (ssh/ping/git not found, not a git checkout)
#   10 ping / Ethernet reachability failed - STOP, do not proceed to SSH/deploy
#   11 SSH (BatchMode) failed - STOP, do not retry with password/accept-new
#
# Stop conditions: see docs/pi-readiness/README.md section 6.

set -u

PI=${PI:-quberon1@10.77.0.2}
case "$PI" in
  *@*) PI_HOST=${PI##*@} ;;
  *)   PI_HOST=$PI ;;
esac
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=8 -o ConnectionAttempts=1 -o StrictHostKeyChecking=yes"

say()  { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }

say "== Quberon Pi readiness probe (read-only) =="
say "utc: $(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
say "target: $PI (host $PI_HOST)"
say "ssh_opts: $SSH_OPTS"
say ""

# ---------------------------------------------------------------- Phase 0
say "-- Phase 0: local artifacts --"
for cmd in git ping ssh; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    say "FAIL: required local command not found: $cmd"
    exit 2
  fi
done
SRC=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if ! git -C "$SRC" rev-parse --verify HEAD >/dev/null 2>&1; then
  say "FAIL: $SRC is not a git checkout"
  exit 2
fi
say "repo: $SRC"
say "local_commit: $(git -C "$SRC" rev-parse HEAD)"
say "local_branch: $(git -C "$SRC" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
for f in scripts/deploy_pi.sh scripts/deploy_user_pi.sh scripts/healthcheck.sh scripts/setup_ap.sh docs/pi-readiness/README.md; do
  if [ -f "$SRC/$f" ]; then say "present: $f"; else warn "missing local artifact: $f"; fi
done
say ""

# ---------------------------------------------------------------- Phase 1
say "-- Phase 1: Ethernet reachability (ping $PI_HOST) --"
case "$(uname -s 2>/dev/null || echo unknown)" in
  Darwin) ping -c 3 -W 2000 "$PI_HOST" ;;
  Linux)  ping -c 3 -W 2 "$PI_HOST" ;;
  *)      ping -c 3 "$PI_HOST" ;;
esac
ping_rc=$?
if [ "$ping_rc" -ne 0 ]; then
  say "FAIL: ping to $PI_HOST failed (rc=$ping_rc)."
  say "STOP: Ethernet management route not verified. Check cable, Mac 10.77.0.1/24,"
  say "Pi power, and that Wi-Fi is still the default route. Do NOT deploy or"
  say "fall back to guest-Wi-Fi SSH. See docs/pi-readiness/README.md section 6."
  exit 10
fi
say "ping: ok"
say ""

# ---------------------------------------------------------------- Phase 2+3
say "-- Phase 2/3: read-only SSH inventory + camera-stack detection --"
say "If SSH fails, this script stops; it will not prompt, accept a new host"
say "key, use a password, install anything, or restart anything."
# Single SSH session; every remote command below is read-only.
# shellcheck disable=SC2086
if ! ssh $SSH_OPTS "$PI" 'sh -s' <<'REMOTE'
set -u
say() { printf '%s\n' "$*"; }
say "remote_hostname: $(hostname 2>/dev/null || echo unknown)"
say "remote_utc: $(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
say "remote_uname: $(uname -a 2>/dev/null || echo unknown)"
if [ -r /proc/device-tree/model ]; then
  say "remote_model: $(tr -d '\000' < /proc/device-tree/model 2>/dev/null)"
fi
if [ -r /etc/os-release ]; then
  say "remote_os: $(grep '^PRETTY_NAME=' /etc/os-release 2>/dev/null | cut -d= -f2- | tr -d '"')"
fi
say "remote_uptime: $(uptime 2>/dev/null || echo unknown)"
say "-- network (read-only) --"
ip -br addr 2>/dev/null || say "WARN: ip -br addr unavailable"
ip route 2>/dev/null || say "WARN: ip route unavailable"
nmcli -t -f NAME,TYPE,DEVICE connection show --active 2>/dev/null || say "WARN: nmcli active connections unavailable"
say "-- power (read-only, if vcgencmd present) --"
if command -v vcgencmd >/dev/null 2>&1; then
  say "throttled: $(vcgencmd get_throttled 2>/dev/null || echo unavailable)"
  say "temp: $(vcgencmd measure_temp 2>/dev/null || echo unavailable)"
else
  say "WARN: vcgencmd not found"
fi
say "-- disk/memory (read-only) --"
df -h / 2>/dev/null || say "WARN: df unavailable"
free -h 2>/dev/null || say "WARN: free unavailable"
say "-- deployed code presence (no .git expected: deploy uses rsync --exclude .git) --"
for d in "$HOME/quberon-robot-interface" /opt/quberon-robot-interface; do
  if [ -d "$d" ]; then
    say "deployed_dir: $d"
    ls -ld "$d" 2>/dev/null || true
    if [ -d "$d/.git" ]; then
      say "deployed_git_commit: $(git -C "$d" rev-parse HEAD 2>/dev/null || echo unreadable)"
    else
      say "deployed_git_commit: unavailable (no .git in $d; record rsync source commit from the Mac instead)"
    fi
    for f in requirements.txt app/main.py; do
      if [ -f "$d/$f" ]; then say "present: $d/$f"; else say "absent: $d/$f"; fi
    done
  else
    say "absent_dir: $d"
  fi
done
say "-- services (read-only status only; nothing is started/restarted) --"
systemctl is-active quberon-robot-interface.service 2>/dev/null || say "system_service: not-active-or-absent"
systemctl --user is-active quberon-robot-interface.service 2>/dev/null || say "user_service: not-active-or-absent"
ss -lntp 2>/dev/null | grep -E ':(22|8443)[[:space:]]' || say "WARN: no listener on 22/8443 seen via ss"
say "-- config presence only (contents/secrets are NEVER printed) --"
for f in /etc/quberon-robot-interface/ca.crt "$HOME/.config/quberon-robot-interface/ca.crt"; do
  if [ -f "$f" ]; then say "present: $f"; else say "absent: $f"; fi
done
for f in /etc/quberon-robot-interface/app.env "$HOME/.config/quberon-robot-interface/app.env" "$HOME/.quberon-robot-interface-secrets.env"; do
  if [ -f "$f" ]; then stat -c 'present(mode %a): %n' "$f" 2>/dev/null || ls -l "$f"; else say "absent: $f"; fi
done
say "-- health endpoint over Ethernet, CA-verified if a public CA is present --"
CA=""
for c in /etc/quberon-robot-interface/ca.crt "$HOME/.config/quberon-robot-interface/ca.crt"; do
  if [ -f "$c" ]; then CA=$c; break; fi
done
if command -v curl >/dev/null 2>&1 && [ -n "$CA" ]; then
  if curl --fail --silent --max-time 8 --cacert "$CA" https://10.77.0.2:8443/healthz; then
    say ""
    say "healthz: ok (CA-verified, run on Pi)"
  else
    say "WARN: healthz curl failed (service may be stopped; do not restart from this probe)"
  fi
else
  say "WARN: curl or public CA cert absent on Pi; healthz not attempted"
fi
say "-- camera stack detection (names/versions only; NO capture here) --"
for tool in rpicam-still libcamera-still rpicam-hello libcamera-hello; do
  if command -v "$tool" >/dev/null 2>&1; then say "camera_tool: $tool -> $(command -v "$tool")"; else say "camera_tool_absent: $tool"; fi
done
if command -v rpicam-hello >/dev/null 2>&1; then
  rpicam-hello --list-cameras 2>&1 | head -20 || say "WARN: rpicam-hello --list-cameras failed"
elif command -v libcamera-hello >/dev/null 2>&1; then
  libcamera-hello --list-cameras 2>&1 | head -20 || say "WARN: libcamera-hello --list-cameras failed"
else
  say "WARN: no rpicam-hello/libcamera-hello; camera presence not proven"
fi
say "-- end of remote inventory --"
REMOTE
then
  say "FAIL: BatchMode SSH to $PI failed."
  say "STOP: Do not retry interactively, do not add StrictHostKeyChecking=no,"
  say "do not accept a changed host key blindly. Verify the fingerprint via a"
  say "trusted channel, check 'ssh -vv' diagnostics if needed, and re-run."
  exit 11
fi
say ""
say "probe: complete (read-only). Next manual steps: docs/pi-readiness/README.md"
say "Phase 3 camera capture, then the Phase 4 deployment gate. This script made"
say "no changes on the Pi."
