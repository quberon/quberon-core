"""Bounded Meta-compatible planning adapter.

The provider is advisory only. It returns data that must pass the deterministic
validator in app.main before any simulated task is even proposed as allowed.
Credentials are read from environment variables on the server only.
"""
import json
import os
from typing import Any, Dict

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


class LiveMetaProvider:
    """OpenAI-compatible chat endpoint adapter, configured only by env.

    Expected env: META_API_URL, META_API_KEY, META_MODEL. This class never logs
    the key and imposes a short timeout. It is not constructed unless
    META_MODE=live and all settings are present.
    """

    name = "live"

    def __init__(self):
        self.url = os.environ.get("META_API_URL", "")
        self.key = os.environ.get("META_API_KEY", "")
        self.model = os.environ.get("META_MODEL", "")
        if not (self.url and self.key and self.model):
            raise MetaProviderError("Meta live mode is not fully configured")

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
                data = json.loads(content)
        except Exception as exc:  # provider failure must never affect STOP
            raise MetaProviderError(f"Meta provider failed: {type(exc).__name__}") from exc
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
        return LiveMetaProvider()
    return MockMetaProvider()
