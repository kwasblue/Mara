# schema/telemetry/_ctrl_observers.py
"""Control observer state telemetry section (variable length)."""

import struct
from .core import TelemetrySectionDef

_OBSERVER_HDR_FMT = struct.Struct("<BBB")  # slot, enabled, num_states
_FLOAT_FMT = struct.Struct("<f")


def _parse_ctrl_observers(body: bytes, ts_ms: int) -> dict:
    """Parse variable-length control observers section."""
    if len(body) < 1:
        return None

    slot_count = body[0]
    observers = []
    pos = 1

    for _ in range(slot_count):
        if pos + _OBSERVER_HDR_FMT.size > len(body):
            break

        slot, enabled, num_states = _OBSERVER_HDR_FMT.unpack_from(body, pos)
        pos += _OBSERVER_HDR_FMT.size

        states = []
        for _ in range(num_states):
            if pos + _FLOAT_FMT.size > len(body):
                break
            (x,) = _FLOAT_FMT.unpack_from(body, pos)
            states.append(x)
            pos += _FLOAT_FMT.size

        observers.append({
            "slot": slot,
            "enabled": bool(enabled),
            "update_count": 0,
            "states": states,
        })

    return {"ts_ms": ts_ms, "observers": observers}


SECTION = TelemetrySectionDef(
    name="TELEM_CTRL_OBSERVERS",
    section_id=0x11,
    description="Observer state estimates",
    variable_length=True,
    custom_parser=_parse_ctrl_observers,
)
