# Rollback

## General rule
Before changing a Pi system file/profile, the deploy/AP scripts copy the original to a timestamped directory under `/var/backups/quberon-robot-interface/` on the Pi (root-readable where sudo is used) and record the path in the command output/test log. Secrets are not copied into this repository.

## Ethernet management anchor (do not remove during AP work)
- Pi: `eth0 = 10.77.0.2/24`, profile `eth0`, autoconnect yes, no gateway, `ipv4.never-default=yes`.
- Mac peer: Ethernet `10.77.0.1/24`, Wi-Fi remains default internet route.
- Verify before and after network changes:
  ```sh
  ssh quberon1@10.77.0.2 'hostname; ip -br addr; ip route'
  ```

## Application rollback
On the Pi:
```sh
sudo systemctl disable --now quberon-robot-interface.service
sudo rm -f /etc/systemd/system/quberon-robot-interface.service
sudo systemctl daemon-reload
# Optional, only if removing the prototype entirely:
sudo rm -rf /opt/quberon-robot-interface /var/lib/quberon-robot-interface /etc/quberon-robot-interface
```
Removing `/var/lib/quberon-robot-interface` deletes the prototype SQLite state and generated demo-account data; back it up first if the audit trail is needed.

## Wi-Fi AP rollback
The AP script arms a Pi-local systemd rollback before activating the AP. Emergency/manual rollback on the Pi:
```sh
sudo systemctl stop quberon-ap-rollback.timer 2>/dev/null || true
sudo nmcli connection down Quberon-Demo-AP 2>/dev/null || true
sudo nmcli connection up aiwifi
nmcli device status
ip route
```
If NetworkManager profile deletion is desired after returning to the client profile:
```sh
sudo nmcli connection delete Quberon-Demo-AP
```
Do not delete the pre-existing `aiwifi` or `eth0` profiles as part of prototype rollback.

## Display rollback
No physical display configuration was changed in the mock-display path. If SPI is enabled in a future supervised step, back up `/boot/firmware/config.txt` first and restore that exact copy, then reboot only with a human present.
