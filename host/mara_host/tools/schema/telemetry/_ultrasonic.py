# schema/telemetry/_ultrasonic.py
"""Ultrasonic sensor telemetry section definition."""

from .core import TelemetrySectionDef, FieldDef

SECTION = TelemetrySectionDef(
    name="TELEM_ULTRASONIC",
    section_id=0x02,
    description="Ultrasonic distance sensor",
    fields=(
        FieldDef.uint8("sensor_id"),
        FieldDef.uint8("attached"),
        FieldDef.uint8("ok"),
        FieldDef.uint16("dist_mm", scale=0.1, description="Distance in cm"),
    ),
)
