import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conformance.quberon_adapter import make_quberon_adapter


@pytest.fixture(autouse=True)
def _dev_secure_core_mode(monkeypatch):
    # Ephemeral secure-core keys require explicit dev mode (as in tests/).
    monkeypatch.setenv("QUBERON_SECURE_CORE_MODE", "development")


@pytest.fixture()
def adapter(tmp_path):
    return make_quberon_adapter(tmp_path)


@pytest.fixture()
def adapter_no_core(tmp_path):
    """Adapter with the authorizing core explicitly unavailable (DEGRADED)."""
    return make_quberon_adapter(tmp_path / "nocore", secure_core=None)


@pytest.fixture()
def adapter_failing(tmp_path):
    """Adapter whose underlying robot adapter reports failure (STATE/DEGRADED)."""
    return make_quberon_adapter(tmp_path / "failing", adapter_fail=True)


@pytest.fixture()
def adapter_persistence_degraded(tmp_path):
    """Adapter after neutral persistence-failure injection (QIP-DEG-03)."""
    a = make_quberon_adapter(tmp_path / "persistfail")
    a.inject_persistence_failure()
    return a


@pytest.fixture()
def adapter_planner_saturated(tmp_path):
    """Adapter after neutral non-intervention saturation (QIP-INT-06)."""
    a = make_quberon_adapter(tmp_path / "plannersat")
    a.saturate_non_intervention_traffic()
    return a


@pytest.fixture()
def adapter_refusing_core(tmp_path):
    """Adapter after neutral reachable-refusal injection (QIP-DEG-03)."""
    a = make_quberon_adapter(tmp_path / "refusing", secure_core=None)
    a.inject_secure_core_refusal()
    return a
