# schema/telemetry/_stepper.py
"""Stepper motor telemetry section definition."""

from .core import TelemetrySectionDef, FieldDef

SECTION = TelemetrySectionDef(
    name="TELEM_STEPPER0",
    section_id=0x05,
    description="Stepper motor 0 state",
    fields=(
        FieldDef.int8("motor_id"),
        FieldDef.uint8("attached"),
        FieldDef.uint8("enabled"),
        FieldDef.uint8("moving"),
        FieldDef.uint8("dir_forward"),
        FieldDef.int32("last_cmd_steps", description="Last commanded steps"),
        FieldDef.int16("speed_centi", scale=0.01, description="Speed"),
    ),
)
