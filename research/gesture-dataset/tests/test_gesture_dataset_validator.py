import copy, importlib.util, json, os
HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "..", "..")
_spec = importlib.util.spec_from_file_location("gesture_dataset_validate", os.path.join(HERE, "..", "validate.py"))
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
validate_records, load_jsonl = _mod.validate_records, _mod.load_jsonl
EXAMPLE = os.path.join(HERE, "..", "examples", "synthetic-example.jsonl")

def base(): return load_jsonl(EXAMPLE)
def changed(fn):
    r = base(); fn(r); return validate_records(r)

def test_synthetic_example_is_valid():
    assert validate_records(base()) == []

def test_example_is_deterministic_synthetic_only():
    recs = base()
    assert all(r["synthetic"] and r["source"] == "synthetic" for r in recs)
    assert {r["split"] for r in recs} == {"train", "val", "test"}
    assert len({r["clip_id"] for r in recs}) == len(recs) == 12

def test_malformed_missing_and_bad_enum_fail():
    assert changed(lambda r: r[0].pop("consent"))
    assert changed(lambda r: r[0].update(split="training"))
    assert changed(lambda r: r[0].update(label="wave"))

def test_boundary_expectation_is_recomputed():
    # 699 ms record is intent-positive but expectation-negative; flipping it must fail.
    assert changed(lambda r: [x.update(expected_endpoint_trigger=True) for x in r if x["clip_id"] == "SYN-BND-001"])

def test_leakage_by_person_session_environment_fails():
    for key in ("person_id", "session_id", "environment_id"):
        def leak(r, key=key):
            src = next(x for x in r if x["split"] == "train"); dst = next(x for x in r if x["split"] == "test")
            dst[key] = src[key]
        assert changed(leak), key

def test_duplicate_clip_and_hash_leak_fail():
    assert changed(lambda r: r.append(copy.deepcopy(r[0])))
    def h(r): r[-1]["frames_hash"] = r[0]["frames_hash"]
    assert changed(h)

def test_temporal_anomaly_must_be_tagged_and_consistent():
    assert changed(lambda r: [x["frames"].update(temporal_tag="none") for x in r if x["clip_id"] == "SYN-TMP-001"])
    assert changed(lambda r: [x["frames"].update(frame_timestamps_ms=[0, 350, 700]) for x in r if x["clip_id"] == "SYN-TMP-002"])

def test_human_capture_without_consent_and_pii_fail():
    def human(r):
        x = r[0]; x.update(source="human_capture", synthetic=False, person_id="person-01")
        x["consent"].update(status="not_applicable_synthetic", consent_id=None)
    assert changed(human)
    assert changed(lambda r: r[0].update(email="a@example.com"))
    assert changed(lambda r: r[0]["consent"].update(status="withdrawn"))

def test_crossmodal_or_expectation():
    # SYN-XMO-002: fist (no gesture) + final confident voice STOP -> expected True.
    rec = next(x for x in base() if x["clip_id"] == "SYN-XMO-002")
    assert rec["expected_endpoint_trigger"] is True
    assert changed(lambda r: [x.update(expected_endpoint_trigger=False) for x in r if x["clip_id"] == "SYN-XMO-002"])
