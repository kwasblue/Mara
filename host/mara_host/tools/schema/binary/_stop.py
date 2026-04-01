# schema/binary/_stop.py
"""STOP binary command definition."""

from .core import BinaryCommandDef

COMMAND = BinaryCommandDef(
    name="STOP",
    opcode=0x21,
    description="Stop (no payload)",
    json_cmd="CMD_STOP",
    payload=(),
)
