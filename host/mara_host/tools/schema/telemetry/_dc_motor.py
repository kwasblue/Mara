# schema/telemetry/_dc_motor.py
"""DC motor telemetry section definition."""

from .core import TelemetrySectionDef, FieldDef

SECTION = TelemetrySectionDef(
    name="TELEM_DC_MOTOR0",
    section_id=0x06,
    description="DC motor 0 state",
    fields=(
        FieldDef.uint8("attached"),
        FieldDef.int16("speed_centi", scale=0.01, description="Speed (-1.0 to 1.0)"),
    ),
)
