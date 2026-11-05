import os, sqlite3, stat, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from fastapi.testclient import TestClient

from adapters.robot_sim import SimulatedRobotAdapter
from app.main import create_app, Store
from integrations.secure_core import (PriorityRateLimiter, SecureCoreError,
                                      SecureCoreRejected, SecureCoreClient,
                                      client_from_env, generate_keypair,
                                      load_key_file, provision_ephemeral)

ROBOT = "quberon-demo-001"
BIN = os.path.join(os.path.dirname(__file__), "..", "target", "debug", "quberon-secure-core-cli")

needs_rust = pytest.mark.skipif(not os.path.isfile(BIN), reason="Rust CLI not built: cargo build --workspace")


@pytest.fixture(autouse=True)
def _dev_mode(monkeypatch):
    monkeypatch.setenv("QUBERON_SECURE_CORE_MODE", "development")


def make(tmp_path, **kw):
    db = str(tmp_path / "test.db")
    app = create_app(db_path=db, **kw)
    s = Store(db)
    s.create_user("operator1", "operator-password-123", "operator")
    s.create_user("admin1", "admin-password-123", "admin")
    return TestClient(app, base_url="https://testserver"), app


def login(c, user="operator1", pw="operator-password-123"):
    assert c.post("/auth/login", data={"username": user, "password": pw}, follow_redirects=False).status_code == 303
    return c.get(f"/api/robots/{ROBOT}/status").json()["csrf_token"]


@needs_rust
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


@needs_rust
def test_app_stop_with_secure_core_accepted(tmp_path, monkeypatch):
    calls = []
    orig = SimulatedRobotAdapter.stop
    def counting(self):
        calls.append(1)
        return orig(self)
    monkeypatch.setattr(SimulatedRobotAdapter, "stop", counting)
    c, app = make(tmp_path)
    csrf = login(c)
    r = c.post(f"/api/robots/{ROBOT}/stop", json={"note": "a"}, headers={"X-CSRF-Token": csrf, "Idempotency-Key": "k1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["secure_core"]["status"] == "accepted"
    assert body["secure_core"]["decision"] == "ACCEPTED_SIMULATION_STOP_AUTHORIZATION"
    assert body["secure_core"]["sequence"] is not None
    assert "audit_record" in body["secure_core"]
    assert len(calls) == 1


def test_stop_executes_without_secure_core_but_reset_does_not(tmp_path, monkeypatch):
    stop_calls, reset_calls = [], []
    orig_stop, orig_reset = SimulatedRobotAdapter.stop, SimulatedRobotAdapter.reset_simulation
    def counting_stop(self):
        stop_calls.append(1)
        return orig_stop(self)
    def counting_reset(self):
        reset_calls.append(1)
        return orig_reset(self)
    monkeypatch.setattr(SimulatedRobotAdapter, "stop", counting_stop)
    monkeypatch.setattr(SimulatedRobotAdapter, "reset_simulation", counting_reset)

    c, app = make(tmp_path, secure_core=None)
    csrf = login(c)
    r = c.post(f"/api/robots/{ROBOT}/stop", json={"note": "a"}, headers={"X-CSRF-Token": csrf, "Idempotency-Key": "k-no-core"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["command_state"] == "ACKNOWLEDGED"
    assert body["stop_latched"] is True
    assert body["secure_core"] == {"status": "unavailable", "decision": None, "sequence": None, "audit_record": None, "scope": "SIMULATION_ONLY_STOP_AUTHORIZATION"}
    assert len(stop_calls) == 1, "authenticated STOP must execute without the optional Rust attestation"

    # Application audit must mark the stop UNSIGNED / core_unavailable.
    db_path = str(tmp_path / "test.db")
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT auth_result, detail FROM events WHERE action='STOP'").fetchall()
    assert rows and rows[0][0] == "UNSIGNED/core_unavailable"
    assert "UNSIGNED" in rows[0][1] and "core_unavailable" in rows[0][1]

    st = c.get(f"/api/robots/{ROBOT}/status").json()
    assert st["stop_latched"] is True

    # Clearing the latch (and any motion-permitting op) stays blocked.
    c2 = TestClient(app, base_url="https://testserver")
    csrf_admin = login(c2, "admin1", "admin-password-123")
    rr = c2.post(f"/api/robots/{ROBOT}/simulation-reset", json={"confirm": "RESET_SIMULATION"}, headers={"X-CSRF-Token": csrf_admin})
    assert rr.status_code == 503, rr.text
    assert len(reset_calls) == 0, "reset adapter must not run without the secure core"
    st2 = c2.get(f"/api/robots/{ROBOT}/status").json()
    assert st2["stop_latched"] is True, "latch must be retained when reset is blocked"
    tr = c2.post(f"/api/robots/{ROBOT}/simulated-task", json={"action": "SIMULATE_INSPECTION"}, headers={"X-CSRF-Token": csrf_admin})
    assert tr.status_code in (409, 503)  # latched (409) / core-gated (503); never motion
    assert c2.get(f"/api/robots/{ROBOT}/status").json()["stop_latched"] is True


def test_stop_rejected_by_secure_core_does_not_invoke_adapter(tmp_path, monkeypatch):
    calls = []
    orig = SimulatedRobotAdapter.stop
    def counting(self):
        calls.append(1)
        return orig(self)
    monkeypatch.setattr(SimulatedRobotAdapter, "stop", counting)

    class RejectingCore:
        binary = BIN  # present-or-not is irrelevant: a decision was reached
        def authorize_stop(self, subject, now_unix=None):
            raise SecureCoreRejected(
                "secure core rejected STOP: REPLAY_REJECTED",
                decision={"code": "REPLAY_REJECTED", "sequence": 7, "audit_record": "deadbeef"},
            )

    c, app = make(tmp_path, secure_core=RejectingCore())
    csrf = login(c)
    r = c.post(f"/api/robots/{ROBOT}/stop", json={}, headers={"X-CSRF-Token": csrf, "Idempotency-Key": "k-rejected"})
    assert r.status_code == 503, r.text
    body = r.json()
    assert body["secure_core"]["status"] == "rejected"
    assert body["secure_core"]["decision"] == "REPLAY_REJECTED"
    assert body["secure_core"]["sequence"] == 7
    assert body["secure_core"]["audit_record"] == "deadbeef"
    assert len(calls) == 0, "adapter must not be invoked when a reachable core rejects STOP"
    st = c.get(f"/api/robots/{ROBOT}/status").json()
    assert st["stop_latched"] is True and st["observed_state"] == "UNKNOWN"


@needs_rust
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


def _counting_adapter(monkeypatch):
    calls = []
    orig = SimulatedRobotAdapter.stop
    monkeypatch.setattr(SimulatedRobotAdapter, "stop",
                        lambda self: (calls.append(1), orig(self))[1])
    return calls


@needs_rust
def test_sqlite_failure_never_invokes_adapter(tmp_path, monkeypatch):
    """Deterministic fault injection at the app boundary: the Rust core DB
    lives in a nonexistent directory, so every authorize fails closed."""
    calls = _counting_adapter(monkeypatch)
    bad = SecureCoreClient(
        binary=BIN, db_path=str(tmp_path / "missing-dir" / "core.db"), trusted=[{
            "kid": "k1", "issuer": "quberon-simulation-issuer", "robot_id": ROBOT,
            "simulation_id": "simulation-only-001",
            "verifying_key_hex": generate_keypair(BIN)["verifying_key_hex"]}],
        signing_key_hex=generate_keypair(BIN)["signing_key_hex"], kid="k1",
        issuer="quberon-simulation-issuer", robot_id=ROBOT,
        simulation_id="simulation-only-001")
    c, app = make(tmp_path, secure_core=bad)
    csrf = login(c)
    r = c.post(f"/api/robots/{ROBOT}/stop", json={}, headers={"X-CSRF-Token": csrf, "Idempotency-Key": "fault1"})
    assert r.status_code == 503 and calls == []
    st = c.get(f"/api/robots/{ROBOT}/status").json()
    assert st["stop_latched"] is True and st["observed_state"] == "UNKNOWN"


def test_subprocess_timeout_fails_closed(tmp_path):
    fake = tmp_path / "slow-cli"
    fake.write_text("#!/bin/sh\nsleep 5\n")
    fake.chmod(0o755)
    client = SecureCoreClient(binary=str(fake), db_path=str(tmp_path / "c.db"), trusted=[],
                              signing_key_hex="00" * 32, kid="k", issuer="i",
                              robot_id=ROBOT, simulation_id="s", timeout_s=0.2)
    with pytest.raises(SecureCoreError):
        client.authorize_stop("operator1", now_unix=1_800_000_000)


def test_rate_limiter_stop_isolated_from_other_traffic():
    now = [1000.0]
    lim = PriorityRateLimiter(stop_rate_per_min=60, stop_burst=4, clock=lambda: now[0])
    # Exhaust the non-critical bucket (burst = 1 token at fraction 0.25).
    assert lim.try_acquire("OTHER") is True
    assert lim.try_acquire("OTHER") is False
    # STOP still has its own full bucket: filling OTHER cannot block STOP.
    for _ in range(4):
        assert lim.try_acquire("STOP") is True
    assert lim.try_acquire("STOP") is False  # STOP's own bound still applies
    now[0] += 2.0  # refill at 1 token/s
    assert lim.try_acquire("STOP") is True


@needs_rust
def test_bounded_subject_rejected(tmp_path):
    client = provision_ephemeral(BIN, str(tmp_path / "core.db"), ROBOT)
    with pytest.raises(SecureCoreError):
        client.authorize_stop("x" * 129)
    with pytest.raises(SecureCoreError):
        client.authorize_stop("bad subject with spaces")


@needs_rust
def test_epoch_advances_across_clients_sequence_preserved(tmp_path):
    db = str(tmp_path / "core.db")
    c1 = provision_ephemeral(BIN, db, ROBOT)
    d1 = c1.authorize_stop("operator1", now_unix=1_800_000_000)
    c2 = provision_ephemeral(BIN, db, ROBOT)
    assert c2.epoch > c1.epoch
    # Same signing key is NOT shared (new ephemeral keypair) so c2 cannot
    # authorize against c1's trust entry; use c1's keys via a fresh client
    # sharing the same seq/epoch files to prove sequence continuity.
    shared = SecureCoreClient(
        binary=BIN, db_path=db, trusted=c1.trusted, signing_key_hex=c1._signing_key_hex,
        kid=c1.kid, issuer=c1.issuer, robot_id=ROBOT, simulation_id=c1.simulation_id)
    assert shared.epoch > c1.epoch
    d2 = shared.authorize_stop("operator1", now_unix=1_800_000_000)
    assert d2["sequence"] == d1["sequence"] + 1


def test_production_mode_fails_closed_without_external_key(tmp_path, monkeypatch):
    for var in ("QUBERON_SECURE_CORE_SIGNING_KEY_HEX", "QUBERON_SECURE_CORE_SIGNING_KEY_FILE",
                "QUBERON_SECURE_CORE_VERIFYING_KEY_HEX", "QUBERON_SECURE_CORE_DB"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("QUBERON_SECURE_CORE_MODE", "production")
    assert client_from_env(ROBOT, app_db_path=str(tmp_path / "app.db")) is None
    monkeypatch.delenv("QUBERON_SECURE_CORE_MODE")
    assert client_from_env(ROBOT, app_db_path=str(tmp_path / "app.db")) is None


@needs_rust
def test_key_file_permissions_enforced(tmp_path):
    keys = generate_keypair(BIN)
    kf = tmp_path / "signing.hex"
    kf.write_text(keys["signing_key_hex"])
    kf.chmod(0o644)
    with pytest.raises(SecureCoreError):
        load_key_file(kf)
    kf.chmod(0o600)
    assert load_key_file(kf) == keys["signing_key_hex"]


@needs_rust
def test_production_mode_with_key_file_accepts(tmp_path, monkeypatch):
    keys = generate_keypair(BIN)
    kf = tmp_path / "signing.hex"
    kf.write_text(keys["signing_key_hex"])
    kf.chmod(0o600)
    core_db = str(tmp_path / "core.db")
    monkeypatch.setenv("QUBERON_SECURE_CORE_MODE", "production")
    monkeypatch.setenv("QUBERON_SECURE_CORE_SIGNING_KEY_FILE", str(kf))
    monkeypatch.setenv("QUBERON_SECURE_CORE_VERIFYING_KEY_HEX", keys["verifying_key_hex"])
    monkeypatch.setenv("QUBERON_SECURE_CORE_DB", core_db)
    monkeypatch.setenv("QUBERON_SECURE_CORE_ANCHOR", core_db + ".anchor.json")
    client = client_from_env(ROBOT, app_db_path=str(tmp_path / "app.db"))
    assert client is not None
    d = client.authorize_stop("operator1", now_unix=1_800_000_000)
    assert d["code"] == "ACCEPTED_SIMULATION_STOP_AUTHORIZATION"
    assert stat.S_IMODE(os.stat(core_db + ".anchor.json").st_mode) & 0o077 == 0
