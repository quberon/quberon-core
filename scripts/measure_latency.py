#!/usr/bin/env python3
"""Measure authenticated simulated STOP latency against a deployed Pi.
Credentials are read from env; results contain no secrets."""
import os, statistics, time, uuid
import httpx

base = os.environ["CONTROL_BASE"].rstrip("/")
ca = os.environ["CA_CERT"]
user, pw = os.environ["DEMO_USER"], os.environ["DEMO_PASSWORD"]
robot = os.environ.get("ROBOT_ID", "quberon-demo-001")
samples = []
with httpx.Client(base_url=base, verify=ca, timeout=10) as c:
    r = c.post("/auth/login", data={"username": user, "password": pw}, follow_redirects=False)
    assert r.status_code in (302, 303), r.status_code
    st = c.get(f"/api/robots/{robot}/status").json()
    csrf = st["csrf_token"]
    # Ensure admin/operator flow starts from reset only if explicitly requested.
    for i in range(30):
        t0 = time.perf_counter()
        r = c.post(f"/api/robots/{robot}/stop", json={"note": "latency bench"}, headers={"X-CSRF-Token": csrf, "Idempotency-Key": str(uuid.uuid4())})
        elapsed = (time.perf_counter() - t0) * 1000
        r.raise_for_status(); samples.append(elapsed)
        # Admin reset between samples only when RESET_BETWEEN=1 and user has admin capability.
        if os.environ.get("RESET_BETWEEN") == "1":
            rr = c.post(f"/api/robots/{robot}/simulation-reset", json={"confirm": "RESET_SIMULATION"}, headers={"X-CSRF-Token": csrf})
            rr.raise_for_status()
samples.sort()
p95 = samples[int(0.95 * (len(samples)-1))]
print(f"samples={len(samples)} median_ms={statistics.median(samples):.2f} p95_ms={p95:.2f} min_ms={samples[0]:.2f} max_ms={samples[-1]:.2f}")
