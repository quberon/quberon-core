"""Read-only GNSS state vocabulary + a checksum-validated NMEA parser.

The Here+ (u-blox) receiver was found on USB as /dev/ttyACM0 streaming NMEA.
This module only parses already-received text; opening the port and passive
listening live in scripts/gnss_reader.py. No UBX/binary frames are ever sent.
"""
from dataclasses import dataclass


@dataclass
class GnssStatus:
    state: str  # NO_DEVICE | NO_DATA | NO_FIX | FIX_NO_RTK | RTK_FLOAT | RTK_FIXED | STALE
    fix_type: str = "none"
    satellites: int | None = None
    age_seconds: float | None = None
    accuracy_m: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    satellites_in_view: int | None = None
    utc: str | None = None


class NoDeviceGnss:
    def status(self) -> GnssStatus:
        return GnssStatus(state="NO_DEVICE")


def _checksum_ok(sentence: str) -> bool:
    sentence = sentence.strip()
    if not sentence.startswith("$") or "*" not in sentence:
        return False
    body, _, tail = sentence[1:].partition("*")
    if len(tail) < 2:
        return False
    try:
        expected = int(tail[:2], 16)
    except ValueError:
        return False
    actual = 0
    for ch in body:
        actual ^= ord(ch)
    return actual == expected


def _dm_to_deg(value: str, hemi: str) -> float | None:
    """NMEA ddmm.mmmm / dddmm.mmmm -> signed decimal degrees."""
    if not value or "." not in value:
        return None
    try:
        raw = float(value)
    except ValueError:
        return None
    degrees = int(raw // 100)
    minutes = raw - degrees * 100
    result = degrees + minutes / 60.0
    if hemi in ("S", "W"):
        result = -result
    return result


_QUALITY = {
    "0": ("NO_FIX", "none"),
    "1": ("FIX_NO_RTK", "gps"),
    "2": ("FIX_NO_RTK", "dgps"),
    "4": ("RTK_FIXED", "rtk_fixed"),
    "5": ("RTK_FLOAT", "rtk_float"),
}


def parse_sentence(sentence: str, status: GnssStatus) -> bool:
    """Fold one NMEA sentence into status. Returns True if checksum-valid."""
    if not _checksum_ok(sentence):
        return False
    parts = sentence.strip()[1:].split("*")[0].split(",")
    talker_type = parts[0]
    if talker_type.endswith("GGA") and len(parts) >= 10:
        quality = parts[6]
        state, fix_type = _QUALITY.get(quality, ("NO_FIX", "none"))
        status.state = state
        status.fix_type = fix_type
        try:
            status.satellites = int(parts[7]) if parts[7] else None
        except ValueError:
            status.satellites = None
        try:
            status.accuracy_m = float(parts[8]) if parts[8] else None  # HDOP, coarse proxy only
        except ValueError:
            status.accuracy_m = None
        status.utc = parts[1] or status.utc
        if state != "NO_FIX":
            status.latitude = _dm_to_deg(parts[2], parts[3])
            status.longitude = _dm_to_deg(parts[4], parts[5])
        else:
            status.latitude = None
            status.longitude = None
    elif talker_type.endswith("RMC") and len(parts) >= 10:
        status.utc = parts[1] or status.utc
        if parts[2] == "A":
            status.latitude = _dm_to_deg(parts[3], parts[4])
            status.longitude = _dm_to_deg(parts[5], parts[6])
        elif status.state != "NO_FIX":
            status.state = "NO_FIX"
    elif talker_type.endswith("GSV") and len(parts) >= 4:
        try:
            status.satellites_in_view = int(parts[3]) if parts[3] else status.satellites_in_view
        except ValueError:
            pass
    return True
