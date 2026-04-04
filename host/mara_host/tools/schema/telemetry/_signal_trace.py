# schema/telemetry/_signal_trace.py
"""Signal trace subscription telemetry section (variable length)."""

import struct
from .core import TelemetrySectionDef

_SIGNAL_FMT = struct.Struct("<Hfi")  # id(u16), value(f32), ts_ms(i32)


def _parse_signal_trace(body: bytes, ts_ms: int) -> dict:
    """Parse variable-length signal trace section.

    Format: count(u8) rate_hz(u8) [id(u16) value(f32) ts_ms(u32)]...
    """
    if len(body) < 2:
        return None

    count = body[0]
    rate_hz = body[1]
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

    return {"ts_ms": ts_ms, "rate_hz": rate_hz, "signals": signals, "count": len(signals)}


SECTION = TelemetrySectionDef(
    name="TELEM_SIGNAL_TRACE",
    section_id=0x14,
    description="Signal trace subscription (up to 16 signals)",
    variable_length=True,
    custom_parser=_parse_signal_trace,
)
