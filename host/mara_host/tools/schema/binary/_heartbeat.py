# schema/binary/_heartbeat.py
"""HEARTBEAT binary command definition."""

from .core import BinaryCommandDef

COMMAND = BinaryCommandDef(
    name="HEARTBEAT",
    opcode=0x20,
    description="Heartbeat (no payload)",
    json_cmd="CMD_HEARTBEAT",
    payload=(),
)
