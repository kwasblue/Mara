# schema/telemetry/_ctrl_signals.py
"""Control signal bus telemetry section (variable length)."""

import struct
from .core import TelemetrySectionDef

_COUNT_FMT = struct.Struct("<H")  # uint16 count
_SIGNAL_FMT = struct.Struct("<Hfi")  # id, value, ts_ms


def _parse_ctrl_signals(body: bytes, ts_ms: int) -> dict:
    """Parse variable-length control signals section."""
    if len(body) < _COUNT_FMT.size:
        return None

    count = _COUNT_FMT.unpack_from(body, 0)[0]
    signals = []
    pos = 2

    for _ in range(count):
        if pos + _SIGNAL_FMT.size > len(body):
            break

        sig_id, value, sig_ts = _SIGNAL_FMT.unpack_from(body, pos)
        pos += _SIGNAL_FMT.size

        signals.append({
            "id": sig_id,
            "name": "",
            "value": value,
            "ts_ms": sig_ts,
        })

    return {"ts_ms": ts_ms, "signals": signals, "count": count}


SECTION = TelemetrySectionDef(
    name="TELEM_CTRL_SIGNALS",
    section_id=0x10,
    description="Control signal bus values",
    variable_length=True,
    custom_parser=_parse_ctrl_signals,
)
