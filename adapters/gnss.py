"""Optional read-only GNSS state vocabulary.

No Here+ device was observed during inventory, so this module only defines the
state contract and a no-device adapter. It does not open arbitrary serial ports.
"""
from dataclasses import dataclass


@dataclass
class GnssStatus:
    state: str
    fix_type: str = "none"
    satellites: int | None = None
    age_seconds: float | None = None
    accuracy_m: float | None = None


class NoDeviceGnss:
    def status(self) -> GnssStatus:
        return GnssStatus(state="NO_DEVICE")
