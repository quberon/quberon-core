import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from adapters.robot_sim import SimulatedRobotAdapter
from integrations.meta import MockMetaProvider, UnavailableMetaProvider, get_provider, validate_plan, sanitize_proposal
from integrations.interventions import InterventionEvent, InterventionKind, SourceStatus, STOP_KINDS
from integrations.secure_core import SecureCoreError, SecureCoreRejected, SecureCoreUnavailable, client_from_env
from integrations.recognizers import (
    GestureFrame,
    HandLandmark,
    OpenPalmStopRecognizer,
    VoiceObservation,
    VoiceStopRecognizer,
)

ROBOT_ID = os.environ.get("ROBOT_ID", "quberon-demo-001")
ROLES = {"viewer": {"read"}, "operator": {"read", "stop", "task", "plan"}, "admin": {"read", "stop", "task", "plan", "admin"}}
ALLOWED_HOSTS = {h.strip().lower() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,10.77.0.2,10.99.0.1,quberon-pi.local,testserver").split(",") if h.strip()}
INSECURE_HTTP = os.environ.get("DEMO_INSECURE_HTTP", "false").lower() == "true"
SESSION_COOKIE = "quberon_session"
SECURE_CORE_NOT_BUILT_MESSAGE = "secure core not built: STOP available with unsigned attestation; simulated task and latch reset are disabled. Run make core to enable them."
DEFAULT_STATE_DIR = Path.home() / ".local" / "share" / "quberon-robot-interface"
DEFAULT_DB_PATH = DEFAULT_STATE_DIR / "quberon.db"


def _private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Never tighten a shared/system ancestor: a DB placed directly in
    # /, the system temp dir, or $HOME must not chmod that shared dir.
    resolved = path.resolve()
    shared = {Path(resolved.anchor), Path.home().resolve()}
    try:
        import tempfile

        shared.add(Path(tempfile.gettempdir()).resolve())
    except Exception:
        pass
    if resolved not in shared:
        path.chmod(0o700)


def _private_file(path: Path) -> None:
    if path.exists():
        path.chmod(0o600)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: Optional[datetime] = None) -> str:
    return (dt or utcnow()).isoformat()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return "pbkdf2_sha256$260000$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt_b64, dk_b64 = stored.split("$", 3)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(rounds))
        return hmac.compare_digest(base64.b64encode(dk).decode(), dk_b64)
    except Exception:
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Store:
    def __init__(self, db_path: str):
        self.db_path = str(Path(db_path).expanduser().resolve())
        self.lock = threading.RLock()
        self.persistence_ok = True
        _private_dir(Path(self.db_path).parent)
        try:
            self._init_db()
            with self._db() as db:
                row = db.execute("SELECT stop_latched, observed_state FROM state WHERE robot_id=?", (ROBOT_ID,)).fetchone()
                if row is None:
                    db.execute("INSERT INTO state VALUES (?,?,?,?)", (ROBOT_ID, 1, "SIMULATED_STOPPED", iso()))
                    self.stop_latched = True
                    self.observed_state = "SIMULATED_STOPPED"
                else:
                    self.stop_latched = bool(row[0])
                    self.observed_state = row[1]
        except Exception:
            # Fail closed: no durable state means tasks stay inhibited.
            self.persistence_ok = False
            self.stop_latched = True
            self.observed_state = "UNKNOWN"
        self._harden_state_files()

    def _harden_state_files(self):
        for suffix in ("", "-wal", "-shm"):
            _private_file(Path(self.db_path + suffix))

    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        self._harden_state_files()
        return db

    def _init_db(self):
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, role TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, csrf TEXT NOT NULL, expires TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS state(robot_id TEXT PRIMARY KEY, stop_latched INTEGER NOT NULL, observed_state TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(
                  id TEXT PRIMARY KEY, ts TEXT NOT NULL, actor TEXT NOT NULL, robot_id TEXT NOT NULL,
                  action TEXT NOT NULL, auth_result TEXT NOT NULL, idempotency_key TEXT,
                  payload_hash TEXT, command_state TEXT, observed_state TEXT, detail TEXT,
                  UNIQUE(actor, robot_id, idempotency_key));
                CREATE TABLE IF NOT EXISTS login_attempts(username TEXT, ts REAL, success INTEGER);
                """
            )

    def create_user(self, username: str, password: str, role: str):
        if role not in ROLES:
            raise ValueError("invalid role")
        with self._db() as db:
            db.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (username, hash_password(password), role))

    def get_user(self, username: str):
        with self._db() as db:
            return db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

    def login_allowed(self, username: str) -> bool:
        cutoff = time.time() - 600
        with self._db() as db:
            row = db.execute("SELECT COUNT(*) c FROM login_attempts WHERE username=? AND success=0 AND ts>?", (username, cutoff)).fetchone()
            return int(row["c"]) < 5

    def record_login(self, username: str, success: bool):
        with self._db() as db:
            db.execute("INSERT INTO login_attempts VALUES (?,?,?)", (username, time.time(), int(success)))

    def create_session(self, username: str) -> tuple[str, str]:
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        expires = iso(utcnow() + timedelta(hours=8))
        with self._db() as db:
            db.execute("INSERT INTO sessions VALUES (?,?,?,?)", (token_hash(token), username, csrf, expires))
        return token, csrf

    def get_session(self, token: Optional[str]):
        if not token:
            return None
        with self._db() as db:
            row = db.execute("SELECT s.*, u.role FROM sessions s JOIN users u ON u.username=s.username WHERE s.token_hash=?", (token_hash(token),)).fetchone()
            if not row or row["expires"] <= iso():
                return None
            return row

    def delete_session(self, token: Optional[str]):
        if token:
            with self._db() as db:
                db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))

    def set_state(self, db, latched: bool, observed: str):
        db.execute("UPDATE state SET stop_latched=?, observed_state=?, updated_at=? WHERE robot_id=?", (int(latched), observed, iso(), ROBOT_ID))
        self.stop_latched, self.observed_state = latched, observed

    def status(self) -> Dict[str, Any]:
        return {
            "robot_id": ROBOT_ID,
            "adapter_mode": "SIMULATION",
            "stop_latched": bool(self.stop_latched),
            "observed_state": self.observed_state,
            "persistence_ok": bool(self.persistence_ok),
            "server_time_utc": iso(),
            "safety_notice": "SIMULATED ROBOT - NOT AN EMERGENCY STOP",
        }


class StopBody(BaseModel):
    note: str = Field(default="", max_length=200)


class TaskBody(BaseModel):
    action: str = Field(max_length=64)


class ResetBody(BaseModel):
    confirm: str = Field(max_length=64)


class PlanBody(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class InterventionBody(BaseModel):
    kind: str = Field(max_length=32)
    source_status: str = Field(default="CLIENT_LABELLED", max_length=32)
    event_id: str = Field(min_length=1, max_length=128)
    evidence_text: str = Field(default="", max_length=200)
    timestamp: str = Field(default="", max_length=64)


class VoiceSafetyBody(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    transcript: str = Field(max_length=200)
    confidence: float
    final: bool = True


class LandmarkBody(BaseModel):
    x: float
    y: float
    visibility: float = 1.0


class GestureFrameBody(BaseModel):
    timestamp_ms: int = Field(ge=0)
    landmarks: list[LandmarkBody] = Field(min_length=21, max_length=21)


class GestureSafetyBody(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    frames: list[GestureFrameBody] = Field(min_length=1, max_length=60)


INDEX_HTML = """<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Quberon Robot Control</title><style>body{font-family:system-ui;margin:0;background:#101418;color:#fff}.wrap{max-width:760px;margin:auto;padding:20px}.banner{background:#7f1d1d;padding:14px;border-radius:12px;font-weight:800}.card{background:#1c2530;border-radius:16px;padding:18px;margin:16px 0}button{font-size:20px;padding:16px;border:0;border-radius:12px;width:100%;margin:8px 0}.stop{background:#dc2626;color:white;font-size:28px;font-weight:900}input,textarea{width:100%;box-sizing:border-box;padding:12px;margin:6px 0;border-radius:8px}pre{white-space:pre-wrap}.muted{color:#cbd5e1}</style></head>
<body><div class='wrap'><div class='banner'>SIMULATED ROBOT - NOT AN EMERGENCY STOP</div><div class='card'><h1>__ROBOT__</h1><p class='muted'>Log in to request STOP. The QR code identifies this robot; it does not authorize you.</p>
<form method='post' action='/auth/login'><input name='username' autocomplete='username' placeholder='Username' required><input name='password' type='password' autocomplete='current-password' placeholder='Password' required><button>Log in</button></form></div>
<div class='card'><h2>Control</h2><div id='status'>Loading status after login...</div><div id='coreNotice'>__CORE_NOTICE__</div><button class='stop' onclick='stopRobot()'>STOP request</button><button id='taskBtn' onclick='task()'>Request simulated task</button><button id='resetBtn' onclick='resetSim()'>Admin: reset simulation latch</button><form onsubmit='plan(event)'><textarea id='planText' placeholder='Describe a simulated job...'></textarea><button>Request Meta plan proposal</button></form><h3>Experimental intervention inputs (NOT recognition)</h3><input id='intervText' placeholder='Transcript for matcher test, e.g. STOP or STOPP'><button onclick='interv("VOICE_STOP")'>Test transcript matcher → STOP</button><button onclick='interv("GESTURE_STOP")'>Inject SYNTHETIC gesture event → STOP</button><button onclick='interv("PANIC_CANDIDATE")'>Record PANIC_CANDIDATE (audit only)</button><pre id='out'></pre><h3>Recent audit events</h3><pre id='events'>—</pre><button onclick='logout()'>Log out</button></div></div>
<script>let csrf='';let lastOk=0;async function load(){try{let r=await fetch('/api/robots/__ROBOT__/status');if(!r.ok)throw new Error(r.status);let j=await r.json();lastOk=Date.now();document.getElementById('status').textContent=JSON.stringify(j,null,2)+'\nLast update: '+new Date(lastOk).toLocaleTimeString();csrf=j.csrf_token||'';let degraded=j.secure_core_available===false;let notice=document.getElementById('coreNotice');notice.textContent=degraded?(j.secure_core_message||''):'';notice.style.display=degraded?'block':'none';document.getElementById('taskBtn').disabled=degraded;document.getElementById('resetBtn').disabled=degraded;document.getElementById('resetBtn').style.display=(j.capabilities||[]).includes('admin')?'block':'none';let ev=await (await fetch('/api/robots/__ROBOT__/events')).json().catch(()=>[]);document.getElementById('events').textContent=(ev||[]).slice(0,8).map(e=>e.ts+' '+e.action+' '+e.auth_result+' '+(e.command_state||'')).join('\n')}catch(e){document.getElementById('status').textContent='STALE / UNCONFIRMED — status fetch failed ('+(lastOk?Math.round((Date.now()-lastOk)/1000)+'s since last update':'no successful update yet')+'). Do not assume robot state.'}}
async function post(path,body,key){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':key||crypto.randomUUID()},body:JSON.stringify(body)});let j=await r.json();document.getElementById('out').textContent=JSON.stringify(j,null,2);load()}
function stopRobot(){post('/api/robots/__ROBOT__/stop',{note:'phone UI STOP request'})}async function interv(kind){let r=await fetch('/api/robots/__ROBOT__/interventions',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({kind:kind,source_status:'SYNTHETIC',event_id:crypto.randomUUID(),evidence_text:document.getElementById('intervText').value})});let j=await r.json();document.getElementById('out').textContent=JSON.stringify(j,null,2);load()}function task(){post('/api/robots/__ROBOT__/simulated-task',{action:'SIMULATE_INSPECTION'})}function resetSim(){if(confirm('Reset simulated latch? This does not start a task.'))post('/api/robots/__ROBOT__/simulation-reset',{confirm:'RESET_SIMULATION'})}async function plan(e){e.preventDefault();post('/api/robots/__ROBOT__/plan',{text:document.getElementById('planText').value})}async function logout(){await fetch('/auth/logout',{method:'POST',headers:{'X-CSRF-Token':csrf}});location.reload()}load();setInterval(load,2000)</script></body></html>"""


def create_app(db_path: Optional[str] = None, adapter_fail: bool = False, provider=None, secure_core="auto") -> FastAPI:
    db_path = str(Path(db_path or os.environ.get("QUBERON_DB_PATH", str(DEFAULT_DB_PATH))).expanduser())
    store = Store(db_path)
    adapter = SimulatedRobotAdapter(fail=adapter_fail or os.environ.get("SIM_ADAPTER_FAIL", "false").lower() == "true")
    if provider is not None:
        meta = provider
    elif os.environ.get("META_MODE"):
        try:
            meta = get_provider()
        except Exception:
            meta = UnavailableMetaProvider()  # fix E: keep simulator interface up
    else:
        meta = MockMetaProvider()
    app = FastAPI(title="Quberon Robot Interface", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store
    app.state.db_path = store.db_path
    app.state.plan_semaphore = threading.BoundedSemaphore(2)
    app.state.voice_recognizer = VoiceStopRecognizer()
    app.state.gesture_recognizer = OpenPalmStopRecognizer()
    # Rust secure core: STOP should obtain a signed ACCEPTED decision here
    # before SimulatedRobotAdapter.stop is invoked as a signed stop. If the
    # core is unavailable, an authenticated STOP still executes UNSIGNED
    # (latch retained, audit-marked); a reachable rejection fails closed.
    # Reset / simulated-task (motion-permitting) require core availability.
    # "auto" builds a client from env: production requires an external key,
    # development explicitly allows ephemeral keys, no mode = no client
    # (which the STOP path above treats as unavailable, not as a rejection).
    if secure_core == "auto":
        try:
            secure_core = client_from_env(ROBOT_ID, app_db_path=db_path)
        except Exception:
            secure_core = None
    app.state.secure_core = secure_core

    def secure_core_available() -> bool:
        """Motion-permitting ops require a present core client/binary."""
        client = app.state.secure_core
        if client is None:
            return False
        binary = getattr(client, "binary", None)
        if binary is None:
            return True
        try:
            return Path(str(binary)).is_file()
        except Exception:
            return False

    def require_secure_core_for_motion():
        if not secure_core_available():
            raise HTTPException(503, "secure core unavailable; latch retained and motion-permitting operation blocked (unsigned reset/task not permitted)")

    @app.exception_handler(sqlite3.Error)
    async def sqlite_degraded(request: Request, exc: sqlite3.Error):
        # Runtime DB failure (fix B): fail closed, never claim durability.
        store.persistence_ok = False
        store.stop_latched = True
        store.observed_state = "UNKNOWN"
        return JSONResponse({"detail": "persistence degraded; task acceptance inhibited and durability not claimed"}, status_code=503)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = (request.headers.get("host") or "").split(":")[0].lower()
        if host and host not in ALLOWED_HOSTS:
            return JSONResponse({"detail": "invalid host"}, status_code=400)
        if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path not in {"/auth/login"}:
            origin = request.headers.get("origin")
            if origin:
                origin_host = origin.split("//", 1)[-1].split(":")[0].lower()
                if origin_host != host:
                    return JSONResponse({"detail": "cross-origin request rejected"}, status_code=403)
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Cache-Control"] = "no-store"
        return resp

    def session(request: Request):
        row = store.get_session(request.cookies.get(SESSION_COOKIE))
        if not row:
            raise HTTPException(401, "login required")
        return row

    def require(request: Request, capability: str, robot_id: str):
        if robot_id != ROBOT_ID:
            raise HTTPException(404, "robot not found")
        row = session(request)
        if capability not in ROLES.get(row["role"], set()):
            raise HTTPException(403, "capability denied")
        return row

    def csrf(request: Request, row):
        supplied = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(supplied, row["csrf"]):
            raise HTTPException(403, "CSRF rejected")

    def event(actor, robot_id, action, auth_result, key, payload_hash, result=None, detail=""):
        eid = secrets.token_urlsafe(16)
        with store._db() as db:
            db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)", (eid, iso(), actor, robot_id, action, auth_result, key, payload_hash, result.command_state if result else None, result.observed_state if result else None, detail or (result.detail if result else "")))
        return eid

    @app.get("/healthz")
    def healthz():
        return {"ok": bool(store.persistence_ok), "robot_id": ROBOT_ID, "adapter_mode": "SIMULATION", "persistence_ok": store.persistence_ok}

    @app.get("/", response_class=RedirectResponse)
    def root():
        return RedirectResponse(f"/robots/{ROBOT_ID}", status_code=302)

    @app.get("/robots/{robot_id}", response_class=HTMLResponse)
    def robot_page(robot_id: str):
        if robot_id != ROBOT_ID:
            raise HTTPException(404, "robot not found")
        return INDEX_HTML.replace("__ROBOT__", ROBOT_ID).replace("__CORE_NOTICE__", "" if secure_core_available() else SECURE_CORE_NOT_BUILT_MESSAGE)

    @app.post("/auth/login")
    def login(username: str = Form(...), password: str = Form(...)):
        if not store.persistence_ok:
            raise HTTPException(503, "persistence degraded")
        if not store.login_allowed(username):
            raise HTTPException(429, "too many login attempts; wait and retry")
        user = store.get_user(username)
        ok = bool(user and verify_password(password, user["password_hash"]))
        store.record_login(username, ok)
        if not ok:
            raise HTTPException(401, "invalid login")
        token, _ = store.create_session(username)
        resp = RedirectResponse(f"/robots/{ROBOT_ID}", status_code=303)
        resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict", secure=not INSECURE_HTTP, max_age=28800, path="/")
        return resp

    @app.post("/auth/logout")
    def logout(request: Request, x_csrf_token: str = Header(default="")):
        row = session(request)
        if not hmac.compare_digest(x_csrf_token, row["csrf"]):
            raise HTTPException(403, "CSRF rejected")
        store.delete_session(request.cookies.get(SESSION_COOKIE))
        resp = JSONResponse({"logged_out": True})
        resp.delete_cookie(SESSION_COOKIE, path="/")
        return resp

    @app.get("/api/robots/{robot_id}/status")
    def status(robot_id: str, request: Request):
        row = require(request, "read", robot_id)
        data = store.status()
        data.update({"actor": row["username"], "role": row["role"], "capabilities": sorted(ROLES[row["role"]]), "csrf_token": row["csrf"], "secure_core_available": secure_core_available(), "secure_core_message": None if secure_core_available() else SECURE_CORE_NOT_BUILT_MESSAGE})
        return data

    def execute_stop(actor_username: str, robot_id: str, idempotency_key: str, payload_hash: str, action_label: str = "STOP"):
        """The ONE stop path. Button, voice, gesture and future inputs all
        converge here: persistence check, idempotency, adapter result,
        persistent latch, audit event. No input modality gets a weaker route,
        and no intervention can clear the latch through this function."""
        with store.lock:
            if not store.persistence_ok:
                store.stop_latched = True
                raise HTTPException(503, "persistence degraded; task acceptance inhibited and durability not claimed")
            with store._db() as db:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT * FROM events WHERE actor=? AND robot_id=? AND idempotency_key=?", (actor_username, robot_id, idempotency_key)).fetchone()
                if existing:
                    if existing["payload_hash"] != payload_hash:
                        raise HTTPException(409, "idempotency key conflicts with a different payload")
                    # Historical duplicate: report the recorded result as history,
                    # never as a claim about the simulator's CURRENT state (fix A).
                    return {"command_id": existing["id"], "command_state": existing["command_state"], "observed_state": existing["observed_state"], "historical_duplicate": True, "current_stop_latched": bool(store.stop_latched), "current_observed_state": store.observed_state, "stop_latched": bool(store.stop_latched), "duplicate": True}
                # Rust secure-core attestation: ACCEPTED = signed stop.
                # Core unavailable: authenticated simulation STOP still
                # executes UNSIGNED (adapter invoked, latch retained,
                # audit UNSIGNED/core_unavailable). Reachable REJECTED:
                # fail closed, no adapter, latch retained, UNKNOWN.
                core_client = app.state.secure_core
                core_decision = {}
                secure_core_obj = {"status": "unavailable", "decision": None, "sequence": None, "audit_record": None, "scope": "SIMULATION_ONLY_STOP_AUTHORIZATION"}
                auth_result = "UNSIGNED/core_unavailable"
                detail_prefix = "UNSIGNED core_unavailable: no signed secure-core decision; authenticated simulation STOP executed without attestation; "
                try:
                    if core_client is None:
                        raise SecureCoreUnavailable("secure core unavailable")
                    core_decision = core_client.authorize_stop(subject=actor_username)
                    secure_core_obj = {"status": "accepted", "decision": core_decision.get("code"), "sequence": core_decision.get("sequence"), "audit_record": core_decision.get("audit_record"), "scope": "SIMULATION_ONLY_STOP_AUTHORIZATION"}
                    auth_result = "allowed"
                    detail_prefix = ""
                except SecureCoreUnavailable:
                    pass
                except Exception as exc:
                    decision = exc.decision if isinstance(exc, SecureCoreRejected) else {}
                    code = decision.get("code") or (str(exc) if isinstance(exc, SecureCoreError) else type(exc).__name__)
                    eid = secrets.token_urlsafe(16)
                    db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)", (eid, iso(), actor_username, robot_id, action_label, "secure_core_rejected", idempotency_key, payload_hash, "UNKNOWN", "UNKNOWN", f"secure core did not authorize STOP; adapter not invoked; {code}"))
                    store.set_state(db, True, "UNKNOWN")
                    db.execute("COMMIT")
                    return JSONResponse(status_code=503, content={"detail": "secure core rejected STOP; latch retained, state UNKNOWN, adapter not invoked", "command_id": eid, "command_state": "UNKNOWN", "observed_state": "UNKNOWN", "stop_latched": True, "secure_core": {"status": "rejected", "decision": code, "sequence": decision.get("sequence"), "audit_record": decision.get("audit_record"), "scope": "SIMULATION_ONLY_STOP_AUTHORIZATION"}})
                result = adapter.stop()
                eid = secrets.token_urlsafe(16)
                db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)", (eid, iso(), actor_username, robot_id, action_label, auth_result, idempotency_key, payload_hash, result.command_state, result.observed_state, detail_prefix + (result.detail or "")))
                if result.command_state == "ACKNOWLEDGED":
                    store.set_state(db, True, result.observed_state)
                else:
                    store.set_state(db, True, "UNKNOWN")
                db.execute("COMMIT")
                return {"command_id": eid, "command_state": result.command_state, "observed_state": store.observed_state, "stop_latched": True, "detail": result.detail, "secure_core": secure_core_obj}

    @app.post("/api/robots/{robot_id}/stop")
    def stop(robot_id: str, body: StopBody, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key")):
        row = require(request, "stop", robot_id)
        csrf(request, row)
        if not idempotency_key or len(idempotency_key) > 128:
            raise HTTPException(400, "valid Idempotency-Key required")
        payload_hash = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        return execute_stop(row["username"], robot_id, idempotency_key, payload_hash)

    @app.post("/api/robots/{robot_id}/interventions")
    def interventions(robot_id: str, body: InterventionBody, request: Request):
        """Experimental multimodal intervention intake (see
        docs/INTERVENTION-INPUTS.md). Authority = authenticated session +
        CSRF, never the modality label. Stop kinds converge on execute_stop;
        PANIC_CANDIDATE is audit-only and cannot trigger or clear anything."""
        row = require(request, "stop", robot_id)
        csrf(request, row)
        try:
            kind = InterventionKind(body.kind)
            source = SourceStatus(body.source_status)
        except ValueError:
            raise HTTPException(400, "unknown intervention kind or source_status")
        ts = None
        if body.timestamp:
            try:
                ts = datetime.fromisoformat(body.timestamp.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except ValueError:
                raise HTTPException(400, "timestamp must be ISO-8601")
        ev = InterventionEvent(robot_id=robot_id, event_id=body.event_id, kind=kind, source_status=source, evidence_text=body.evidence_text, **({"timestamp": ts} if ts else {}))
        errors = ev.validate(robot_id)
        if errors:
            raise HTTPException(400, "; ".join(errors))
        if kind not in STOP_KINDS:
            eid = event(row["username"], robot_id, kind.value, "audit_only", None, None, None, detail=f"client_event_id={body.event_id}; source={source.value}; no stop triggered by label alone")
            return {"event_id": eid, "kind": kind.value, "stop_triggered": False, "stop_latched": bool(store.stop_latched), "note": "PANIC_CANDIDATE is recorded for human review only; it is not panic detection and never triggers or clears a stop."}
        payload_hash = hashlib.sha256(f"{kind.value}|{source.value}|{body.evidence_text}".encode()).hexdigest()
        result = execute_stop(row["username"], robot_id, body.event_id, payload_hash, action_label=kind.value)
        if isinstance(result, JSONResponse):
            return result
        result.update({"kind": kind.value, "source_status": source.value, "stop_triggered": True})
        return result

    @app.post("/api/robots/{robot_id}/safety-inputs/voice")
    def voice_safety_input(robot_id: str, body: VoiceSafetyBody, request: Request):
        """Recognize a bounded transcript observation, then use the one STOP path."""
        row = require(request, "stop", robot_id)
        csrf(request, row)
        decision = app.state.voice_recognizer.recognize(VoiceObservation(body.transcript, body.confidence, body.final))
        if not decision.stop_requested:
            return {"event_id": body.event_id, "stop_triggered": False, "reason": decision.reason, "stop_latched": bool(store.stop_latched)}
        payload_hash = hashlib.sha256(f"VOICE_STOP|{body.transcript}|{body.confidence}|{body.final}".encode()).hexdigest()
        result = execute_stop(row["username"], robot_id, body.event_id, payload_hash, action_label="VOICE_STOP")
        if isinstance(result, JSONResponse):
            return result
        result.update({"kind": "VOICE_STOP", "source_status": "DEVICE_RECOGNIZED", "stop_triggered": True, "matched_token": decision.matched_token})
        return result

    @app.post("/api/robots/{robot_id}/safety-inputs/gesture")
    def gesture_safety_input(robot_id: str, body: GestureSafetyBody, request: Request):
        """Recognize recorded normalized hand observations, then use STOP."""
        row = require(request, "stop", robot_id)
        csrf(request, row)
        frames = [GestureFrame(f.timestamp_ms, [HandLandmark(p.x, p.y, p.visibility) for p in f.landmarks]) for f in body.frames]
        decision = app.state.gesture_recognizer.recognize(frames)
        if not decision.stop_requested:
            return {"event_id": body.event_id, "stop_triggered": False, "reason": decision.reason, "qualifying_frames": decision.qualifying_frames, "held_ms": decision.held_ms, "stop_latched": bool(store.stop_latched)}
        canonical = json.dumps(body.model_dump(), sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(canonical.encode()).hexdigest()
        result = execute_stop(row["username"], robot_id, body.event_id, payload_hash, action_label="GESTURE_STOP")
        if isinstance(result, JSONResponse):
            return result
        result.update({"kind": "GESTURE_STOP", "source_status": "DEVICE_RECOGNIZED", "stop_triggered": True, "qualifying_frames": decision.qualifying_frames, "held_ms": decision.held_ms})
        return result

    @app.post("/api/robots/{robot_id}/simulated-task")
    def simulated_task(robot_id: str, body: TaskBody, request: Request, idempotency_key: str = Header(default="")):
        row = require(request, "task", robot_id)
        csrf(request, row)
        if body.action not in {"SIMULATE_INSPECTION", "SIMULATE_STATUS_CHECK"}:
            raise HTTPException(400, "simulated action not allow-listed")
        with store.lock:
            if not store.persistence_ok:
                raise HTTPException(503, "persistence degraded")
            if store.stop_latched:
                raise HTTPException(409, "STOP latch is active; simulated task rejected")
            require_secure_core_for_motion()
            if idempotency_key:
                # Fix F: exact retry returns the previous result WITHOUT invoking
                # the adapter again; same key + different action is a conflict.
                with store._db() as db:
                    existing = db.execute("SELECT * FROM events WHERE actor=? AND robot_id=? AND idempotency_key=?", (row["username"], robot_id, idempotency_key)).fetchone()
                if existing:
                    if existing["action"] != body.action:
                        raise HTTPException(409, "idempotency key conflicts with a different action")
                    return {"command_id": existing["id"], "command_state": existing["command_state"], "observed_state": store.observed_state, "duplicate": True}
            result = adapter.simulated_task(body.action)
            eid = event(row["username"], robot_id, body.action, "allowed", idempotency_key or None, None, result)
            if result.command_state == "ACKNOWLEDGED":
                with store._db() as db:
                    store.set_state(db, False, result.observed_state)
            return {"command_id": eid, "command_state": result.command_state, "observed_state": store.observed_state}

    @app.post("/api/robots/{robot_id}/simulation-reset")
    def reset(robot_id: str, body: ResetBody, request: Request):
        row = require(request, "admin", robot_id)
        csrf(request, row)
        if body.confirm != "RESET_SIMULATION":
            raise HTTPException(400, "explicit confirmation required")
        if not store.persistence_ok:
            raise HTTPException(503, "persistence degraded; reset inhibited")
        require_secure_core_for_motion()
        with store.lock:
            result = adapter.reset_simulation()
            eid = event(row["username"], robot_id, "SIMULATION_RESET", "allowed", None, None, result)
            if result.command_state == "ACKNOWLEDGED":
                with store._db() as db:
                    store.set_state(db, False, result.observed_state)
            return {"command_id": eid, "command_state": result.command_state, "observed_state": store.observed_state, "stop_latched": store.stop_latched, "task_started": False}

    @app.get("/api/robots/{robot_id}/events")
    def events(robot_id: str, request: Request):
        require(request, "read", robot_id)
        with store._db() as db:
            rows = db.execute("SELECT id,ts,actor,robot_id,action,auth_result,command_state,observed_state FROM events WHERE robot_id=? ORDER BY ts DESC LIMIT 50", (robot_id,)).fetchall()
            return [dict(r) for r in rows]

    @app.post("/api/robots/{robot_id}/plan")
    def plan(robot_id: str, body: PlanBody, request: Request):
        row = require(request, "plan", robot_id)
        csrf(request, row)
        # Fix D: planner work is capped by its OWN small limiter. A saturated
        # planner returns 'busy' immediately instead of consuming the shared
        # sync-worker capacity that STOP depends on. Best-effort, not real-time.
        if not app.state.plan_semaphore.acquire(blocking=False):
            return {"provider_status": "busy", "error": "planner concurrency limit", "stop_unaffected": True}
        try:
            try:
                proposal = meta.propose(robot_id, body.text)
            except Exception as exc:
                return {"provider_status": "unavailable", "error": type(exc).__name__, "stop_unaffected": True}
            try:
                validation = validate_plan(proposal, robot_id, store.stop_latched)
            except Exception as exc:  # provider output must never escape as a 500 (fix C)
                validation = {"allowed_as_proposal": False, "errors": [f"invalid proposal: {type(exc).__name__}"], "latch_blocks_task": bool(store.stop_latched)}
            # Wave4 N1 (N5 escapes A/B + provenance finding): downstream
            # only ever sees the bounded sanitized copy -- never the raw
            # untrusted proposal (no NaN render 500, no 100KB reflection,
            # no forged secure_core/stop_latched fields).
            visible = sanitize_proposal(proposal)
            if validation.get("provenance_forgery_attempt"):
                # Audit the forgery attempt (plan-related event type only,
                # I6): field paths, never attacker values or large content.
                paths = [str(p)[:64] for p in validation.get("trusted_fields_rejected", [])[:5]]
                try:
                    event(row["username"], robot_id, "PLAN_PROPOSAL", "provenance_forgery_rejected", None,
                          hashlib.sha256(",".join(paths).encode()).hexdigest(), None,
                          detail="provenance-forgery attempt in planner proposal: trusted-looking fields stripped from downstream-visible data: " + ",".join(paths))
                except Exception:
                    validation = {**validation, "audit_failed": True}
            return {"provider": getattr(meta, "name", "unknown"), "proposal": visible, "validation": validation}
        finally:
            app.state.plan_semaphore.release()

    return app


def asgi_app() -> FastAPI:
    """Explicit ASGI application factory; importing this module is inert."""
    return create_app()
