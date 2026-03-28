# schema/telemetry/_encoder.py
"""Encoder telemetry section definition."""

from .core import TelemetrySectionDef, FieldDef

SECTION = TelemetrySectionDef(
    name="TELEM_ENCODER0",
    section_id=0x04,
    description="Encoder 0 tick count",
    fields=(
        FieldDef.int32("ticks", description="Encoder tick count"),
    ),
)
