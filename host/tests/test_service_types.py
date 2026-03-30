"""Tests for typed service response classes."""

import pytest
from mara_host.services.types import (
    GpioReadResponse,
    GpioWriteResponse,
    GpioRegisterResponse,
    EncoderReadResponse,
    EncoderAttachResponse,
    ServoAttachResponse,
    ServoSetAngleResponse,
    MotorSetSpeedResponse,
    MotorAttachResponse,
    ImuReadResponse,
    RobotStateResponse,
    ControlGraphSlotStatus,
    ControlGraphStatus,
)


class TestGpioResponses:
    def test_read_response_from_dict(self):
        data = {"channel": 5, "value": 1, "pin": 13}
        resp = GpioReadResponse.from_dict(data)

        assert resp.channel == 5
        assert resp.value == 1
        assert resp.pin == 13

    def test_write_response_from_dict(self):
        data = {"channel": 2, "value": 0}
        resp = GpioWriteResponse.from_dict(data)

        assert resp.channel == 2
        assert resp.value == 0

    def test_register_response_from_dict(self):
        data = {"channel": 0, "pin": 14, "mode": "input_pullup"}
        resp = GpioRegisterResponse.from_dict(data)

        assert resp.channel == 0
        assert resp.pin == 14
        assert resp.mode == "input_pullup"


class TestEncoderResponses:
    def test_read_response_from_dict(self):
        data = {"encoder_id": 0, "ticks": 1234, "velocity": 50.5}
        resp = EncoderReadResponse.from_dict(data)

        assert resp.encoder_id == 0
        assert resp.ticks == 1234
        assert resp.velocity == 50.5

    def test_attach_response_from_dict(self):
        data = {"encoder_id": 1, "pin_a": 34, "pin_b": 35}
        resp = EncoderAttachResponse.from_dict(data)

        assert resp.encoder_id == 1
        assert resp.pin_a == 34
        assert resp.pin_b == 35


class TestServoResponses:
    def test_attach_response_from_dict(self):
        data = {"servo_id": 0, "channel": 5, "min_us": 500, "max_us": 2500}
        resp = ServoAttachResponse.from_dict(data)

        assert resp.servo_id == 0
        assert resp.channel == 5
        assert resp.min_us == 500
        assert resp.max_us == 2500

    def test_set_angle_response_from_dict(self):
        data = {"servo_id": 1, "angle_deg": 90.5}
        resp = ServoSetAngleResponse.from_dict(data)

        assert resp.servo_id == 1
        assert resp.angle_deg == 90.5


class TestMotorResponses:
    def test_set_speed_response_from_dict(self):
        data = {"motor_id": 2, "speed": 0.75}
        resp = MotorSetSpeedResponse.from_dict(data)

        assert resp.motor_id == 2
        assert resp.speed == 0.75

    def test_attach_response_from_dict(self):
        data = {"motor_id": 0, "pin_pwm": 25, "pin_dir": 26, "pin_dir_b": 27}
        resp = MotorAttachResponse.from_dict(data)

        assert resp.motor_id == 0
        assert resp.pin_pwm == 25
        assert resp.pin_dir == 26
        assert resp.pin_dir_b == 27


class TestImuResponse:
    def test_from_dict_full(self):
        data = {
            "pitch": 10.5,
            "roll": 2.0,
            "yaw": -5.0,
            "accel_x": 0.1,
            "accel_y": 0.2,
            "accel_z": 9.8,
            "gyro_x": 0.01,
            "gyro_y": 0.02,
            "gyro_z": 0.03,
        }
        resp = ImuReadResponse.from_dict(data)

        assert resp.pitch == 10.5
        assert resp.roll == 2.0
        assert resp.accel_z == 9.8

    def test_from_dict_short_names(self):
        data = {"pitch": 5.0, "ax": 0.5, "ay": 0.6, "az": 9.8}
        resp = ImuReadResponse.from_dict(data)

        assert resp.pitch == 5.0
        assert resp.accel_x == 0.5
        assert resp.accel_y == 0.6


class TestRobotStateResponse:
    def test_armed_state(self):
        resp = RobotStateResponse.from_dict({"state": "ARMED"})

        assert resp.state == "ARMED"
        assert resp.armed is True
        assert resp.active is False
        assert resp.estopped is False

    def test_active_state(self):
        resp = RobotStateResponse.from_dict({"state": "ACTIVE"})

        assert resp.state == "ACTIVE"
        assert resp.armed is True  # Active implies armed
        assert resp.active is True
        assert resp.estopped is False

    def test_estopped_state(self):
        resp = RobotStateResponse.from_dict({"state": "ESTOPPED"})

        assert resp.state == "ESTOPPED"
        assert resp.armed is False
        assert resp.active is False
        assert resp.estopped is True


class TestControlGraphResponses:
    def test_slot_status_from_dict(self):
        data = {"id": "imu_to_servo", "enabled": True, "last_value": 45.0, "rate_hz": 50}
        slot = ControlGraphSlotStatus.from_dict(data)

        assert slot.id == "imu_to_servo"
        assert slot.enabled is True
        assert slot.last_value == 45.0
        assert slot.rate_hz == 50

    def test_status_from_dict(self):
        data = {
            "running": True,
            "slot_count": 2,
            "slots": [
                {"id": "slot_1", "enabled": True, "last_value": 10.0},
                {"id": "slot_2", "enabled": False, "last_value": 0.0},
            ],
        }
        status = ControlGraphStatus.from_dict(data)

        assert status.running is True
        assert status.slot_count == 2
        assert len(status.slots) == 2
        assert status.slots[0].id == "slot_1"
        assert status.slots[1].enabled is False


class TestUsageWithServiceResult:
    """Tests demonstrating how response types integrate with ServiceResult."""

    def test_parse_response_from_service_data(self):
        """Response types can parse the data dict from ServiceResult."""
        from mara_host.core.result import ServiceResult

        # Simulating what a service returns
        result = ServiceResult.success(data={"channel": 3, "value": 1})

        if result.ok:
            resp = GpioReadResponse.from_dict(result.data)
            assert resp.channel == 3
            assert resp.value == 1

    def test_immutable_response(self):
        """Response types are immutable to prevent accidental modification."""
        resp = EncoderReadResponse(encoder_id=0, ticks=100)
        with pytest.raises(AttributeError):
            resp.ticks = 200
