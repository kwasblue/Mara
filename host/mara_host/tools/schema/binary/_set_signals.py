# schema/binary/_set_signals.py
"""SET_SIGNALS binary command definition (variable-length batch)."""

from .core import BinaryCommandDef, BinaryFieldDef

COMMAND = BinaryCommandDef(
    name="SET_SIGNALS",
    opcode=0x12,
    description="Set multiple signals: count(u8), [id(u16), value(f32)]*",
    json_cmd=None,  # Batch-only, no JSON equivalent
    payload=(
        BinaryFieldDef.u8("count", "Number of signals"),
    ),
    variable_length=True,
    variable_item=(
        BinaryFieldDef.u16("id", "Signal ID"),
        BinaryFieldDef.f32("value", "Signal value"),
    ),
)
