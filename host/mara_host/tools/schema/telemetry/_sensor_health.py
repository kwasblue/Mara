# schema/telemetry/_sensor_health.py
"""Sensor health telemetry section (variable length)."""

import struct
from .core import TelemetrySectionDef

_ENTRY_FMT = struct.Struct("<BBBB")  # kind, sensor_id, flags, detail

_SENSOR_KIND_NAMES = {
    1: "imu",
    2: "ultrasonic",
    3: "lidar",
    4: "encoder",
}


def _parse_sensor_health(body: bytes, ts_ms: int) -> dict:
    """Parse variable-length sensor health section."""
    if len(body) < 1:
        return None

    count = body[0]
    sensors = []
    pos = 1

    for _ in range(count):
        if pos + _ENTRY_FMT.size > len(body):
            break

        kind_code, sensor_id, flags, detail = _ENTRY_FMT.unpack_from(body, pos)
        pos += _ENTRY_FMT.size

        sensors.append({
            "kind": _SENSOR_KIND_NAMES.get(kind_code, f"kind_{kind_code}"),
            "sensor_id": int(sensor_id),
            "present": bool(flags & 0x01),
            "healthy": bool(flags & 0x02),
            "degraded": bool(flags & 0x04),
            "stale": bool(flags & 0x08),
            "detail": int(detail),
            "flags": int(flags),
        })

    return {"ts_ms": ts_ms, "sensors": sensors}


SECTION = TelemetrySectionDef(
    name="TELEM_SENSOR_HEALTH",
    section_id=0x08,
    description="Compact sensor health and degraded-state summary",
    variable_length=True,
    custom_parser=_parse_sensor_health,
)
