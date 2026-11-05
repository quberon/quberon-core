#!/usr/bin/env python3
"""One-shot live Meta planning evidence command (Lane C).

Makes EXACTLY ONE LiveMetaProvider.propose() call when META_API_URL,
META_API_KEY and META_MODEL are present (no retries), validates the
returned proposal with the deterministic validator, and writes a
sanitized evidence file. When credentials are absent or the call fails,
it still writes evidence documenting the failure honestly and exits
non-zero -- no silent failure.

Credentials are read only from the environment. They are never printed,
logged, or written: every string written is passed through sanitize(),
which removes the exact credential value and Authorization/Bearer
patterns. Usage:

    META_MODE=live META_API_URL=... META_API_KEY=... META_MODEL=... \
        .venv/bin/python scripts/meta_live_evidence.py [--output PATH]
"""
import argparse
import contextlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.meta import LiveMetaProvider, MetaProviderError, validate_plan  # noqa: E402

REQUIRED_ENV = ("META_API_URL", "META_API_KEY", "META_MODEL")
PROMPT = "Plan a simulated status check for the simulated robot. Simulated environment only; no physical robot is connected."
DEFAULT_ROBOT_ID = "quberon-demo-001"


def sanitize(text, secret=""):
    if text is None:
        text = ""
    text = str(text)
    if secret:
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(?i)(authorization\s*:\s*bearer\s+)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-~+/=]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)\S+", r"\1[REDACTED]", text)
    return text[:4000]


def _httpx_available():
    try:
        return importlib.util.find_spec("httpx") is not None
    except (ImportError, ValueError):
        return False


@contextlib.contextmanager
def _provider_environ(environ):
    """Make an explicitly supplied ``environ`` win over the process env.

    LiveMetaProvider reads os.environ at construction (URL, model and the
    key placed in the Authorization header). Previously run(environ=...)
    checked/redacted that mapping while the provider silently used the
    process environment, so a stale process value could select a different
    endpoint and send a different Authorization header than the evidence
    claimed to configure. Applying the mapping for construction *and* the
    single propose() call fixes that precedence/header mismatch; the
    process environment is restored afterwards, even on failure.
    """
    if environ is None or environ is os.environ:
        yield
        return
    keys = REQUIRED_ENV + ("META_MODE", "ROBOT_ID")
    saved = {k: os.environ.get(k) for k in keys}
    try:
        for key in keys:
            value = environ.get(key)
            if value:
                os.environ[key] = str(value)
            else:
                os.environ.pop(key, None)
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _tested_commit():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def run(output_path, environ=None, provider_factory=None, robot_id=None, now=None, commit=None,
        httpx_available=None):
    environ = os.environ if environ is None else environ
    secret = environ.get("META_API_KEY", "")
    robot_id = robot_id or environ.get("ROBOT_ID", "") or DEFAULT_ROBOT_ID
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    commit = commit or _tested_commit()
    model = (environ.get("META_MODEL", "") or "").strip() or "(not configured)"
    provider_label = "live"
    missing = [name for name in REQUIRED_ENV if not (environ.get(name, "") or "").strip()]

    verdict = None
    response_text = "(no provider call was made)"
    failure = ""
    calls = 0
    success = False

    if missing:
        failure = "Blocked: missing required environment variable(s): " + ", ".join(missing) + ". No provider call was made."
    elif not (_httpx_available() if httpx_available is None else httpx_available):
        # LiveMetaProvider imports httpx inside propose(), before its own
        # error wrapping; without a preflight that surfaces as a bare
        # ImportError and was miscounted as a call. Block honestly, 0 calls.
        failure = ("Blocked: missing Python dependency 'httpx' required for the live provider call. "
                   "Install requirements.txt in the selected interpreter. "
                   "No provider call was made and no Authorization header was sent.")
    else:
        factory = provider_factory or LiveMetaProvider
        try:
            with _provider_environ(environ):
                provider = factory()
                provider_label = f"live (endpoint host: {getattr(provider, 'endpoint_host', 'unknown')})"
                model = getattr(provider, "model", model) or model
                calls += 1  # exactly one planning call; no retries anywhere
                plan = provider.propose(robot_id, PROMPT)
            response_text = json.dumps(plan, indent=2, sort_keys=True, default=str)
            verdict = validate_plan(plan, robot_id, stop_latched=False)
            success = bool(verdict.get("allowed_as_proposal"))
            if not success:
                failure = "Validator rejected the proposal: " + json.dumps(verdict.get("errors", []))
        except Exception as exc:  # verbatim, but sanitized below
            failure = f"{type(exc).__name__}: {exc}"

    verdict_text = json.dumps(verdict, indent=2, sort_keys=True) if verdict is not None else "(not run: no validated proposal)"
    status = "SUCCESS" if success else "BLOCKED / FAILED"
    lines = [
        "# Live Meta inference — evidence (Lane C one-shot)",
        "",
        f"Status: {status}",
        "",
        f"- Provider: {sanitize(provider_label, secret)}",
        f"- Exact model ID: {sanitize(model, secret)}",
        f"- UTC timestamp: {timestamp}",
        f"- Tested commit: {commit} (HEAD at evidence-run time; the commit containing this file may be a later evidence-only commit)",
        f"- Robot ID: {sanitize(robot_id, secret)}",
        f"- Provider planning calls made: {calls} (exactly one when configured; zero when blocked)",
        "- Planner boundary: advisory only. This call cannot reset the latch, grant a capability, invoke an adapter, or permit motion (see named tests in tests/test_meta_live.py).",
        "",
        "## Prompt",
        "",
        sanitize(PROMPT, secret),
        "",
        "## Redacted response",
        "",
        "```json",
        sanitize(response_text, secret),
        "```",
        "",
        "## Validator verdict",
        "",
        "```json",
        sanitize(verdict_text, secret),
        "```",
        "",
        "## Failure (verbatim, sanitized)",
        "",
        sanitize(failure, secret) if failure else "(none)",
        "",
        "## Claim boundary",
        "",
        ("A single live planning call succeeded and passed the deterministic validator on the date above. "
         "This verifies only that one advisory proposal; it does not verify physical control, safety, or any motion path."
         if success else
         "Live runtime Meta inference is NOT verified. Runtime Meta planning remains on warning status in README.md. "
         "Do not claim runtime Meta inference works from this file."),
        "",
    ]
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    # Console output is sanitized and contains no credential values.
    print(f"meta-live evidence: {status}; calls={calls}; wrote {out}")
    if failure:
        print(f"meta-live failure: {sanitize(failure, secret)}")
    return 0 if success else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="docs/evidence/meta-live.md")
    parser.add_argument("--robot-id", default=None)
    args = parser.parse_args(argv)
    return run(args.output, robot_id=args.robot_id)


if __name__ == "__main__":
    raise SystemExit(main())
