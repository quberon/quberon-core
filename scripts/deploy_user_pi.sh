#!/bin/sh
set -eu
# Unprivileged fallback deployment. Preserves Ethernet SSH; no sudo required.
# System-service deployment in deploy_pi.sh remains preferred when an admin can enter sudo credentials interactively.
PI=${PI:-quberon1@10.77.0.2}
SRC=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ssh "$PI" 'mkdir -p ~/quberon-robot-interface ~/.local/share/quberon-robot-interface ~/.config/quberon-robot-interface ~/.config/systemd/user'
rsync -az --delete --exclude .git --exclude .venv --exclude artifacts/camera-eink-view.jpg "$SRC/" "$PI:~/quberon-robot-interface/"
ssh "$PI" 'set -eu
cd ~/quberon-robot-interface
[ -x .venv/bin/uvicorn ] || { python3 -m venv .venv; .venv/bin/pip install --disable-pip-version-check -r requirements.txt; }
chmod 700 ~/.local/share/quberon-robot-interface ~/.config/quberon-robot-interface
if [ ! -f ~/.config/quberon-robot-interface/ca.key ]; then
  openssl req -x509 -newkey rsa:3072 -sha256 -days 825 -nodes -keyout ~/.config/quberon-robot-interface/ca.key -out ~/.config/quberon-robot-interface/ca.crt -subj "/CN=Quberon Local Demo CA" -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign"
fi
if [ ! -f ~/.config/quberon-robot-interface/server.key ]; then
  openssl req -newkey rsa:3072 -nodes -keyout ~/.config/quberon-robot-interface/server.key -out /tmp/quberon-server.csr -subj "/CN=quberon-pi.local"
  printf "subjectAltName=DNS:quberon-pi.local,IP:10.77.0.2,IP:10.99.0.1\n" > ~/.config/quberon-robot-interface/server.ext
  openssl x509 -req -in /tmp/quberon-server.csr -CA ~/.config/quberon-robot-interface/ca.crt -CAkey ~/.config/quberon-robot-interface/ca.key -CAcreateserial -days 825 -sha256 -out ~/.config/quberon-robot-interface/server.crt -extfile ~/.config/quberon-robot-interface/server.ext
fi
chmod 600 ~/.config/quberon-robot-interface/ca.key ~/.config/quberon-robot-interface/server.key
cat > ~/.config/systemd/user/quberon-robot-interface.service <<EOF
[Unit]
Description=Quberon Robot Interface (simulated robot prototype, user service)
After=network.target
[Service]
WorkingDirectory=%h/quberon-robot-interface
Environment=ROBOT_ID=quberon-demo-001
Environment=QUBERON_DB_PATH=%h/.local/share/quberon-robot-interface/quberon.db
Environment=ALLOWED_HOSTS=localhost,127.0.0.1,10.77.0.2,10.99.0.1,quberon-pi.local
Environment=META_MODE=mock
Environment=DEMO_INSECURE_HTTP=false
ExecStart=%h/quberon-robot-interface/.venv/bin/uvicorn app.main:asgi_app --factory --host 0.0.0.0 --port 8443 --ssl-certfile %h/.config/quberon-robot-interface/server.crt --ssl-keyfile %h/.config/quberon-robot-interface/server.key
Restart=on-failure
RestartSec=3
[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
# Linger keeps the user service alive after SSH logout; without it logind stops the service.
loginctl enable-linger "$USER" 2>/dev/null || true
systemctl --user enable --now quberon-robot-interface.service
systemctl --user --no-pager --full status quberon-robot-interface.service | head -40
'
echo "User-service deploy completed; verify health separately."
