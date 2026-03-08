# schema/binary.py
"""Binary command definitions for high-rate streaming."""

from typing import Dict, Any

# Binary commands are compact fixed-format messages for control loops.
# Use JSON commands for setup/config, binary for real-time streaming (50+ Hz).

BINARY_COMMANDS: Dict[str, Dict[str, Any]] = {
    "SET_VEL": {
        "opcode": 0x10,
        "json_cmd": "CMD_SET_VEL",  # Maps to JSON equivalent
        "description": "Set velocity: vx(f32), omega(f32)",
        "payload": [
            {"name": "vx", "type": "f32"},
            {"name": "omega", "type": "f32"},
        ],
    },
    "SET_SIGNAL": {
        "opcode": 0x11,
        "json_cmd": "CMD_CTRL_SIGNAL_SET",
        "description": "Set signal: id(u16), value(f32)",
        "payload": [
            {"name": "id", "type": "u16"},
            {"name": "value", "type": "f32"},
        ],
    },
    "SET_SIGNALS": {
        "opcode": 0x12,
        "json_cmd": None,  # Batch-only, no JSON equivalent
        "description": "Set multiple signals: count(u8), [id(u16), value(f32)]*",
        "payload": [
            {"name": "count", "type": "u8"},
        ],
        "variable_length": True,  # [id:u16, value:f32] * count follows
        "variable_item": [
            {"name": "id", "type": "u16"},
            {"name": "value", "type": "f32"},
        ],
    },
    "HEARTBEAT": {
        "opcode": 0x20,
        "json_cmd": "CMD_HEARTBEAT",
        "description": "Heartbeat (no payload)",
        "payload": [],
    },
    "STOP": {
        "opcode": 0x21,
        "json_cmd": "CMD_STOP",
        "description": "Stop (no payload)",
        "payload": [],
    },
}
