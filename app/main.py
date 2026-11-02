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
from integrations.meta import MockMetaProvider, get_provider, validate_plan

ROBOT_ID = os.environ.get("ROBOT_ID", "quberon-demo-001")
ROLES = {"viewer": {"read"}, "operator": {"read", "stop", "task", "plan"}, "admin": {"read", "stop", "task", "plan", "admin"}}
ALLOWED_HOSTS = {h.strip().lower() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,10.77.0.2,10.99.0.1,quberon-pi.local,testserver").split(",") if h.strip()}
INSECURE_HTTP = os.environ.get("DEMO_INSECURE_HTTP", "false").lower() == "true"
SESSION_COOKIE = "quberon_session"


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
        self.db_path = db_path
        self.lock = threading.RLock()
        self.persistence_ok = True
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
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

    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
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


INDEX_HTML = """<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Quberon Robot Control</title><style>body{font-family:system-ui;margin:0;background:#101418;color:#fff}.wrap{max-width:760px;margin:auto;padding:20px}.banner{background:#7f1d1d;padding:14px;border-radius:12px;font-weight:800}.card{background:#1c2530;border-radius:16px;padding:18px;margin:16px 0}button{font-size:20px;padding:16px;border:0;border-radius:12px;width:100%;margin:8px 0}.stop{background:#dc2626;color:white;font-size:28px;font-weight:900}input,textarea{width:100%;box-sizing:border-box;padding:12px;margin:6px 0;border-radius:8px}pre{white-space:pre-wrap}.muted{color:#cbd5e1}</style></head>
<body><div class='wrap'><div class='banner'>SIMULATED ROBOT - NOT AN EMERGENCY STOP</div><div class='card'><h1>__ROBOT__</h1><p class='muted'>Log in to request STOP. The QR code identifies this robot; it does not authorize you.</p>
<form method='post' action='/auth/login'><input name='username' autocomplete='username' placeholder='Username' required><input name='password' type='password' autocomplete='current-password' placeholder='Password' required><button>Log in</button></form></div>
<div class='card'><h2>Control</h2><div id='status'>Loading status after login...</div><button class='stop' onclick='stopRobot()'>STOP request</button><button onclick='task()'>Request simulated task</button><button id='resetBtn' onclick='resetSim()'>Admin: reset simulation latch</button><form onsubmit='plan(event)'><textarea id='planText' placeholder='Describe a simulated job...'></textarea><button>Request Meta plan proposal</button></form><pre id='out'></pre><button onclick='logout()'>Log out</button></div></div>
<script>let csrf='';async function load(){let r=await fetch('/api/robots/__ROBOT__/status');let j=await r.json();document.getElementById('status').textContent=JSON.stringify(j,null,2);csrf=j.csrf_token||'';document.getElementById('resetBtn').style.display=(j.capabilities||[]).includes('admin')?'block':'none'}
async function post(path,body,key){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Idempotency-Key':key||crypto.randomUUID()},body:JSON.stringify(body)});let j=await r.json();document.getElementById('out').textContent=JSON.stringify(j,null,2);load()}
function stopRobot(){post('/api/robots/__ROBOT__/stop',{note:'phone UI STOP request'})}function task(){post('/api/robots/__ROBOT__/simulated-task',{action:'SIMULATE_INSPECTION'})}function resetSim(){if(confirm('Reset simulated latch? This does not start a task.'))post('/api/robots/__ROBOT__/simulation-reset',{confirm:'RESET_SIMULATION'})}async function plan(e){e.preventDefault();post('/api/robots/__ROBOT__/plan',{text:document.getElementById('planText').value})}async function logout(){await fetch('/auth/logout',{method:'POST',headers:{'X-CSRF-Token':csrf}});location.reload()}load()</script></body></html>"""


def create_app(db_path: Optional[str] = None, adapter_fail: bool = False, provider=None) -> FastAPI:
    db_path = db_path or os.environ.get("QUBERON_DB_PATH", "/var/lib/quberon-robot-interface/quberon.db")
    store = Store(db_path)
    adapter = SimulatedRobotAdapter(fail=adapter_fail or os.environ.get("SIM_ADAPTER_FAIL", "false").lower() == "true")
    meta = provider or (get_provider() if os.environ.get("META_MODE") else MockMetaProvider())
    app = FastAPI(title="Quberon Robot Interface", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store

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
        return {"ok": True, "robot_id": ROBOT_ID, "adapter_mode": "SIMULATION", "persistence_ok": store.persistence_ok}

    @app.get("/", response_class=RedirectResponse)
    def root():
        return RedirectResponse(f"/robots/{ROBOT_ID}", status_code=302)

    @app.get("/robots/{robot_id}", response_class=HTMLResponse)
    def robot_page(robot_id: str):
        if robot_id != ROBOT_ID:
            raise HTTPException(404, "robot not found")
        return INDEX_HTML.replace("__ROBOT__", ROBOT_ID)

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
        data.update({"actor": row["username"], "role": row["role"], "capabilities": sorted(ROLES[row["role"]]), "csrf_token": row["csrf"]})
        return data

    @app.post("/api/robots/{robot_id}/stop")
    def stop(robot_id: str, body: StopBody, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key")):
        row = require(request, "stop", robot_id)
        csrf(request, row)
        if not idempotency_key or len(idempotency_key) > 128:
            raise HTTPException(400, "valid Idempotency-Key required")
        payload_hash = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        with store.lock:
            if not store.persistence_ok:
                store.stop_latched = True
                raise HTTPException(503, "persistence degraded; task acceptance inhibited and durability not claimed")
            with store._db() as db:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT * FROM events WHERE actor=? AND robot_id=? AND idempotency_key=?", (row["username"], robot_id, idempotency_key)).fetchone()
                if existing:
                    if existing["payload_hash"] != payload_hash:
                        raise HTTPException(409, "idempotency key conflicts with a different payload")
                    return {"command_id": existing["id"], "command_state": existing["command_state"], "observed_state": existing["observed_state"], "stop_latched": True, "duplicate": True}
                result = adapter.stop()
                eid = secrets.token_urlsafe(16)
                db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)", (eid, iso(), row["username"], robot_id, "STOP", "allowed", idempotency_key, payload_hash, result.command_state, result.observed_state, result.detail))
                if result.command_state == "ACKNOWLEDGED":
                    store.set_state(db, True, result.observed_state)
                else:
                    store.set_state(db, True, "UNKNOWN")
                db.execute("COMMIT")
                return {"command_id": eid, "command_state": result.command_state, "observed_state": store.observed_state, "stop_latched": True, "detail": result.detail}

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
        try:
            proposal = meta.propose(robot_id, body.text)
        except Exception as exc:
            return {"provider_status": "unavailable", "error": type(exc).__name__, "stop_unaffected": True}
        validation = validate_plan(proposal, robot_id, store.stop_latched)
        return {"provider": getattr(meta, "name", "unknown"), "proposal": proposal, "validation": validation}

    return app


app = create_app(db_path=os.environ.get("QUBERON_DB_PATH", "/tmp/quberon-robot-interface.db"))
