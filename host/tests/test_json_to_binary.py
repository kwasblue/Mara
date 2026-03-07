# tests/test_json_to_binary.py
"""Tests for JSON-to-Binary encoder."""

import struct
import pytest
from mara_host.command.json_to_binary import JsonToBinaryEncoder, JsonToBinaryBatchEncoder
from mara_host.command.binary_commands import Opcode


class TestJsonToBinaryEncoder:
    """Test JsonToBinaryEncoder."""

    def setup_method(self):
        self.encoder = JsonToBinaryEncoder()

    def test_encode_set_vel(self):
        """Test SET_VEL encoding."""
        cmd = {"type": "CMD_SET_VEL", "vx": 0.5, "omega": 0.1}
        binary = self.encoder.encode(cmd)

        assert binary is not None
        assert len(binary) == 9  # opcode + 2 floats

        # Parse it back
        opcode, vx, omega = struct.unpack("<Bff", binary)
        assert opcode == Opcode.SET_VEL
        assert abs(vx - 0.5) < 1e-6
        assert abs(omega - 0.1) < 1e-6

    def test_encode_set_vel_defaults(self):
        """Test SET_VEL with missing fields defaults to 0."""
        cmd = {"type": "CMD_SET_VEL"}
        binary = self.encoder.encode(cmd)

        opcode, vx, omega = struct.unpack("<Bff", binary)
        assert vx == 0.0
        assert omega == 0.0

    def test_encode_set_signal(self):
        """Test SET_SIGNAL encoding."""
        cmd = {"type": "CMD_CTRL_SIGNAL_SET", "id": 100, "value": 1.5}
        binary = self.encoder.encode(cmd)

        assert binary is not None
        assert len(binary) == 7  # opcode + u16 + f32

        opcode, signal_id, value = struct.unpack("<BHf", binary)
        assert opcode == Opcode.SET_SIGNAL
        assert signal_id == 100
        assert abs(value - 1.5) < 1e-6

    def test_encode_heartbeat(self):
        """Test HEARTBEAT encoding."""
        cmd = {"type": "CMD_HEARTBEAT"}
        binary = self.encoder.encode(cmd)

        assert binary is not None
        assert len(binary) == 1
        assert binary[0] == Opcode.HEARTBEAT

    def test_encode_stop(self):
        """Test STOP encoding."""
        cmd = {"type": "CMD_STOP"}
        binary = self.encoder.encode(cmd)

        assert binary is not None
        assert len(binary) == 1
        assert binary[0] == Opcode.STOP

    def test_encode_unsupported_returns_none(self):
        """Test that unsupported commands return None."""
        unsupported = [
            {"type": "CMD_ARM"},
            {"type": "CMD_DISARM"},
            {"type": "CMD_SERVO_SET_ANGLE", "servo_id": 0, "angle_deg": 45},
            {"type": "CMD_GPIO_WRITE", "channel": 0, "value": 1},
        ]

        for cmd in unsupported:
            assert self.encoder.encode(cmd) is None

    def test_supports_binary(self):
        """Test supports_binary check."""
        assert self.encoder.supports_binary("CMD_SET_VEL") is True
        assert self.encoder.supports_binary("CMD_HEARTBEAT") is True
        assert self.encoder.supports_binary("CMD_STOP") is True
        assert self.encoder.supports_binary("CMD_CTRL_SIGNAL_SET") is True

        assert self.encoder.supports_binary("CMD_ARM") is False
        assert self.encoder.supports_binary("CMD_SERVO_ATTACH") is False

    def test_wire_size_comparison(self):
        """Verify binary is significantly smaller than JSON."""
        import json

        # JSON version
        json_cmd = {
            "kind": "cmd",
            "type": "CMD_SET_VEL",
            "seq": 1,
            "vx": 0.5,
            "omega": 0.1,
        }
        json_size = len(json.dumps(json_cmd, separators=(",", ":")).encode())

        # Binary version
        binary = self.encoder.encode({"type": "CMD_SET_VEL", "vx": 0.5, "omega": 0.1})
        binary_size = len(binary)

        print(f"JSON size: {json_size} bytes, Binary size: {binary_size} bytes")
        print(f"Compression ratio: {json_size / binary_size:.1f}x")

        # Binary should be at least 5x smaller
        assert binary_size < json_size / 5


class TestJsonToBinaryBatchEncoder:
    """Test batch signal encoding."""

    def setup_method(self):
        self.encoder = JsonToBinaryBatchEncoder()

    def test_encode_signals_batch(self):
        """Test batching multiple signals."""
        signals = [
            (100, 1.5),
            (101, 0.0),
            (102, -2.5),
        ]
        binary = self.encoder.encode_signals(signals)

        assert binary is not None
        # opcode(1) + count(1) + 3 * (id:u16 + value:f32) = 2 + 3*6 = 20 bytes
        assert len(binary) == 20

        # Parse header
        opcode, count = struct.unpack("<BB", binary[:2])
        assert opcode == Opcode.SET_SIGNALS
        assert count == 3

        # Parse signals
        for i, (expected_id, expected_val) in enumerate(signals):
            offset = 2 + i * 6
            sig_id, value = struct.unpack("<Hf", binary[offset : offset + 6])
            assert sig_id == expected_id
            assert abs(value - expected_val) < 1e-6

    def test_encode_signal_cmds(self):
        """Test converting multiple CMD_CTRL_SIGNAL_SET to batch."""
        cmds = [
            {"type": "CMD_CTRL_SIGNAL_SET", "id": 10, "value": 1.0},
            {"type": "CMD_CTRL_SIGNAL_SET", "id": 11, "value": 2.0},
        ]
        binary = self.encoder.encode_signal_cmds(cmds)

        assert binary is not None
        opcode, count = struct.unpack("<BB", binary[:2])
        assert opcode == Opcode.SET_SIGNALS
        assert count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
