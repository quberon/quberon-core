"""quberon-core adapter: maps the neutral interface onto app.main's HTTP API.

This is the reference mapping for ONE implementation (the in-repo simulator).
It is not part of the neutral interface: another vendor/system writes its own
module like this one and runs the same test_conformance.py unchanged.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from app.main import ROBOT_ID, Store, create_app
from conformance.adapter_interface import AdapterUnderTest, NeutralResult
from integrations.secure_core import SecureCoreRejected


class _RefusingSecureCore:
    """Reachable-but-refusing authority stub (conformance injection only).

    This is NOT the Rust secure core and makes no signed-attestation claim.
    It drives the app's already-existing reachable-refusal branch (which
    raises/handles SecureCoreRejected) so the neutral suite can observe
    refusal-vs-unavailability semantics. A real Rust-core rejection is
    listed as NOT TESTED in README.md.
    """

    binary = None  # present/reachable at the app boundary, unlike no-core

    def authorize_stop(self, subject=None, **_kw):
        raise SecureCoreRejected(
            "conformance-injected secure-core refusal",
            decision={"code": "REFUSED_CONFORMANCE_INJECTION",
                      "sequence": None, "audit_record": None},
        )

USERS = {
    "viewer": ("viewer1", "viewer-password-123", "viewer"),
    "operator": ("operator1", "operator-password-123", "operator"),
    "admin": ("admin1", "admin-password-123", "admin"),
}


class QuberonCoreAdapter(AdapterUnderTest):
    def __init__(self, tmp_path, **create_kwargs):
        self.robot_id = ROBOT_ID
        db = str(tmp_path / "conformance.db")
        app = create_app(db_path=db, **create_kwargs)
        store = Store(db)
        for username, password, role in USERS.values():
            store.create_user(username, password, role)
        self._app = app
        self._clients = {}
        self._csrf = {}
        for role, (username, password, _r) in USERS.items():
            client = TestClient(app, base_url="https://testserver")
            resp = client.post("/auth/login", data={"username": username, "password": password},
                               follow_redirects=False)
            assert resp.status_code == 303, resp.text
            self._clients[role] = client
            self._csrf[role] = client.get(f"/api/robots/{ROBOT_ID}/status").json()["csrf_token"]
        self._anon = TestClient(app, base_url="https://testserver")

    # -- helpers ---------------------------------------------------------
    def _client(self, role):
        return self._anon if role == "anonymous" else self._clients[role]

    def _headers(self, role, csrf=True, extra=None):
        headers = {}
        if csrf and role != "anonymous":
            headers["X-CSRF-Token"] = self._csrf[role]
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _wrap(resp) -> NeutralResult:
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}
        if isinstance(body, list):
            body = {"events": body}
        elif not isinstance(body, dict):
            body = {"value": body}
        return NeutralResult(status_code=resp.status_code, body=body)

    def capabilities(self):
        status = self.status("operator").body
        return {
            "secure_core_available": bool(status.get("secure_core_available")),
            "adapter_mode_simulation": status.get("adapter_mode") == "SIMULATION",
            "persistence_failure_injectable": True,
            "secure_core_refusal_injectable": True,
            "manufacturer_mapping_declared": True,
        }

    # -- manufacturer-mapping declaration (QIP-R10.2) ---------------------
    def manufacturer_mapping_declaration(self):
        # quberon-core is a simulator (status adapter_mode == "SIMULATION").
        # No manufacturer stop/status/reset interface has been observed in
        # manufacturer-provided material recorded with its source for this
        # implementation, so R10.2 requires an explicit non-claim here --
        # not silence, and not an approximated/simulated mapping.
        return {
            "mapping_claimed": False,
            "mappings": [],
            "basis": "simulation_only: no manufacturer interface observed "
                     "or claimed for this implementation",
        }

    # -- neutral fault injection (QIP-DEG-03, conformance only) ----------
    def inject_persistence_failure(self) -> None:
        # Set the same degraded flag the app's own SQLite-error handler
        # and Store init-failure path set (app.main: persistence_ok=False,
        # latch retained, observed UNKNOWN). This does not simulate a real
        # disk/SQLite failure; that remains NOT TESTED (README.md).
        store = self._app.state.store
        store.persistence_ok = False
        store.stop_latched = True
        store.observed_state = "UNKNOWN"

    def inject_secure_core_refusal(self) -> None:
        self._app.state.secure_core = _RefusingSecureCore()

    # -- neutral surface ---------------------------------------------------
    def status(self, role):
        return self.status_for_robot(role, self.robot_id)

    def status_for_robot(self, role, robot_id):
        return self._wrap(self._client(role).get(f"/api/robots/{robot_id}/status"))

    def stop(self, role, idempotency_key, note="conformance stop", csrf=True):
        resp = self._client(role).post(
            f"/api/robots/{self.robot_id}/stop", json={"note": note},
            headers=self._headers(role, csrf=csrf, extra={"Idempotency-Key": idempotency_key}))
        return self._wrap(resp)

    def stop_for_robot(self, role, robot_id, idempotency_key):
        resp = self._client(role).post(
            f"/api/robots/{robot_id}/stop", json={},
            headers=self._headers(role, extra={"Idempotency-Key": idempotency_key}))
        return self._wrap(resp)

    def reset_latch(self, role, confirm="RESET_SIMULATION"):
        resp = self._client(role).post(
            f"/api/robots/{self.robot_id}/simulation-reset", json={"confirm": confirm},
            headers=self._headers(role))
        return self._wrap(resp)

    def submit_task(self, role, action):
        resp = self._client(role).post(
            f"/api/robots/{self.robot_id}/simulated-task", json={"action": action},
            headers=self._headers(role))
        return self._wrap(resp)

    def submit_proposal(self, role, text):
        resp = self._client(role).post(
            f"/api/robots/{self.robot_id}/plan", json={"text": text},
            headers=self._headers(role))
        return self._wrap(resp)

    def intervene(self, role, kind, event_id, evidence_text="", timestamp=""):
        body = {"kind": kind, "source_status": "SYNTHETIC", "event_id": event_id,
                "evidence_text": evidence_text}
        if timestamp:
            body["timestamp"] = timestamp
        resp = self._client(role).post(
            f"/api/robots/{self.robot_id}/interventions", json=body,
            headers=self._headers(role))
        return self._wrap(resp)

    def events(self, role):
        return self._wrap(self._client(role).get(f"/api/robots/{self.robot_id}/events"))


def make_quberon_adapter(tmp_path, **kwargs):
    return QuberonCoreAdapter(tmp_path, **kwargs)
