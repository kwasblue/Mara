"""Tests for generated command payload classes."""

import pytest
from mara_host.command.payloads import (
    SetVelPayload,
    DcSetSpeedPayload,
    DcStopPayload,
    ServoSetAnglePayload,
    GpioWritePayload,
)


class TestSetVelPayload:
    def test_required_params(self):
        payload = SetVelPayload(vx=1.0, omega=0.5)
        assert payload.vx == 1.0
        assert payload.omega == 0.5
        assert payload.frame == 'robot'  # default

    def test_to_dict(self):
        payload = SetVelPayload(vx=0.5, omega=0.1, frame='world')
        result = payload.to_dict()

        assert result["vx"] == 0.5
        assert result["omega"] == 0.1
        assert result["frame"] == 'world'

    def test_cmd_attribute(self):
        assert SetVelPayload._cmd == "CMD_SET_VEL"


class TestDcSetSpeedPayload:
    def test_creation(self):
        payload = DcSetSpeedPayload(motor_id=0, speed=0.75)
        assert payload.motor_id == 0
        assert payload.speed == 0.75

    def test_to_dict(self):
        payload = DcSetSpeedPayload(motor_id=2, speed=-0.5)
        result = payload.to_dict()

        assert result["motor_id"] == 2
        assert result["speed"] == -0.5


class TestDcStopPayload:
    def test_creation(self):
        payload = DcStopPayload(motor_id=1)
        assert payload.motor_id == 1

    def test_to_dict(self):
        payload = DcStopPayload(motor_id=3)
        result = payload.to_dict()
        assert result["motor_id"] == 3


class TestServoSetAnglePayload:
    def test_required_and_optional(self):
        payload = ServoSetAnglePayload(servo_id=0, angle_deg=90.0)
        assert payload.servo_id == 0
        assert payload.angle_deg == 90.0
        assert payload.duration_ms == 0  # default

    def test_with_duration(self):
        payload = ServoSetAnglePayload(servo_id=1, angle_deg=45.0, duration_ms=500)
        result = payload.to_dict()

        assert result["servo_id"] == 1
        assert result["angle_deg"] == 45.0
        assert result["duration_ms"] == 500


class TestGpioWritePayload:
    def test_creation(self):
        payload = GpioWritePayload(channel=5, value=1)
        assert payload.channel == 5
        assert payload.value == 1

    def test_to_dict(self):
        payload = GpioWritePayload(channel=2, value=0)
        result = payload.to_dict()

        assert result["channel"] == 2
        assert result["value"] == 0


class TestPayloadUsageWithClient:
    """Tests demonstrating how payloads integrate with client code."""

    def test_payload_can_be_used_with_send(self):
        """Payloads produce dicts suitable for client.send_reliable()."""
        payload = SetVelPayload(vx=1.0, omega=0.0)
        cmd_dict = payload.to_dict()

        # This is what would be passed to client.send_reliable(payload._cmd, cmd_dict)
        assert isinstance(cmd_dict, dict)
        assert "vx" in cmd_dict
        assert "omega" in cmd_dict
