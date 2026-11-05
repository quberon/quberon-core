#!/usr/bin/env python3
import io, json, pathlib, sys, unittest, zipfile
from importlib.machinery import SourceFileLoader
HERE = pathlib.Path(__file__).resolve().parent
V = SourceFileLoader("quberon_verify", str(HERE.parent / "quberon-verify")).load_module()
GOOD = HERE / "fixtures" / "simulated-stop.qeb"
TAMPERED = HERE / "fixtures" / "tampered-replay.qeb"

def repack(path, mutate):
    zin = zipfile.ZipFile(path); data = {n: zin.read(n) for n in zin.namelist()}
    mutate(data); buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in sorted(data):
            zi = zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED; z.writestr(zi, data[n])
    p = HERE / "_tmp.qeb"; p.write_bytes(buf.getvalue()); return p

class Verify(unittest.TestCase):
    def tearDown(self):
        t = HERE / "_tmp.qeb"
        if t.exists(): t.unlink()
    def test_good_passes_limited_claims(self):
        r = V.validate(str(GOOD)); self.assertEqual(r["verdict"], "PASS_LIMITED_CLAIMS", r)
        self.assertIn("physical_stop_or_safety_rated_estop", r["unsupported_claims"])
        self.assertNotIn("certification_or_regulatory_compliance", r["supported_claims"])
    def test_committed_tampered_rejected(self):
        r = V.validate(str(TAMPERED)); self.assertEqual(r["verdict"], "REJECT")
        self.assertIn("REPLAY_TASK_OUTPUTS_MISMATCH", r["errors"]); self.assertIn("HASH_MISMATCH:copper/replay-task-outputs.bin", r["errors"])
    def test_signature_tamper_rejected(self):
        def m(d):
            e = json.loads(d["secure-core/envelope.json"]); e["signature"] = ("0" if e["signature"][0] != "0" else "1") + e["signature"][1:]
            d["secure-core/envelope.json"] = json.dumps(e).encode()
        r = V.validate(str(repack(GOOD, m))); self.assertIn("SIGNATURE_INVALID", r["errors"])
    def test_audit_chain_tamper_rejected(self):
        def m(d):
            a = json.loads(d["secure-core/audit.json"]); a[0]["decision_code"] = "FORGED"; d["secure-core/audit.json"] = json.dumps(a).encode()
        r = V.validate(str(repack(GOOD, m))); self.assertIn("AUDIT_CHAIN_INVALID", r["errors"])
    def test_env_incomplete_rejected(self):
        def m(d):
            e = json.loads(d["environment.json"]); del e["git_commit"]; d["environment.json"] = json.dumps(e).encode()
        r = V.validate(str(repack(GOOD, m))); self.assertIn("ENV_FIELD_MISSING:git_commit", r["errors"])
    def test_physical_claim_rejected(self):
        def m(d):
            e = json.loads(d["secure-core/decision.json"]); e["physical_state_claim"] = "STOPPED"; d["secure-core/decision.json"] = json.dumps(e).encode()
        r = V.validate(str(repack(GOOD, m))); self.assertIn("DECISION_PHYSICAL_CLAIM_VIOLATION", r["errors"])
    def test_not_a_bundle_rejected(self):
        p = HERE / "_tmp.qeb"; p.write_bytes(b"not a zip")
        r = V.validate(str(p)); self.assertEqual(r["errors"], ["BUNDLE_EMPTY_OR_NOT_ZIP"])

if __name__ == "__main__": unittest.main()
