"""Coverage for app.main:asgi_app() -- the uvicorn --factory entrypoint.

No other test module names asgi_app. These tests pin the factory
contract used by Makefile demo, the systemd unit and
scripts/deploy_user_pi.sh (all: `uvicorn app.main:asgi_app --factory`):

* zero-arg callable returning a fresh FastAPI app per call (not a
  module-level singleton created at import time);
* the DB is the one named by QUBERON_DB_PATH (create_app's env fallback),
  created only there, with fail-closed initial latch state;
* the app actually serves through the ASGI interface (healthz, redirect,
  public page, auth boundary, logged-in status).

Determinism with/without Rust: QUBERON_SECURE_CORE_MODE is removed, so
client_from_env() returns None in both modes (no mode = no client; a
missing binary also = None). The app then reports the secure core as
unavailable -- STOP would run unsigned, motion-permitting ops blocked --
regardless of whether target/*/quberon-secure-core-cli exists. No test
here asserts a signed decision, so none needs the Rust binary.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import ROBOT_ID, SECURE_CORE_NOT_BUILT_MESSAGE, Store, asgi_app

# Env vars that would otherwise make asgi_app()'s create_app() call
# environment-dependent (secure-core provisioning, provider, adapter).
_AMBIENT = (
    "QUBERON_SECURE_CORE_MODE",
    "QUBERON_SECURE_CORE_BIN",
    "QUBERON_SECURE_CORE_DB",
    "QUBERON_SECURE_CORE_SIGNING_KEY_FILE",
    "QUBERON_SECURE_CORE_SIGNING_KEY_HEX",
    "QUBERON_SECURE_CORE_VERIFYING_KEY_HEX",
    "META_MODE",
    "SIM_ADAPTER_FAIL",
)


@pytest.fixture()
def factory_db(tmp_path, monkeypatch):
    """Point QUBERON_DB_PATH at an isolated tmp DB and clear ambient env."""
    for var in _AMBIENT:
        monkeypatch.delenv(var, raising=False)
    db = tmp_path / "asgi" / "factory.db"
    monkeypatch.setenv("QUBERON_DB_PATH", str(db))
    return db


def _client(app):
    # https + testserver: ALLOWED_HOSTS includes testserver and the
    # session cookie is Secure unless DEMO_INSECURE_HTTP was set at
    # import time (same convention as tests/test_app.py).
    return TestClient(app, base_url="https://testserver")


def test_asgi_app_factory_signature_and_fresh_instances(factory_db):
    # uvicorn --factory requires a zero-arg callable.
    assert callable(asgi_app)
    assert inspect.signature(asgi_app).parameters == {}
    first = asgi_app()
    second = asgi_app()
    assert isinstance(first, FastAPI)
    assert isinstance(second, FastAPI)
    # Each call builds a new app/store -- not a shared import-time app.
    assert first is not second
    assert first.state.store is not second.state.store
    assert first.title == "Quberon Robot Interface"


def test_asgi_app_uses_env_db_path_and_starts_latched(factory_db):
    app = asgi_app()
    assert app.state.db_path == str(factory_db.resolve())
    assert factory_db.is_file()
    # No secure-core client without an explicit mode (both Rust modes),
    # so no *-secure-core.db / .seq / .epoch files are provisioned.
    assert app.state.secure_core is None
    created = {p.name for p in factory_db.parent.iterdir()}
    assert created <= {"factory.db", "factory.db-wal", "factory.db-shm"}
    # Fresh state starts fail-closed: latch set, simulated-stopped.
    assert app.state.store.persistence_ok is True
    assert app.state.store.stop_latched is True
    assert app.state.store.observed_state == "SIMULATED_STOPPED"


def test_asgi_app_serves_health_redirect_page_and_auth_boundary(factory_db):
    client = _client(asgi_app())
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {
        "ok": True,
        "robot_id": ROBOT_ID,
        "adapter_mode": "SIMULATION",
        "persistence_ok": True,
    }
    root = client.get("/", follow_redirects=False)
    assert root.status_code == 302
    assert root.headers["location"] == f"/robots/{ROBOT_ID}"
    page = client.get(f"/robots/{ROBOT_ID}")
    assert page.status_code == 200
    assert "SIMULATED ROBOT - NOT AN EMERGENCY STOP" in page.text
    # Degraded-core notice is rendered when no core is provisioned.
    assert SECURE_CORE_NOT_BUILT_MESSAGE in page.text
    assert client.get("/robots/not-the-robot").status_code == 404
    # Status requires a session; the factory app does not bypass auth.
    assert client.get(f"/api/robots/{ROBOT_ID}/status").status_code == 401
    assert client.post(
        f"/api/robots/{ROBOT_ID}/stop",
        json={},
        headers={"Idempotency-Key": "asgi-unauth"},
    ).status_code == 401


def test_asgi_app_logged_in_status_reports_unsigned_degraded_core(factory_db):
    app = asgi_app()
    Store(app.state.db_path).create_user("operator1", "operator-password-123", "operator")
    client = _client(app)
    login = client.post(
        "/auth/login",
        data={"username": "operator1", "password": "operator-password-123"},
        follow_redirects=False,
    )
    assert login.status_code == 303, login.text
    status = client.get(f"/api/robots/{ROBOT_ID}/status")
    assert status.status_code == 200, status.text
    data = status.json()
    assert data["actor"] == "operator1"
    assert data["stop_latched"] is True
    assert data["persistence_ok"] is True
    # Deterministic in both Rust modes given no QUBERON_SECURE_CORE_MODE:
    # core unavailable (unsigned STOP only), never claimed available.
    assert data["secure_core_available"] is False
    assert data["secure_core_message"] == SECURE_CORE_NOT_BUILT_MESSAGE
