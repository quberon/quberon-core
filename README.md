# Quberon Robot Interface

Authenticated mobile web prototype for a **simulated** robot STOP-request workflow on a Raspberry Pi. It is not a safety-rated emergency stop and does not control physical robot hardware.

## Run tests (Mac)
```sh
~/.hermes/bin/uv venv .venv --python /Users/quberon1/.hermes/hermes-agent/venv/bin/python3.11
~/.hermes/bin/uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest -q
```

## Deploy (from Mac, preserves Ethernet SSH at 10.77.0.2)
```sh
DRY_RUN=1 scripts/deploy_pi.sh
scripts/deploy_pi.sh
scripts/healthcheck.sh https://10.77.0.2:8443 /etc/quberon-robot-interface/ca.crt  # run on Pi, or copy the public CA cert to the Mac first
```

Demo passwords are never stored in this repo. See `MORNING-HANDOFF.md`, `INVENTORY.md`, `BLOCKERS.md`, `ROLLBACK.md`, and `TEST-RESULTS.md`.
