# schema/can/_heartbeat.py
"""HEARTBEAT CAN message definition."""

from .core import CanMessageDef, CanFieldDef

MESSAGE = CanMessageDef(
    name="HEARTBEAT",
    base_id="HEARTBEAT_BASE",
    direction="both",
    description="Node heartbeat (CAN-native, 8 bytes)",
    struct=(
        CanFieldDef.u32("uptime_ms"),
        CanFieldDef.u8("state"),
        CanFieldDef.u8("load_pct"),
        CanFieldDef.u16("errors"),
    ),
)
