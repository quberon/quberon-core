"""Bounded Meta-compatible planning adapter.

The provider is advisory only. It returns data that must pass the deterministic
validator in app.main before any simulated task is even proposed as allowed.
Credentials are read from environment variables on the server only.
"""
import json
import os
from typing import Any, Dict
from urllib.parse import urlparse

ALLOWED_ACTIONS = {"SIMULATE_INSPECTION", "SIMULATE_STATUS_CHECK"}
ALLOWED_CAPABILITIES = {"inspect", "status"}


class MetaProviderError(RuntimeError):
    pass


class MockMetaProvider:
    name = "mock"

    def propose(self, robot_id: str, text: str) -> Dict[str, Any]:
        lowered = text.lower()
        if "status" in lowered or "health" in lowered:
            action, caps = "SIMULATE_STATUS_CHECK", ["status"]
        else:
            action, caps = "SIMULATE_INSPECTION", ["inspect"]
        return {
            "summary": f"Mock plan proposal for: {text[:160]}",
            "robot_id": robot_id,
            "requested_action": action,
            "required_capabilities": caps,
            "hazards": ["Simulated environment only", "No physical robot is connected"],
            "human_confirmation_required": True,
            "provider": "mock",
        }


def _redact_secret(value: Any, secret: str) -> Any:
    """Recursively remove the credential from untrusted provider output."""
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, "[REDACTED]")
    if isinstance(value, list):
        return [_redact_secret(v, secret) for v in value]
    if isinstance(value, dict):
        return {_redact_secret(k, secret): _redact_secret(v, secret) for k, v in value.items()}
    return value


class LiveMetaProvider:
    """OpenAI-compatible chat endpoint adapter, configured only by env.

    Expected env: META_API_URL, META_API_KEY, META_MODEL. This class never logs
    the key and imposes a short timeout. It is not constructed unless
    META_MODE=live and all settings are present.
    """

    name = "live"

    def __init__(self):
        self.url = os.environ.get("META_API_URL", "").strip()
        self.key = os.environ.get("META_API_KEY", "")
        self.model = os.environ.get("META_MODEL", "").strip()
        if not (self.url and self.key and self.model):
            raise MetaProviderError("Meta live mode is not fully configured")
        parsed = urlparse(self.url)
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not local_http:
            raise MetaProviderError("Meta live endpoint must use HTTPS (HTTP only for localhost)")
        if parsed.username or parsed.password or parsed.fragment:
            raise MetaProviderError("Meta live endpoint must not contain credentials or a fragment")
        self.endpoint_host = parsed.hostname or ""

    def propose(self, robot_id: str, text: str) -> Dict[str, Any]:
        import httpx

        prompt = (
            "Return only JSON with keys summary, robot_id, requested_action, "
            "required_capabilities, hazards, human_confirmation_required. "
            "requested_action must be SIMULATE_INSPECTION or SIMULATE_STATUS_CHECK. "
            f"robot_id must be {robot_id}. User request: {text[:1000]}"
        )
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.post(
                    self.url,
                    headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,
                        "max_tokens": 300,
                    },
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                if not isinstance(content, str) or len(content) > 20000:
                    raise ValueError("provider response content is not bounded text")
                stripped = content.strip()
                if stripped.startswith("```"):
                    stripped = stripped.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                data = json.loads(stripped)
                if not isinstance(data, dict):
                    raise ValueError("provider response is not a JSON object")
        except Exception as exc:  # provider failure must never affect STOP
            # Only the exception type is exposed: messages from HTTP stacks
            # may embed the request (and its Authorization header/key).
            raise MetaProviderError(f"Meta provider failed: {type(exc).__name__}") from None
        data = _redact_secret(data, self.key)
        # Advisory-boundary hardening: drop any smuggled fields (latch,
        # capability grants, adapter/motion commands) instead of passing
        # untrusted provider output through verbatim.
        allowed_keys = {"summary", "robot_id", "requested_action", "required_capabilities", "hazards", "human_confirmation_required"}
        data = {k: v for k, v in data.items() if k in allowed_keys}
        data["provider"] = "live"
        return data


ACTION_CAPABILITIES = {
    "SIMULATE_INSPECTION": {"inspect"},
    "SIMULATE_STATUS_CHECK": {"status"},
}


def validate_plan(plan: Any, robot_id: str, stop_latched: bool) -> Dict[str, Any]:
    # Type-safe (fix C): provider output is untrusted; never raise on bad types.
    errors = []
    if not isinstance(plan, dict):
        return {
            "allowed_as_proposal": False,
            "errors": ["plan is not an object"],
            "latch_blocks_task": bool(stop_latched),
            "note": "Validation never resets the latch, grants a session capability, or commands hardware.",
        }
    if plan.get("robot_id") != robot_id:
        errors.append("robot mismatch")
    action = plan.get("requested_action")
    if not isinstance(action, str) or action not in ALLOWED_ACTIONS:
        errors.append("action not allow-listed")
        action = None
    caps = plan.get("required_capabilities")
    if (
        not isinstance(caps, list)
        or not caps
        or len(caps) > 4
        or any(not isinstance(c, str) or len(c) > 32 for c in caps)
        or not set(caps).issubset(ALLOWED_CAPABILITIES)
    ):
        errors.append("capability not allow-listed")
    elif action is not None and set(caps) != ACTION_CAPABILITIES[action]:
        errors.append("capabilities do not match requested action")
    if plan.get("human_confirmation_required") is not True:
        errors.append("human confirmation must be required")
    # Optional descriptive fields, when present, must be bounded text;
    # plans without them remain valid for the pre-existing validator tests.
    if "summary" in plan and (not isinstance(plan["summary"], str) or not plan["summary"] or len(plan["summary"]) > 1000):
        errors.append("summary is not bounded text")
    if "hazards" in plan and (
        not isinstance(plan["hazards"], list) or len(plan["hazards"]) > 8
        or any(not isinstance(h, str) or len(h) > 200 for h in plan["hazards"])
    ):
        errors.append("hazards are not bounded text")
    allowed = not errors and not stop_latched
    return {
        "allowed_as_proposal": allowed,
        "errors": errors,
        "latch_blocks_task": bool(stop_latched),
        "note": "Validation never resets the latch, grants a session capability, or commands hardware.",
    }


class UnavailableMetaProvider:
    """Live mode requested but not fully configured (fix E): app stays up,
    planner reports UNAVAILABLE instead of silently pretending to be mock."""

    name = "unavailable"

    def propose(self, robot_id: str, text: str) -> Dict[str, Any]:
        raise MetaProviderError("Meta live mode is not fully configured")


def get_provider():
    if os.environ.get("META_MODE", "mock").lower() == "live":
        try:
            return LiveMetaProvider()
        except MetaProviderError:
            # Never silently fall back to mock in live mode: report
            # unavailable so callers cannot mistake mock for live.
            return UnavailableMetaProvider()
    return MockMetaProvider()
