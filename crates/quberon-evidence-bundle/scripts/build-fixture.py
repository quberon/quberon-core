#!/usr/bin/env python3
"""Build the simulated STOP fixture using the REAL secure-core CLI for
sign+authorize (not a reimplementation), the ACTUAL committed Copper
evidence under spikes/copper-stop-path/evidence, and the Rust bundle
builder. Simulation only. Usage:
  build-fixture.py --repo ROOT --secure-cli BIN --bundle-bin BIN --out GOOD [--tampered OUT2]
The signing key is ephemeral/generated for this simulated fixture; it is
not production custody and proves no signer authority (see claims)."""
import argparse, hashlib, json, pathlib, platform, sqlite3, subprocess, sys, tempfile, time, zipfile

def run(cmd, inp=None):
    p=subprocess.run(cmd, input=inp, capture_output=True, text=True)
    if p.returncode!=0: print(p.stdout); print(p.stderr, file=sys.stderr); raise SystemExit(f"failed: {cmd}")
    return p.stdout.strip()
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
    a=argparse.ArgumentParser(); a.add_argument("--repo",required=True); a.add_argument("--secure-cli",required=True); a.add_argument("--bundle-bin",required=True); a.add_argument("--out",required=True); a.add_argument("--tampered")
    x=a.parse_args(); repo=pathlib.Path(x.repo)
    with tempfile.TemporaryDirectory() as td:
        td=pathlib.Path(td); secure=td/"secure"; secure.mkdir()
        kp=json.loads(run([x.secure_cli,"generate-keypair"]))
        now=int(time.time())
        req={"signing_key_hex":kp["signing_key_hex"],"kid":"sim-fixture-key-1","issuer":"quberon-sim-issuer","robot_id":"sim-robot-01","simulation_id":"copper-stop-sim","subject":"simulated-operator","epoch":1,"sequence":1,"issued_at_unix":now-10,"expires_at_unix":now+290}
        env=json.loads(run([x.secure_cli,"sign"], json.dumps(req)))
        (secure/"envelope.json").write_text(json.dumps(env,indent=2))
        (secure/"verifying-key.json").write_text(json.dumps({"kid":"sim-fixture-key-1","verifying_key_hex":kp["verifying_key_hex"],"key_origin":"ephemeral_simulated_fixture_not_production"},indent=2))
        auth={"db_path":str(td/"core.db"),"anchor_path":str(td/"anchor.json"),"boot_epoch":1,"trusted":[{"kid":"sim-fixture-key-1","issuer":"quberon-sim-issuer","robot_id":"sim-robot-01","simulation_id":"copper-stop-sim","verifying_key_hex":kp["verifying_key_hex"]}],"envelope":env,"now_unix":now}
        dec=json.loads(run([x.secure_cli,"authorize"], json.dumps(auth)))
        if dec.get("code")!="ACCEPTED_SIMULATION_STOP_AUTHORIZATION": raise SystemExit(f"secure-core did not accept: {dec}")
        (secure/"decision.json").write_text(json.dumps(dec,indent=2))
        con=sqlite3.connect(td/"core.db")
        rows=con.execute("SELECT seq,payload_hash,decision_code,prev_hash,record_hash FROM audit ORDER BY seq").fetchall()
        audit=[{"seq":r[0],"payload_hash":r[1],"decision_code":r[2],"prev_hash":r[3],"record_hash":r[4]} for r in rows]
        (secure/"audit.json").write_text(json.dumps(audit,indent=2))
        # cu29 version from spike lockfile
        lock=(repo/"spikes/copper-stop-path/Cargo.lock").read_text(); cu="unknown"
        for block in lock.split("[[package]]"):
            if 'name = "cu29"' in block:
                for line in block.splitlines():
                    if line.startswith("version"): cu=line.split('"')[1]
        env_manifest={"arch":platform.machine(),"cargo_version":run(["cargo","--version"]),"copper_config_sha256":sha(repo/"spikes/copper-stop-path/copper.ron"),"copper_cu29_version":cu,"created_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(now)),"git_commit":run(["git","rev-parse","HEAD"],), "os":platform.system(),"os_version":platform.release(),"python_version":platform.python_version(),"rustc_version":run(["rustc","--version"]),"secure_core_cli_sha256":sha(x.secure_cli),"secure_core_source_sha256":sha(repo/"crates/quberon-secure-core/src/lib.rs"),"bundle_builder":"crates/quberon-evidence-bundle (quberon-bundle)","copper_evidence_source":"spikes/copper-stop-path/evidence (committed Wave3 N3 record/replay)"}
        # git rev-parse must run in repo
        env_manifest["git_commit"]=subprocess.run(["git","rev-parse","HEAD"],cwd=repo,capture_output=True,text=True).stdout.strip()
        envp=td/"environment.json"; envp.write_text(json.dumps(env_manifest,indent=2))
        out=pathlib.Path(x.out); out.parent.mkdir(parents=True,exist_ok=True)
        print(run([x.bundle_bin,"build","--out",str(out),"--bundle-id","simulated-stop-v1","--signing-seed-hex",kp["signing_key_hex"],"--copper-dir",str(repo/"spikes/copper-stop-path/evidence"),"--secure-dir",str(secure),"--environment",str(envp)]))
        print(f"audit_records={len(audit)} decision={dec['code']} audit_tip={audit[-1]['record_hash']}")
        if x.tampered:
            data={n:zipfile.ZipFile(out).read(n) for n in zipfile.ZipFile(out).namelist()}
            b=bytearray(data["copper/replay-task-outputs.bin"]); b[0]^=0xFF; data["copper/replay-task-outputs.bin"]=bytes(b)
            tp=pathlib.Path(x.tampered); tp.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(tp,"w",zipfile.ZIP_DEFLATED) as z:
                for n in sorted(data): zi=zipfile.ZipInfo(n,(1980,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED; z.writestr(zi,data[n])
            print(f"TAMPERED_WROTE {tp}")
if __name__=="__main__": main()
