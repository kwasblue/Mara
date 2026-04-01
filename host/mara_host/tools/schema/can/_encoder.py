# schema/can/_encoder.py
"""ENCODER CAN message definition."""

from .core import CanMessageDef, CanFieldDef

MESSAGE = CanMessageDef(
    name="ENCODER",
    base_id="ENCODER_BASE",
    direction="mcu->host",
    description="Encoder counts and velocity (CAN-native, 8 bytes)",
    struct=(
        CanFieldDef.i32("counts"),
        CanFieldDef.i16("velocity", unit="counts/s"),
        CanFieldDef.u16("timestamp", unit="ms"),
    ),
)
