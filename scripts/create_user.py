#!/usr/bin/env python3
import argparse, getpass, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.main import Store

p = argparse.ArgumentParser()
p.add_argument("--db", default=os.environ.get("QUBERON_DB_PATH", "/var/lib/quberon-robot-interface/quberon.db"))
p.add_argument("--username", required=True)
p.add_argument("--role", choices=["viewer", "operator", "admin"], required=True)
p.add_argument("--password-env", default="")
a = p.parse_args()
password = (os.environ.get(a.password_env) or "") if a.password_env else getpass.getpass("Password (input hidden): ")
if len(password) < 12:
    raise SystemExit("Use at least 12 characters for this throwaway demo account")
Store(a.db).create_user(a.username, password, a.role)
print(f"created/updated {a.username} role={a.role}")
