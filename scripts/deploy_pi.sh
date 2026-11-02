#!/bin/sh
set -eu
# Run from repo checkout on the Mac. Uses the verified Ethernet management route.
PI=${PI:-quberon1@10.77.0.2}
SRC=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
echo "Deploying $SRC -> $PI:/opt/quberon-robot-interface (dry-run=${DRY_RUN:-0})"
if [ "${DRY_RUN:-0}" = "1" ]; then
  rsync -azn --delete --exclude .git --exclude .venv --exclude artifacts/camera-eink-view.jpg "$SRC/" "$PI:/tmp/quberon-robot-interface-stage/"
  exit 0
fi
ssh "$PI" 'sudo -n true && mkdir -p /tmp/quberon-robot-interface-stage'
rsync -az --delete --exclude .git --exclude .venv "$SRC/" "$PI:/tmp/quberon-robot-interface-stage/"
ssh "$PI" 'set -eu
sudo -n id quberon >/dev/null 2>&1 || sudo -n useradd --system --home /var/lib/quberon-robot-interface --shell /usr/sbin/nologin quberon
sudo -n mkdir -p /opt/quberon-robot-interface /var/lib/quberon-robot-interface /etc/quberon-robot-interface /var/backups/quberon-robot-interface
sudo -n cp -a /tmp/quberon-robot-interface-stage/. /opt/quberon-robot-interface/
sudo -n chown -R root:root /opt/quberon-robot-interface
sudo -n chown quberon:quberon /var/lib/quberon-robot-interface
sudo -n chmod 700 /var/lib/quberon-robot-interface
if [ ! -x /opt/quberon-robot-interface/.venv/bin/uvicorn ]; then
  sudo -n apt-get update && sudo -n apt-get install -y python3-venv python3-pip
  sudo -n python3 -m venv /opt/quberon-robot-interface/.venv
  sudo -n /opt/quberon-robot-interface/.venv/bin/pip install --disable-pip-version-check -r /opt/quberon-robot-interface/requirements.txt
fi
if [ ! -f /etc/quberon-robot-interface/ca.key ]; then
  sudo -n openssl req -x509 -newkey rsa:3072 -sha256 -days 825 -nodes -keyout /etc/quberon-robot-interface/ca.key -out /etc/quberon-robot-interface/ca.crt -subj "/CN=Quberon Local Demo CA" -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign"
fi
if [ ! -f /etc/quberon-robot-interface/server.key ]; then
  sudo -n openssl req -newkey rsa:3072 -nodes -keyout /etc/quberon-robot-interface/server.key -out /tmp/quberon-server.csr -subj "/CN=quberon-pi.local"
  printf "subjectAltName=DNS:quberon-pi.local,IP:10.77.0.2,IP:10.99.0.1\n" | sudo -n tee /etc/quberon-robot-interface/server.ext >/dev/null
  sudo -n openssl x509 -req -in /tmp/quberon-server.csr -CA /etc/quberon-robot-interface/ca.crt -CAkey /etc/quberon-robot-interface/ca.key -CAcreateserial -days 825 -sha256 -out /etc/quberon-robot-interface/server.crt -extfile /etc/quberon-robot-interface/server.ext
fi
sudo -n chmod 600 /etc/quberon-robot-interface/ca.key /etc/quberon-robot-interface/server.key
sudo -n chown root:quberon /etc/quberon-robot-interface/server.key /etc/quberon-robot-interface/server.crt /etc/quberon-robot-interface/ca.crt
sudo -n chmod 640 /etc/quberon-robot-interface/server.key
if [ ! -f /etc/quberon-robot-interface/app.env ]; then sudo -n cp /opt/quberon-robot-interface/config/example.env /etc/quberon-robot-interface/app.env; fi
sudo -n cp /opt/quberon-robot-interface/systemd/quberon-robot-interface.service /etc/systemd/system/quberon-robot-interface.service
sudo -n systemctl daemon-reload
sudo -n systemctl enable --now quberon-robot-interface.service
sudo -n systemctl --no-pager --full status quberon-robot-interface.service | head -40
'
echo "Deploy command completed; verify health separately."
