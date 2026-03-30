"""Tests for typed protocol message classes."""

import pytest
from mara_host.command.types import (
    IdentityMessage,
    CommandMessage,
    CommandAck,
    TelemetryMessage,
    RawFrame,
    HelloMessage,
)


class TestIdentityMessage:
    def test_from_dict_parses_all_fields(self):
        data = {
            "firmware": "1.2.3",
            "protocol": 5,
            "schema_version": 2,
            "capabilities": 0xFF,
            "features": ["pwm", "servo", "imu"],
            "board": "esp32",
            "name": "mara_bot",
        }
        msg = IdentityMessage.from_dict(data)

        assert msg.firmware == "1.2.3"
        assert msg.protocol == 5
        assert msg.schema_version == 2
        assert msg.capabilities == 0xFF
        assert msg.features == ("pwm", "servo", "imu")
        assert msg.board == "esp32"
        assert msg.name == "mara_bot"

    def test_from_dict_applies_defaults(self):
        msg = IdentityMessage.from_dict({})

        assert msg.firmware == "unknown"
        assert msg.protocol == 0
        assert msg.schema_version == 0
        assert msg.capabilities == 0
        assert msg.features == ()
        assert msg.board == "unknown"
        assert msg.name == "unknown"

    def test_to_dict_roundtrip(self):
        original = {
            "firmware": "2.0.0",
            "protocol": 10,
            "schema_version": 3,
            "capabilities": 15,
            "features": ["can", "pwm"],
            "board": "teensy",
            "name": "test_bot",
        }
        msg = IdentityMessage.from_dict(original)
        result = msg.to_dict()

        assert result["firmware"] == "2.0.0"
        assert result["protocol"] == 10
        assert result["features"] == ["can", "pwm"]

    def test_immutable(self):
        msg = IdentityMessage(firmware="1.0")
        with pytest.raises(AttributeError):
            msg.firmware = "2.0"


class TestCommandMessage:
    def test_to_dict_includes_kind(self):
        msg = CommandMessage(type="CMD_ARM", seq=42, payload={"param": "value"})
        result = msg.to_dict()

        assert result["kind"] == "cmd"
        assert result["type"] == "CMD_ARM"
        assert result["seq"] == 42
        assert result["param"] == "value"

    def test_from_dict_extracts_payload(self):
        data = {
            "kind": "cmd",
            "type": "CMD_SET_VEL",
            "seq": 123,
            "vx": 1.0,
            "omega": 0.5,
        }
        msg = CommandMessage.from_dict(data)

        assert msg.type == "CMD_SET_VEL"
        assert msg.seq == 123
        assert msg.payload == {"vx": 1.0, "omega": 0.5}

    def test_empty_payload(self):
        msg = CommandMessage(type="CMD_STOP", seq=1)
        result = msg.to_dict()

        assert result["kind"] == "cmd"
        assert result["type"] == "CMD_STOP"
        assert result["seq"] == 1


class TestCommandAck:
    def test_from_dict_parses_ack(self):
        data = {
            "cmd": "CMD_ARM",
            "seq": 42,
            "ok": True,
            "src": "mcu",
            "state": "armed",
        }
        ack = CommandAck.from_dict(data)

        assert ack.cmd == "CMD_ARM"
        assert ack.seq == 42
        assert ack.ok is True
        assert ack.state == "armed"
        assert ack.error is None
        assert ack.error_code is None

    def test_from_dict_parses_error(self):
        data = {
            "cmd": "CMD_ARM",
            "seq": 43,
            "ok": False,
            "error": "E-STOP active",
            "error_code": 101,
            "src": "mcu",
        }
        ack = CommandAck.from_dict(data)

        assert ack.ok is False
        assert ack.error == "E-STOP active"
        assert ack.error_code == 101

    def test_success_property(self):
        ack_ok = CommandAck(cmd="CMD_STOP", seq=1, ok=True)
        ack_fail = CommandAck(cmd="CMD_STOP", seq=2, ok=False, error="failed")

        assert ack_ok.success is True
        assert ack_fail.success is False

    def test_to_dict_includes_src(self):
        ack = CommandAck(cmd="CMD_ARM", seq=1, ok=True)
        result = ack.to_dict()

        assert result["src"] == "mcu"
        assert result["cmd"] == "CMD_ARM"
        assert result["ok"] is True

    def test_extra_data_preserved(self):
        data = {
            "cmd": "CMD_GPIO_READ",
            "seq": 10,
            "ok": True,
            "src": "mcu",
            "value": 1,
            "channel": 5,
        }
        ack = CommandAck.from_dict(data)

        assert ack.data["value"] == 1
        assert ack.data["channel"] == 5


class TestTelemetryMessage:
    def test_from_dict_extracts_timestamp(self):
        data = {
            "type": "TELEMETRY",
            "timestamp_ms": 12345,
            "imu_pitch": 10.5,
            "motor_speed": 0.75,
        }
        msg = TelemetryMessage.from_dict(data)

        assert msg.timestamp_ms == 12345
        assert msg.data["imu_pitch"] == 10.5
        assert msg.data["motor_speed"] == 0.75
        assert "type" not in msg.data

    def test_from_dict_with_short_timestamp_key(self):
        data = {"t": 999, "value": 42}
        msg = TelemetryMessage.from_dict(data)

        assert msg.timestamp_ms == 999

    def test_to_dict(self):
        msg = TelemetryMessage(timestamp_ms=5000, data={"speed": 1.0})
        result = msg.to_dict()

        assert result["timestamp_ms"] == 5000
        assert result["speed"] == 1.0


class TestRawFrame:
    def test_creation(self):
        frame = RawFrame(msg_type=0x99, payload=b"\x01\x02\x03")

        assert frame.msg_type == 0x99
        assert frame.payload == b"\x01\x02\x03"

    def test_to_dict(self):
        frame = RawFrame(msg_type=0x50, payload=b"test")
        result = frame.to_dict()

        assert result["msg_type"] == 0x50
        assert result["payload"] == b"test"


class TestHelloMessage:
    def test_from_dict_extracts_data(self):
        data = {"type": "HELLO", "version": "1.0", "name": "test"}
        msg = HelloMessage.from_dict(data)

        assert msg.data["version"] == "1.0"
        assert msg.data["name"] == "test"
        assert "type" not in msg.data

    def test_to_dict_includes_type(self):
        msg = HelloMessage(data={"info": "test"})
        result = msg.to_dict()

        assert result["type"] == "HELLO"
        assert result["info"] == "test"
