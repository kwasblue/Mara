# schema/can/_status.py
"""STATUS CAN message definition."""

from .core import CanMessageDef, CanFieldDef

MESSAGE = CanMessageDef(
    name="STATUS",
    base_id="STATUS_BASE",
    direction="mcu->host",
    description="Node status (CAN-native, 8 bytes)",
    struct=(
        CanFieldDef.u8("state"),
        CanFieldDef.u8("flags"),  # Bitfield: armed, active, estopped, error
        CanFieldDef.u16("voltage_mv"),
        CanFieldDef.u16("temp_c10", scale=10.0, unit="C"),
        CanFieldDef.u16("seq"),
    ),
)
