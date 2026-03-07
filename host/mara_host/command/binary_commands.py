# AUTO-GENERATED FILE — DO NOT EDIT BY HAND
# Generated from BINARY_COMMANDS in platform_schema.py
"""
Binary command encoder for high-rate streaming.

Use binary commands for real-time control loops (50+ Hz).
Use JSON commands for setup/configuration.

Binary format is ~10x smaller than equivalent JSON:
  SET_VEL binary: 9 bytes
  SET_VEL JSON:   ~50 bytes
"""

from __future__ import annotations

import struct
from typing import List, Tuple


class Opcode:
    """Binary command opcodes (must match BinaryCommands.h on MCU)."""
    SET_VEL         = 0x10  # Set velocity: vx(f32), omega(f32)
    SET_SIGNAL      = 0x11  # Set signal: id(u16), value(f32)
    SET_SIGNALS     = 0x12  # Set multiple signals: count(u8), [id(u16), value(f32)]*
    HEARTBEAT       = 0x20  # Heartbeat (no payload)
    STOP            = 0x21  # Stop (no payload)


class BinaryStreamer:
    """
    Encodes binary commands for high-rate streaming.

    All multi-byte values are little-endian to match ESP32.
    """

    def encode_set_vel(self, vx: float, omega: float) -> bytes:
        """
        Encode SET_VEL command.

        Args:
            vx: Vx
            omega: Omega

        Returns:
            Binary payload (9 bytes)
        """
        return struct.pack('<Bff', Opcode.SET_VEL, vx, omega)

    def encode_set_signal(self, id: int, value: float) -> bytes:
        """
        Encode SET_SIGNAL command.

        Args:
            id: Id
            value: Value

        Returns:
            Binary payload (7 bytes)
        """
        return struct.pack('<BHf', Opcode.SET_SIGNAL, id, value)

    def encode_set_signals(self, signals: List[Tuple[int, float]]) -> bytes:
        """
        Encode SET_SIGNALS command for multiple signals.

        Args:
            signals: List of (signal_id, value) tuples

        Returns:
            Binary payload: opcode + count(u8) + [id(u16) + value(f32)] * count
        """
        count = min(len(signals), 255)  # Max 255 signals per packet
        data = struct.pack('<BB', Opcode.SET_SIGNALS, count)
        for i in range(count):
            signal_id, value = signals[i]
            data += struct.pack('<Hf', signal_id, value)
        return data

    def encode_heartbeat(self) -> bytes:
        """Heartbeat (no payload)"""
        return struct.pack('<B', Opcode.HEARTBEAT)

    def encode_stop(self) -> bytes:
        """Stop (no payload)"""
        return struct.pack('<B', Opcode.STOP)


__all__ = ["Opcode", "BinaryStreamer"]
