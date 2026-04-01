# schema/can/_set_signal.py
"""SET_SIGNAL CAN message definition."""

from .core import CanMessageDef, CanFieldDef

MESSAGE = CanMessageDef(
    name="SET_SIGNAL",
    base_id="SET_SIGNAL_BASE",
    direction="host->mcu",
    description="Set signal value (CAN-native, 8 bytes)",
    struct=(
        CanFieldDef.u16("signal_id"),
        CanFieldDef.f32("value"),
        CanFieldDef.u16("reserved"),
    ),
)
