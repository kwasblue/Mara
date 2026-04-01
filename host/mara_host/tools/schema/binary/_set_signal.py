# schema/binary/_set_signal.py
"""SET_SIGNAL binary command definition."""

from .core import BinaryCommandDef, BinaryFieldDef

COMMAND = BinaryCommandDef(
    name="SET_SIGNAL",
    opcode=0x11,
    description="Set signal: id(u16), value(f32)",
    json_cmd="CMD_CTRL_SIGNAL_SET",
    payload=(
        BinaryFieldDef.u16("id", "Signal ID"),
        BinaryFieldDef.f32("value", "Signal value"),
    ),
)
