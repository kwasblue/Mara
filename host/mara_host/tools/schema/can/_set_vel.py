# schema/can/_set_vel.py
"""SET_VEL CAN message definition."""

from .core import CanMessageDef, CanFieldDef

MESSAGE = CanMessageDef(
    name="SET_VEL",
    base_id="SET_VEL_BASE",
    direction="host->mcu",
    description="Set velocity command (CAN-native, 8 bytes)",
    struct=(
        CanFieldDef.i16("vx_mm_s", scale=1000.0, unit="m/s"),
        CanFieldDef.i16("omega_mrad_s", scale=1000.0, unit="rad/s"),
        CanFieldDef.u16("flags"),
        CanFieldDef.u16("seq"),
    ),
)
