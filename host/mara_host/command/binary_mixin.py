# mara_host/command/binary_mixin.py
"""Binary command encoding mixin for MaraClient."""

from typing import Any, Dict, Optional

from mara_host.core import protocol
from .json_to_binary import JsonToBinaryEncoder

MSG_CMD_BIN = protocol.MSG_CMD_BIN


class BinaryCommandsMixin:
    """
    Mixin providing binary command encoding methods.

    Binary encoding reduces wire size significantly for high-rate commands:
    - CMD_SET_VEL: 9 bytes vs ~50 bytes JSON
    - CMD_HEARTBEAT: 5 bytes vs ~30 bytes JSON
    - CMD_SIGNAL_SET: 7 bytes vs ~40 bytes JSON

    This mixin requires:
    - self._send_frame(msg_type, payload) - async method
    - self._send_json_cmd_internal(type_str, payload) - async method
    """

    _binary_encoder: JsonToBinaryEncoder
    _prefer_binary: bool

    def _init_binary_encoder(self) -> None:
        """Initialize binary encoder. Call from __init__."""
        self._binary_encoder = JsonToBinaryEncoder()
        self._prefer_binary = True

    async def send_binary(self, cmd: Dict[str, Any]) -> bool:
        """
        Send a command as binary (if supported).

        Args:
            cmd: JSON command dict, e.g. {"type": "CMD_SET_VEL", "vx": 0.5, "omega": 0.1}

        Returns:
            True if sent as binary, False if not supported (caller should use JSON).

        Example:
            sent = await client.send_binary({"type": "CMD_SET_VEL", "vx": 0.5, "omega": 0.1})
            if not sent:
                await client.send_json_cmd("CMD_SET_VEL", {"vx": 0.5, "omega": 0.1})
        """
        binary_payload = self._binary_encoder.encode(cmd)
        if binary_payload is None:
            return False

        await self._send_frame(MSG_CMD_BIN, binary_payload)
        return True

    async def send_auto(
        self,
        type_str: str,
        payload: Optional[Dict[str, Any]] = None,
        prefer_binary: bool = True,
    ) -> None:
        """
        Send a command using binary if supported, otherwise JSON.

        This is the recommended method for streaming commands - it automatically
        uses the most efficient encoding:
        - SET_VEL, SIGNAL_SET, HEARTBEAT, STOP -> Binary (5-10x smaller)
        - All other commands -> JSON

        Args:
            type_str: Command type (e.g. "CMD_SET_VEL")
            payload: Command payload dict
            prefer_binary: If True, use binary when available

        Example:
            # These use binary automatically (9 bytes vs ~50 bytes)
            await client.send_auto("CMD_SET_VEL", {"vx": 0.5, "omega": 0.1})
            await client.send_auto("CMD_HEARTBEAT")
            await client.send_auto("CMD_STOP")

            # These fall back to JSON (no binary encoding)
            await client.send_auto("CMD_ARM")
            await client.send_auto("CMD_SERVO_SET_ANGLE", {"servo_id": 0, "angle_deg": 45})
        """
        cmd = {"type": type_str, **(payload or {})}

        if prefer_binary and self._prefer_binary:
            binary_payload = self._binary_encoder.encode(cmd)
            if binary_payload is not None:
                await self._send_frame(MSG_CMD_BIN, binary_payload)
                return

        # Fall back to JSON
        await self._send_json_cmd_internal(type_str, payload or {})

    async def send_vel_binary(self, vx: float, omega: float) -> None:
        """
        Send SET_VEL as binary (9 bytes instead of ~50 bytes JSON).

        Use this for high-rate velocity streaming (50+ Hz).
        """
        await self.send_binary({"type": "CMD_SET_VEL", "vx": vx, "omega": omega})

    async def send_signal_binary(self, signal_id: int, value: float) -> None:
        """
        Send SIGNAL_SET as binary (7 bytes instead of ~40 bytes JSON).

        Use this for high-rate signal streaming.
        """
        await self.send_binary({"type": "CMD_CTRL_SIGNAL_SET", "id": signal_id, "value": value})

    def set_prefer_binary(self, prefer: bool) -> None:
        """Enable/disable automatic binary encoding for send_auto()."""
        self._prefer_binary = prefer
