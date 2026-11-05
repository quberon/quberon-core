import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from fastapi.testclient import TestClient

from adapters.robot_sim import SimulatedRobotAdapter
from app.main import create_app, Store
from integrations.secure_core import SecureCoreError, SecureCoreClient, generate_keypair, provision_ephemeral

ROBOT = "quberon-demo-001"
BIN = os.path.join(os.path.dirname(__file__), "..", "target", "debug", "quberon-secure-core-cli")

pytestmark = pytest.mark.skipif(not os.path.isfile(BIN), reason="Rust CLI not built: cargo build --workspace")


def make(tmp_path, **kw):
    db = str(tmp_path / "test.db")
    app = create_app(db_path=db, **kw)
    s = Store(db)
    s.create_user("operator1", "operator-password-123", "operator")
    return TestClient(app, base_url="https://testserver"), app


def login(c):
    assert c.post("/auth/login", data={"username": "operator1", "password": "operator-password-123"}, follow_redirects=False).status_code == 303
    return c.get(f"/api/robots/{ROBOT}/status").json()["csrf_token"]


def test_client_accepts_stop_and_rejected_client_fails_closed(tmp_path):
    client = provision_ephemeral(BIN, str(tmp_path / "core.db"), ROBOT)
    d = client.authorize_stop("operator1", now_unix=1_800_000_000)
    assert d["code"] == "ACCEPTED_SIMULATION_STOP_AUTHORIZATION"
    assert d["observed_state"] == "UNKNOWN" and d["physical_state_claim"] == "NONE"
    bad = SecureCoreClient(binary="/nonexistent/quberon-core", db_path=str(tmp_path / "c.db"),
                           trusted=[], signing_key_hex="00" * 32, kid="k", issuer="i",
                           robot_id=ROBOT, simulation_id="simulation-only-001")
    with pytest.raises(SecureCoreError):
        bad.authorize_stop("operator1")


def test_app_stop_requires_rust_and_core_error_never_invokes_adapter(tmp_path, monkeypatch):
    calls = []
    orig = SimulatedRobotAdapter.stop
    def counting(self):
        calls.append(1)
        return orig(self)
    monkeypatch.setattr(SimulatedRobotAdapter, "stop", counting)
    c, app = make(tmp_path)
    csrf = login(c)
    r = c.post(f"/api/robots/{ROBOT}/stop", json={"note": "a"}, headers={"X-CSRF-Token": csrf, "Idempotency-Key": "k1"})
    assert r.status_code == 200 and r.json()["secure_core"]["decision"] == "ACCEPTED_SIMULATION_STOP_AUTHORIZATION"
    assert len(calls) == 1

    c2, app2 = make(tmp_path / "second", secure_core=None)
    csrf2 = login(c2)
    r = c2.post(f"/api/robots/{ROBOT}/stop", json={}, headers={"X-CSRF-Token": csrf2, "Idempotency-Key": "k2"})
    assert r.status_code == 503
    st = c2.get(f"/api/robots/{ROBOT}/status").json()
    assert st["stop_latched"] is True and st["observed_state"] == "UNKNOWN"
    assert len(calls) == 1, "adapter must not be invoked when the Rust core does not accept"


def test_scope_mismatch_client_rejected(tmp_path):
    keys = generate_keypair(BIN)
    trusted = [{"kid": "k1", "issuer": "quberon-simulation-issuer", "robot_id": ROBOT,
                "simulation_id": "other-simulation", "verifying_key_hex": keys["verifying_key_hex"]}]
    mismatched = SecureCoreClient(binary=BIN, db_path=str(tmp_path / "core.db"), trusted=trusted,
                                  signing_key_hex=keys["signing_key_hex"], kid="k1",
                                  issuer="quberon-simulation-issuer", robot_id=ROBOT,
                                  simulation_id="simulation-only-001")
    with pytest.raises(SecureCoreError):
        mismatched.authorize_stop("operator1")
