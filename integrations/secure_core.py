"""Python client for the Rust secure core (subprocess boundary).

SIMULATION ONLY, STOP AUTHORIZATION ONLY. NO PHYSICAL CONTROL.
NOT A SAFETY-RATED E-STOP.

Every STOP request in the app must obtain an ACCEPTED decision from the
Rust core (via the ``quberon-secure-core-cli`` subprocess) before
``SimulatedRobotAdapter.stop`` may be invoked. Any client, subprocess,
or core error raises :class:`SecureCoreError`; callers must fail closed
(latch retained, observed state UNKNOWN, no adapter invocation).

Key custody: the Ed25519 signing seed is supplied via environment
(``QUBERON_SECURE_CORE_SIGNING_KEY_HEX``) or generated ephemerally for a
local simulation app instance by the CLI itself. It is never stored in
this repository. Signing is performed by the Rust CLI, not by Python.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_CORE_OUTPUT_BYTES = 32_768


class SecureCoreError(Exception):
    """Any failure of the Rust secure-core boundary. Always fail closed."""


def _default_binary() -> Path:
    override = os.environ.get("QUBERON_SECURE_CORE_BIN", "")
    if override:
        return Path(override)
    release = REPO_ROOT / "target" / "release" / "quberon-secure-core-cli"
    debug = REPO_ROOT / "target" / "debug" / "quberon-secure-core-cli"
    return release if release.exists() else debug


class SecureCoreClient:
    def __init__(self, binary, db_path, trusted, signing_key_hex, kid,
                 issuer, robot_id, simulation_id, sequence_path=None,
                 timeout_s: float = 5.0):
        self.binary = Path(binary)
        self.db_path = str(db_path)
        self.trusted = trusted  # list of trusted-issuer dicts for the CLI
        self._signing_key_hex = signing_key_hex
        self.kid = kid
        self.issuer = issuer
        self.robot_id = robot_id
        self.simulation_id = simulation_id
        self.timeout_s = timeout_s
        self._lock = threading.Lock()
        self._seq_path = Path(sequence_path) if sequence_path else Path(str(db_path) + ".seq")
        self._sequence = self._load_sequence()

    # -- subprocess plumbing -------------------------------------------------
    def _run_cli(self, args, payload: dict) -> dict:
        if not self.binary.is_file():
            raise SecureCoreError(f"secure core binary not found: {self.binary}")
        try:
            proc = subprocess.run(
                [str(self.binary), *args],
                input=json.dumps(payload).encode(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=self.timeout_s, check=False,
            )
        except Exception as exc:  # timeout, spawn failure, ...
            raise SecureCoreError(f"secure core subprocess failed: {type(exc).__name__}") from exc
        if len(proc.stdout) > MAX_CORE_OUTPUT_BYTES:
            raise SecureCoreError("secure core output too large")
        try:
            data = json.loads(proc.stdout.decode())
        except Exception as exc:
            raise SecureCoreError("secure core returned malformed output") from exc
        if not isinstance(data, dict):
            raise SecureCoreError("secure core returned non-object output")
        return data

    def _load_sequence(self) -> int:
        try:
            return int(self._seq_path.read_text().strip())
        except Exception:
            return 0

    def _next_sequence(self) -> int:
        self._sequence += 1
        try:
            self._seq_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._seq_path.with_suffix(".tmp")
            tmp.write_text(str(self._sequence))
            tmp.replace(self._seq_path)
        except Exception as exc:
            raise SecureCoreError("sequence persistence failed") from exc
        return self._sequence

    # -- public API -----------------------------------------------------------
    def authorize_stop(self, subject: str, now_unix: int | None = None) -> dict:
        """Sign a STOP envelope (in the Rust CLI) and ask the Rust core to
        authorize it. Returns the core Decision on ACCEPTED; raises
        SecureCoreError on any rejection or boundary failure."""
        now = int(time.time()) if now_unix is None else int(now_unix)
        with self._lock:
            sequence = self._next_sequence()
            envelope = self._run_cli(["sign"], {
                "signing_key_hex": self._signing_key_hex, "kid": self.kid,
                "issuer": self.issuer, "robot_id": self.robot_id,
                "simulation_id": self.simulation_id, "subject": subject,
                "sequence": sequence, "issued_at_unix": now,
                "expires_at_unix": now + 120,
            })
            if "signature" not in envelope:
                raise SecureCoreError(f"signing failed: {envelope.get('code', 'UNKNOWN')}")
            decision = self._run_cli(["authorize"], {
                "db_path": self.db_path, "trusted": self.trusted,
                "envelope": envelope, "now_unix": now,
            })
        if decision.get("outcome") != "ACCEPTED" or \
                decision.get("code") != "ACCEPTED_SIMULATION_STOP_AUTHORIZATION":
            raise SecureCoreError(f"secure core rejected STOP: {decision.get('code', 'UNKNOWN')}")
        if decision.get("robot_id") != self.robot_id or \
                decision.get("simulation_id") != self.simulation_id:
            raise SecureCoreError("secure core decision scope mismatch")
        return decision


def generate_keypair(binary) -> dict:
    client = SecureCoreClient.__new__(SecureCoreClient)
    client.binary = Path(binary)
    client.timeout_s = 5.0
    return client._run_cli(["generate-keypair"], {})


def provision_ephemeral(binary, core_db_path, robot_id, simulation_id="simulation-only-001"):
    """Create a per-instance simulation client: fresh keypair from the Rust
    CLI, seed held only in this process's memory (never written to disk)."""
    keys = generate_keypair(binary)
    if "signing_key_hex" not in keys:
        raise SecureCoreError("key generation failed")
    trusted = [{
        "kid": "simulation-issuer-1", "issuer": "quberon-simulation-issuer",
        "robot_id": robot_id, "simulation_id": simulation_id,
        "verifying_key_hex": keys["verifying_key_hex"],
    }]
    return SecureCoreClient(
        binary=binary, db_path=core_db_path, trusted=trusted,
        signing_key_hex=keys["signing_key_hex"], kid="simulation-issuer-1",
        issuer="quberon-simulation-issuer", robot_id=robot_id,
        simulation_id=simulation_id,
    )


def client_from_env(robot_id, app_db_path=None):
    """Build a client from QUBERON_SECURE_CORE_* env, or provision an
    ephemeral simulation client next to QUBERON_DB_PATH. Returns None only
    if the CLI binary is unavailable (callers must then fail closed)."""
    binary = _default_binary()
    if not binary.is_file():
        return None
    simulation_id = os.environ.get("QUBERON_SECURE_CORE_SIMULATION_ID", "simulation-only-001")
    seed = os.environ.get("QUBERON_SECURE_CORE_SIGNING_KEY_HEX", "")
    db_path = os.environ.get("QUBERON_SECURE_CORE_DB", "")
    if seed and db_path:
        trusted = [{
            "kid": os.environ.get("QUBERON_SECURE_CORE_KID", "simulation-issuer-1"),
            "issuer": os.environ.get("QUBERON_SECURE_CORE_ISSUER", "quberon-simulation-issuer"),
            "robot_id": robot_id, "simulation_id": simulation_id,
            "verifying_key_hex": os.environ.get("QUBERON_SECURE_CORE_VERIFYING_KEY_HEX", ""),
        }]
        return SecureCoreClient(
            binary=binary, db_path=db_path, trusted=trusted, signing_key_hex=seed,
            kid=trusted[0]["kid"], issuer=trusted[0]["issuer"],
            robot_id=robot_id, simulation_id=simulation_id,
        )
    app_db = app_db_path or os.environ.get("QUBERON_DB_PATH", "/tmp/quberon-robot-interface.db")
    core_db = str(Path(app_db).with_name(Path(app_db).stem + "-secure-core.db"))
    try:
        return provision_ephemeral(binary, core_db, robot_id, simulation_id)
    except SecureCoreError:
        return None
