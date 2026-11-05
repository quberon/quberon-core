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
