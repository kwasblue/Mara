# AUTO-GENERATED FILE — DO NOT EDIT BY HAND
# Generated from BINARY_COMMANDS in platform_schema.py
"""
JSON-to-Binary command encoder.

Converts JSON command dictionaries to compact binary format for wire transmission.
The MCU receives binary (fast parsing) while the host writes JSON (human-readable).

Example:
    from robot_host.command.json_to_binary import JsonToBinaryEncoder
    from robot_host.core.protocol import encode, MSG_CMD_BIN

    encoder = JsonToBinaryEncoder()

    # Write commands as JSON dicts
    cmd = {"type": "CMD_SET_VEL", "vx": 0.5, "omega": 0.1}

    # Convert to binary
    binary_payload = encoder.encode(cmd)
    if binary_payload:
        frame = encode(MSG_CMD_BIN, binary_payload)
        transport.send(frame)
"""

from __future__ import annotations

import struct
from typing import Dict, Any, Optional, List, Tuple

from .binary_commands import Opcode


class JsonToBinaryEncoder:
    """
    Converts JSON command dictionaries to binary wire format.

    Supports a subset of commands that benefit from binary encoding:
    - High-rate streaming commands (SET_VEL, SET_SIGNAL, etc.)
    - Simple commands (HEARTBEAT, STOP)

    Commands without binary support are returned as None (caller should
    fall back to JSON encoding).
    """

    # Map JSON command types to binary opcodes (auto-generated)
    _COMMAND_MAP: Dict[str, int] = {
        "CMD_SET_VEL": Opcode.SET_VEL,
        "CMD_CTRL_SIGNAL_SET": Opcode.SET_SIGNAL,
        "CMD_HEARTBEAT": Opcode.HEARTBEAT,
        "CMD_STOP": Opcode.STOP,
    }

    def encode(self, cmd: Dict[str, Any]) -> Optional[bytes]:
        """
        Encode a JSON command dict to binary.

        Args:
            cmd: JSON command dict with "type" field and payload fields.
                 Example: {"type": "CMD_SET_VEL", "vx": 0.5, "omega": 0.1}

        Returns:
            Binary payload bytes, or None if command doesn't support binary.
        """
        cmd_type = cmd.get("type", "")

        if cmd_type == "CMD_SET_VEL":
            return self._encode_set_vel(cmd)
        elif cmd_type == "CMD_CTRL_SIGNAL_SET":
            return self._encode_set_signal(cmd)
        elif cmd_type == "CMD_HEARTBEAT":
            return self._encode_heartbeat(cmd)
        elif cmd_type == "CMD_STOP":
            return self._encode_stop(cmd)
        else:
            # No binary encoding for this command
            return None

    def supports_binary(self, cmd_type: str) -> bool:
        """Check if a command type has binary encoding support."""
        return cmd_type in self._COMMAND_MAP

    def _encode_set_vel(self, cmd: Dict[str, Any]) -> bytes:
        """
        Encode SET_VEL command.

        JSON: CMD_SET_VEL
        """
        vx = float(cmd.get("vx", 0.0))
        omega = float(cmd.get("omega", 0.0))
        return struct.pack('<Bff', Opcode.SET_VEL, vx, omega)

    def _encode_set_signal(self, cmd: Dict[str, Any]) -> bytes:
        """
        Encode SET_SIGNAL command.

        JSON: CMD_CTRL_SIGNAL_SET
        """
        id = int(cmd.get("id", 0))
        value = float(cmd.get("value", 0.0))
        return struct.pack('<BHf', Opcode.SET_SIGNAL, id, value)

    def _encode_heartbeat(self, cmd: Dict[str, Any]) -> bytes:
        """
        Encode HEARTBEAT command.

        JSON: CMD_HEARTBEAT
        """
        return struct.pack('<B', Opcode.HEARTBEAT)

    def _encode_stop(self, cmd: Dict[str, Any]) -> bytes:
        """
        Encode STOP command.

        JSON: CMD_STOP
        """
        return struct.pack('<B', Opcode.STOP)


class JsonToBinaryBatchEncoder(JsonToBinaryEncoder):
    """
    Extended encoder with batch signal support.

    Use encode_signals() to batch multiple signal updates into one packet.
    """

    def encode_signals(self, signals: List[Tuple[int, float]]) -> bytes:
        """
        Encode multiple signals into one SET_SIGNALS command.

        Args:
            signals: List of (signal_id, value) tuples

        Returns:
            Binary payload: [opcode][count:u8][id:u16][value:f32]...
        """
        count = min(len(signals), 255)
        data = struct.pack('<BB', Opcode.SET_SIGNALS, count)
        for i in range(count):
            signal_id, value = signals[i]
            data += struct.pack('<Hf', signal_id, value)
        return data

    def encode_signal_cmds(self, cmds: List[Dict[str, Any]]) -> Optional[bytes]:
        """
        Batch multiple CMD_CTRL_SIGNAL_SET commands into one binary packet.

        Args:
            cmds: List of signal set commands

        Returns:
            Binary payload, or None if list is empty
        """
        signals = []
        for cmd in cmds:
            if cmd.get("type") == "CMD_CTRL_SIGNAL_SET":
                signal_id = int(cmd.get("id", 0))
                value = float(cmd.get("value", 0.0))
                signals.append((signal_id, value))

        if not signals:
            return None

        return self.encode_signals(signals)


__all__ = ["JsonToBinaryEncoder", "JsonToBinaryBatchEncoder"]
