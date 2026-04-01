# schema/binary/_set_vel.py
"""SET_VEL binary command definition."""

from .core import BinaryCommandDef, BinaryFieldDef

COMMAND = BinaryCommandDef(
    name="SET_VEL",
    opcode=0x10,
    description="Set velocity: vx(f32), omega(f32)",
    json_cmd="CMD_SET_VEL",
    payload=(
        BinaryFieldDef.f32("vx", "Linear velocity"),
        BinaryFieldDef.f32("omega", "Angular velocity"),
    ),
)
