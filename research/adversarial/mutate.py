"""Deterministic mutation engine, no model. Never run against the Pi.

Systematic mutations of benign control payloads: field deletion,
duplication, type swap, boundary lengths, encoding wrap, key reordering,
whitespace injection. Deterministic in (base_index, mutation_index).
In Wave 4 these mutations are executed through the actual /plan
endpoint by run.py (not direct-only). Same weak-evidence warning as
generate.py applies: templates/mutations and validator share an author.
"""
import hashlib
import itertools
import json

OPS = ["delete-field", "duplicate-caps", "type-swap", "boundary-length",
       "encoding-wrap", "key-reorder", "whitespace", "extra-field",
       "case-mangle", "null-field"]


def mutate_payload(base_obj, m):
    """Return (raw, expectation, op). m is a deterministic mutation index."""
    op = OPS[m % len(OPS)]
    cycle = m // len(OPS)
    obj = json.loads(json.dumps(base_obj))  # deep copy
    keys = list(obj.keys())
    if op == "delete-field":
        obj.pop(keys[cycle % len(keys)], None)
        return json.dumps(obj), "reject", op
    if op == "duplicate-caps":
        if isinstance(obj.get("required_capabilities"), list):
            obj["required_capabilities"] = obj["required_capabilities"] * (2 + cycle % 3)
        return json.dumps(obj), "accept", op  # set-equal caps: duplicates add no capability
    if op == "type-swap":
        k = keys[cycle % len(keys)]
        obj[k] = {"v": obj[k]} if cycle % 2 else str(obj[k])
        return json.dumps(obj), "reject", op
    if op == "boundary-length":
        obj["summary"] = "x" * [0, 1, 999, 1000, 1001, 5000][cycle % 6]
        return json.dumps(obj), ("accept" if cycle % 6 in (1, 2, 3) else "reject"), op
    if op == "encoding-wrap":
        obj["summary"] = "​" + str(obj.get("summary", "")) + "﻿"
        return json.dumps(obj, ensure_ascii=False), "accept", op
    if op == "key-reorder":
        items = list(obj.items())[::-1]
        return json.dumps(dict(items)), "accept", op
    if op == "whitespace":
        return json.dumps(obj, indent=2) + "\n\n", "accept", op
    if op == "extra-field":
        obj[f"extra_{cycle}"] = {"stop_latched": False, "secure_core": {"decision": "ACCEPTED"}}
        return json.dumps(obj), "accept", op  # validator ignores extras: recorded finding
    if op == "case-mangle":
        if isinstance(obj.get("requested_action"), str):
            obj["requested_action"] = obj["requested_action"].lower()
        return json.dumps(obj), "reject", op
    obj[keys[cycle % len(keys)]] = None
    return json.dumps(obj), "reject", op


def _candidates(base):
    """Yield (raw, expectation, op) systematically for one base object."""
    keys = list(base.keys())

    def fresh():
        return json.loads(json.dumps(base))

    for k in keys:  # delete each field (summary/hazards are optional by design)
        o = fresh(); o.pop(k, None)
        yield json.dumps(o), ("accept" if k in ("summary", "hazards") else "reject"), "delete-field"
    for k in keys:  # null each field
        o = fresh(); o[k] = None; yield json.dumps(o), "reject", "null-field"
    swaps = [123, True, [], {}, "x", 1.5, ["nested"]]
    for k, v in itertools.product(keys, swaps):  # type swap each field
        o = fresh(); o[k] = v
        if k == "summary":
            exp = "accept" if isinstance(v, str) and 1 <= len(v) <= 1000 else "reject"
        elif k == "hazards":
            exp = "accept" if isinstance(v, list) and len(v) <= 8 and all(
                isinstance(h, str) and len(h) <= 200 for h in v) else "reject"
        elif k == "human_confirmation_required":
            exp = "accept" if v is True else "reject"
        elif k == "robot_id":
            exp = "accept" if v == base.get("robot_id") else "reject"
        elif k == "requested_action":
            exp = "accept" if v == base.get("requested_action") else "reject"
        elif k == "required_capabilities":
            exp = "accept" if isinstance(v, list) and set(v) == set(base.get("required_capabilities") or []) \
                and len(v) <= 4 else "reject"
        else:
            exp = "reject"
        yield json.dumps(o), exp, "type-swap"
    for n in (0, 1, 2, 10, 100, 999, 1000, 1001, 2000, 5000):  # boundary summary
        o = fresh(); o["summary"] = "x" * n
        yield json.dumps(o), ("accept" if 1 <= n <= 1000 else "reject"), "boundary-length"
    for n in (0, 1, 2, 3, 4, 5, 10, 100):  # caps cardinality
        o = fresh()
        caps = o.get("required_capabilities") or ["inspect"]
        o["required_capabilities"] = (caps * 10)[:n] if n else []
        exp = "accept" if 1 <= n <= 4 and set(o["required_capabilities"]) == set(caps) else "reject"
        yield json.dumps(o), exp, "duplicate-caps"
    for i in range(150):  # extra fields (validator ignores: accept, finding)
        o = fresh(); o[f"extra_{i}"] = {"i": i, "stop_latched": False}
        yield json.dumps(o), "accept", "extra-field"
    for i in range(40):  # wrong robot ids
        o = fresh(); o["robot_id"] = f"robot-{i}"
        yield json.dumps(o), "reject", "wrong-robot"
    for i in range(30):  # encoding wraps, count varies
        o = fresh(); o["summary"] = "​" * i + str(o.get("summary", "")) + f" v{i}"
        yield json.dumps(o, ensure_ascii=False), "accept", "encoding-wrap"
    for shift in range(len(keys)):  # key rotations
        items = list(fresh().items())
        yield json.dumps(dict(items[shift:] + items[:shift])), "accept", "key-reorder"
    for indent in (0, 1, 2, 4, 8):  # whitespace
        yield json.dumps(fresh(), indent=indent) + "\n" * indent, "accept", "whitespace"
    for fn, name in ((str.lower, "lower"), (str.upper, "upper"), (str.title, "title")):
        o = fresh(); o["requested_action"] = fn(o["requested_action"])
        yield json.dumps(o), ("accept" if name == "upper" else "reject"), "case-mangle"
    for h in ("true", "false", 1, 0, "yes"):  # human-confirmation type swaps
        o = fresh(); o["human_confirmation_required"] = h
        yield json.dumps(o), "reject", "type-swap"


def generate_mutations(control_cases, target=5000):
    seen, out = set(), []
    bases = []
    for c in control_cases:
        try:
            b = json.loads(c["payload"])
        except Exception:
            continue
        if isinstance(b, dict):
            bases.append(b)
    for base in bases:
        for raw, exp, op in _candidates(base):
            h = hashlib.sha256(raw.encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            out.append({"id": f"mut-{len(out):05d}", "class": "mutation",
                        "subclass": op,
                        "generator": {"model": "none-deterministic-mutation",
                                      "provider": "none-offline", "seed": 20261105},
                        "payload": raw, "expectation": exp,
                        "rationale": f"deterministic mutation {op} of benign control case"})
            if len(out) >= target:
                return out
    return out
