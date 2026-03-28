# schema/telemetry/_ctrl_slots.py
"""Control slot status telemetry section (variable length)."""

import struct
from .core import TelemetrySectionDef

_SLOT_FMT = struct.Struct("<BBBI")  # slot, enabled, ok, run_count


def _parse_ctrl_slots(body: bytes, ts_ms: int) -> dict:
    """Parse variable-length control slots section."""
    if len(body) < 1:
        return None

    slot_count = body[0]
    slots = []
    pos = 1

    for _ in range(slot_count):
        if pos + _SLOT_FMT.size > len(body):
            break

        slot, enabled, ok, run_count = _SLOT_FMT.unpack_from(body, pos)
        pos += _SLOT_FMT.size

        slots.append({
            "slot": slot,
            "enabled": bool(enabled),
            "ok": bool(ok),
            "run_count": run_count,
        })

    return {"ts_ms": ts_ms, "slots": slots}


SECTION = TelemetrySectionDef(
    name="TELEM_CTRL_SLOTS",
    section_id=0x12,
    description="Control slot status",
    variable_length=True,
    custom_parser=_parse_ctrl_slots,
)
