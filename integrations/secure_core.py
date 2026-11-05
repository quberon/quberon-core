"""Python client for the Rust secure core (subprocess boundary).

SIMULATION ONLY, STOP AUTHORIZATION ONLY. NO PHYSICAL CONTROL.
NOT A SAFETY-RATED E-STOP.

Every STOP request in the app must obtain an ACCEPTED decision from the
Rust core (via the ``quberon-secure-core-cli`` subprocess) before
``SimulatedRobotAdapter.stop`` may be invoked. Any client, subprocess,
or core error raises :class:`SecureCoreError`; callers must fail closed
(latch retained, observed state UNKNOWN, no adapter invocation).

Key custody (Increment 2):
- Production mode (``QUBERON_SECURE_CORE_MODE=production``) FAILS CLOSED
  unless an external signing key is supplied via
  ``QUBERON_SECURE_CORE_SIGNING_KEY_FILE`` (a file with strict 0600
  permissions, never committed) or ``QUBERON_SECURE_CORE_SIGNING_KEY_HEX``
  (injected by an external secrets manager), plus a verifying key and an
  explicit core DB path. An audit anchor path should also be configured.
- Ephemeral keys exist ONLY in explicit development mode
  (``QUBERON_SECURE_CORE_MODE=development``). There is no permissive
  default: with no mode set, no client is provisioned and STOP fails
  closed.
Signing is performed by the Rust CLI, not by Python.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_CORE_OUTPUT_BYTES = 32_768
MAX_SUBJECT_CHARS = 128


class SecureCoreError(Exception):
    """Any failure of the Rust secure-core boundary. Always fail closed."""


def _default_binary() -> Path:
    override = os.environ.get("QUBERON_SECURE_CORE_BIN", "")
    if override:
        return Path(override)
    release = REPO_ROOT / "target" / "release" / "quberon-secure-core-cli"
    debug = REPO_ROOT / "target" / "debug" / "quberon-secure-core-cli"
    return release if release.exists() else debug


class PriorityRateLimiter:
    """Token-bucket limiter where STOP is isolated from non-critical work.

    Two independent buckets: filling the non-critical bucket can never
    consume STOP tokens, so an attacker flooding non-critical requests
    cannot block STOP merely by exhausting a shared queue. STOP itself is
    still bounded (its own bucket) as a DoS control. The clock is
    injectable for deterministic tests.
    """

    def __init__(self, stop_rate_per_min: float = 120.0, stop_burst: float = 30.0,
                 other_fraction: float = 0.25, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets = {
            "STOP": [float(stop_burst), float(stop_burst), float(stop_rate_per_min) / 60.0, clock()],
            "OTHER": [float(stop_burst) * other_fraction, float(stop_burst) * other_fraction,
                      float(stop_rate_per_min) * other_fraction / 60.0, clock()],
        }

    def try_acquire(self, priority: str = "STOP") -> bool:
        bucket = self._buckets.get(priority, self._buckets["OTHER"])
        with self._lock:
            now = self._clock()
            tokens, capacity, rate, last = bucket
            tokens = min(capacity, tokens + max(0.0, now - last) * rate)
            bucket[0], bucket[3] = tokens, now
            if tokens < 1.0:
                return False
            bucket[0] = tokens - 1.0
            return True


def load_key_file(path) -> str:
    """Load a hex key from a file with strict permissions. Never log it."""
    p = Path(path)
    try:
        mode = stat.S_IMODE(p.stat().st_mode)
    except OSError as exc:
        raise SecureCoreError("signing key file unavailable") from exc
    if mode & 0o077:
        raise SecureCoreError(
            f"signing key file permissions too permissive: {oct(mode)} (require 0600)")
    try:
        raw = p.read_text().strip()
    except OSError as exc:
        raise SecureCoreError("signing key file unreadable") from exc
    if len(raw) != 64 or any(c not in "0123456789abcdefABCDEF" for c in raw):
        raise SecureCoreError("signing key file malformed (expected 64 hex chars)")
    return raw.lower()


def _atomic_write_int(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(str(value))
    tmp.replace(path)


def _read_int(path: Path) -> int:
    try:
        return int(Path(path).read_text().strip())
    except Exception:
        return 0


class SecureCoreClient:
    def __init__(self, binary, db_path, trusted, signing_key_hex, kid,
                 issuer, robot_id, simulation_id, sequence_path=None,
                 timeout_s: float = 5.0, anchor_path=None, epoch=None,
                 epoch_path=None, max_audit_records: int = 0, rate_limiter=None):
        self.binary = Path(binary)
        self.db_path = str(db_path)
        self.trusted = trusted  # list of trusted-issuer dicts for the CLI
        self._signing_key_hex = signing_key_hex
        self.kid = kid
        self.issuer = issuer
        self.robot_id = robot_id
        self.simulation_id = simulation_id
        self.timeout_s = timeout_s
        self.anchor_path = str(anchor_path) if anchor_path else None
        self.max_audit_records = int(max_audit_records or 0)
        self.rate_limiter = rate_limiter or PriorityRateLimiter()
        self._lock = threading.Lock()
        self._seq_path = Path(sequence_path) if sequence_path else Path(str(db_path) + ".seq")
        self._sequence = _read_int(self._seq_path)
        # Monotonic boot/session epoch: each new client process-instance
        # advances the persisted epoch. The persisted sequence is NOT reset.
        self._epoch_path = Path(epoch_path) if epoch_path else Path(str(db_path) + ".epoch")
        if epoch is not None:
            self.epoch = int(epoch)
            if self.epoch < 1:
                raise SecureCoreError("epoch must be >= 1")
        else:
            self.epoch = _read_int(self._epoch_path) + 1
            try:
                _atomic_write_int(self._epoch_path, self.epoch)
            except Exception as exc:
                raise SecureCoreError("epoch persistence failed") from exc

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

    def _next_sequence(self) -> int:
        self._sequence += 1
        try:
            _atomic_write_int(self._seq_path, self._sequence)
        except Exception as exc:
            raise SecureCoreError("sequence persistence failed") from exc
        return self._sequence

    # -- public API -----------------------------------------------------------
    def authorize_stop(self, subject: str, now_unix: int | None = None) -> dict:
        """Sign a STOP envelope (in the Rust CLI) and ask the Rust core to
        authorize it. Returns the core Decision on ACCEPTED; raises
        SecureCoreError on any rejection or boundary failure."""
        if not isinstance(subject, str) or not (1 <= len(subject) <= MAX_SUBJECT_CHARS) \
                or any(ord(c) < 0x21 or ord(c) > 0x7E for c in subject):
            raise SecureCoreError("subject field rejected")
        if not self.rate_limiter.try_acquire("STOP"):
            raise SecureCoreError("secure core STOP rate limit exceeded")
        now = int(time.time()) if now_unix is None else int(now_unix)
        with self._lock:
            sequence = self._next_sequence()
            envelope = self._run_cli(["sign"], {
                "signing_key_hex": self._signing_key_hex, "kid": self.kid,
                "issuer": self.issuer, "robot_id": self.robot_id,
                "simulation_id": self.simulation_id, "subject": subject,
                "epoch": self.epoch,
                "sequence": sequence, "issued_at_unix": now,
                "expires_at_unix": now + 120,
            })
            if "signature" not in envelope:
                raise SecureCoreError(f"signing failed: {envelope.get('code', 'UNKNOWN')}")
            authorize_req = {
                "db_path": self.db_path, "trusted": self.trusted,
                "envelope": envelope, "now_unix": now, "boot_epoch": self.epoch,
                "max_audit_records": self.max_audit_records,
            }
            if self.anchor_path:
                authorize_req["anchor_path"] = self.anchor_path
            decision = self._run_cli(["authorize"], authorize_req)
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


def provision_ephemeral(binary, core_db_path, robot_id, simulation_id="simulation-only-001",
                        **kw):
    """DEVELOPMENT ONLY: fresh keypair from the Rust CLI, seed held only in
    this process's memory (never written to disk). Callers must explicitly
    opt into development mode; there is no permissive default."""
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
        simulation_id=simulation_id, **kw,
    )


def client_from_env(robot_id, app_db_path=None):
    """Build a client from QUBERON_SECURE_CORE_* env.

    - production: external key (file 0600 or secrets-manager hex) + verifying
      key + DB path required; anything missing -> None (fail closed).
    - development: explicit opt-in; ephemeral keys allowed, or an env key
      if one is supplied.
    - unset/unknown mode: None (fail closed). No permissive default.
    """
    binary = _default_binary()
    if not binary.is_file():
        return None
    mode = os.environ.get("QUBERON_SECURE_CORE_MODE", "").strip().lower()
    if mode not in {"production", "development"}:
        return None
    simulation_id = os.environ.get("QUBERON_SECURE_CORE_SIMULATION_ID", "simulation-only-001")
    db_path = os.environ.get("QUBERON_SECURE_CORE_DB", "")
    anchor_path = os.environ.get("QUBERON_SECURE_CORE_ANCHOR", "") or None
    max_audit = os.environ.get("QUBERON_SECURE_CORE_MAX_AUDIT_RECORDS", "")
    try:
        max_audit_records = int(max_audit) if max_audit else 100_000
    except ValueError:
        return None
    try:
        seed = ""
        key_file = os.environ.get("QUBERON_SECURE_CORE_SIGNING_KEY_FILE", "")
        if key_file:
            seed = load_key_file(key_file)
        else:
            seed = os.environ.get("QUBERON_SECURE_CORE_SIGNING_KEY_HEX", "")
        verifying = os.environ.get("QUBERON_SECURE_CORE_VERIFYING_KEY_HEX", "")
        vk_file = os.environ.get("QUBERON_SECURE_CORE_VERIFYING_KEY_FILE", "")
        if vk_file:
            verifying = load_key_file(vk_file)
        if seed and db_path:
            if not verifying:
                return None  # production and dev-with-key both need trust root
            trusted = [{
                "kid": os.environ.get("QUBERON_SECURE_CORE_KID", "simulation-issuer-1"),
                "issuer": os.environ.get("QUBERON_SECURE_CORE_ISSUER", "quberon-simulation-issuer"),
                "robot_id": robot_id, "simulation_id": simulation_id,
                "verifying_key_hex": verifying,
            }]
            return SecureCoreClient(
                binary=binary, db_path=db_path, trusted=trusted, signing_key_hex=seed,
                kid=trusted[0]["kid"], issuer=trusted[0]["issuer"],
                robot_id=robot_id, simulation_id=simulation_id,
                anchor_path=anchor_path, max_audit_records=max_audit_records,
            )
        if mode == "production":
            return None  # fail closed: no external signing key configured
        app_db = app_db_path or os.environ.get("QUBERON_DB_PATH", "/tmp/quberon-robot-interface.db")
        core_db = str(Path(app_db).with_name(Path(app_db).stem + "-secure-core.db"))
        return provision_ephemeral(
            binary, core_db, robot_id, simulation_id,
            anchor_path=anchor_path or (core_db + ".anchor.json"),
            max_audit_records=max_audit_records)
    except SecureCoreError:
        return None
