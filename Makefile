.PHONY: setup test demo core

PYTHON ?= $(shell command -v python3.11 || command -v python3)
VENV := .venv
VENV_PY := $(VENV)/bin/python

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PY) -m pip install -r requirements.txt
	@if command -v cargo >/dev/null 2>&1; then \
		$(MAKE) core; \
	else \
		echo "secure core not built - STOP will run with unsigned attestation; see docs/SECURE-CORE.md"; \
	fi

core:
	@if command -v cargo >/dev/null 2>&1; then \
		cargo build --workspace; \
	else \
		echo "secure core not built - STOP will run with unsigned attestation; see docs/SECURE-CORE.md"; \
	fi

test:
	$(VENV_PY) -m pytest -q

demo:
	$(VENV_PY) -m uvicorn app.main:app --host 127.0.0.1 --port 8000
