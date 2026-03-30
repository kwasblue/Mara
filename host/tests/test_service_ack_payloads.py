import pytest
from unittest.mock import AsyncMock

from mara_host.core.event_bus import EventBus
from mara_host.services.control.encoder_service import EncoderService
from mara_host.services.control.gpio_service import GpioService
from mara_host.services.control.composite_service import CompositeService
from mara_host.services.control.ultrasonic_service import UltrasonicService
from mara_host.services.control.imu_service import ImuService


class FakeClient:
    def __init__(self):
        self.bus = EventBus()
        self.send_reliable = AsyncMock(side_effect=self._send_reliable)

    async def _send_reliable(self, command, payload):
        if command == "CMD_GPIO_READ":
            self.bus.publish(f"cmd.{command}", {
                "src": "mcu",
                "cmd": command,
                "ok": True,
                "channel": payload["channel"],
                "value": 1,
            })
        elif command == "CMD_ENCODER_READ":
            self.bus.publish(f"cmd.{command}", {
                "src": "mcu",
                "cmd": command,
                "ok": True,
                "encoder_id": payload["encoder_id"],
                "ticks": 321,
            })
        elif command == "CMD_ULTRASONIC_READ":
            if payload.get("sensor_id") == 9:
                self.bus.publish(f"cmd.{command}", {
                    "src": "mcu",
                    "cmd": command,
                    "ok": False,
                    "sensor_id": payload["sensor_id"],
                    "attached": True,
                    "error": "read_failed",
                })
                return False, "read_failed"
            self.bus.publish(f"cmd.{command}", {
                "src": "mcu",
                "cmd": command,
                "ok": True,
                "sensor_id": payload["sensor_id"],
                "distance_cm": 55.5,
            })
        elif command == "CMD_IMU_READ":
            self.bus.publish(f"cmd.{command}", {
                "src": "mcu",
                "cmd": command,
                "ok": True,
                "online": True,
                "ax_g": 0.01,
                "ay_g": -0.02,
                "az_g": 1.00,
                "gx_dps": 0.3,
                "gy_dps": -0.4,
                "gz_dps": 0.5,
                "temp_c": 24.75,
            })
        return True, None


@pytest.mark.asyncio
async def test_gpio_read_returns_ack_payload_and_updates_cached_state():
    client = FakeClient()
    service = GpioService(client)
    service.configure(channel=7, pin=7)

    result = await service.read(7)

    assert result.ok is True
    assert result.data["channel"] == 7
    assert result.data["value"] == 1
    assert service.get_channel(7).value == 1


@pytest.mark.asyncio
async def test_encoder_read_returns_ack_payload_and_updates_state():
    client = FakeClient()
    service = EncoderService(client)

    result = await service.read(2)

    assert result.ok is True
    assert result.data["encoder_id"] == 2
    assert result.data["ticks"] == 321
    assert service.get_state(2).count == 321


@pytest.mark.asyncio
async def test_ultrasonic_read_returns_ack_payload():
    client = FakeClient()
    service = UltrasonicService(client)

    result = await service.read(0)

    assert result.ok is True
    assert result.data["sensor_id"] == 0
    assert result.data["distance_cm"] == 55.5


@pytest.mark.asyncio
async def test_imu_read_returns_explicit_snapshot_payload():
    client = FakeClient()
    service = ImuService(client)

    result = await service.read()

    assert result.ok is True
    assert result.data["online"] is True
    assert result.data["ax"] == pytest.approx(0.01)
    assert result.data["az"] == pytest.approx(1.0)
    assert result.data["temperature"] == pytest.approx(24.75)
    assert result.data["units"]["accel"] == "g"
    assert service.last_reading is not None
    assert service.last_reading.gz == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_composite_service_accepts_extended_batch_payload():
    client = FakeClient()
    service = CompositeService(client)

    actions = [
        {"cmd": "CMD_GPIO_WRITE", "args": {"channel": 0, "value": 1}},
        {"cmd": "CMD_SERVO_SET_ANGLE", "args": {"servo_id": 0, "angle_deg": 90, "duration_ms": 250}},
        {"cmd": "CMD_PWM_SET", "args": {"channel": 1, "duty": 0.4, "freq_hz": 1000.0}},
        {"cmd": "CMD_DC_SET_SPEED", "args": {"motor_id": 0, "speed": 0.2}},
        {"cmd": "CMD_STEPPER_MOVE_REL", "args": {"stepper_id": 1, "steps": 100, "speed_rps": 2.0}},
    ]

    result = await service.apply(actions)

    assert result.ok is True
    client.send_reliable.assert_awaited_once_with("CMD_BATCH_APPLY", {"actions": actions})


@pytest.mark.asyncio
async def test_composite_service_rejects_conflicting_motor_actions_locally():
    client = FakeClient()
    service = CompositeService(client)

    result = await service.apply([
        {"cmd": "CMD_DC_SET_SPEED", "args": {"motor_id": 0, "speed": 0.5}},
        {"cmd": "CMD_DC_STOP", "args": {"motor_id": 0}},
    ])

    assert result.ok is False
    assert result.error.startswith("conflicting_motor_action")
    client.send_reliable.assert_not_awaited()



@pytest.mark.asyncio
async def test_ultrasonic_read_timeout_is_reported_as_degraded_hardware_state():
    client = FakeClient()
    service = UltrasonicService(client)
    service.configure(9, trig_pin=4, echo_pin=5)
    service.get_state(9).attached = True

    result = await service.read(9)

    assert result.ok is True
    assert result.data["degraded"] is True
    assert result.data["expected"] is True
    assert result.data["reason"] == "no_echo"
    assert service.get_state(9).degraded is True
    assert service.get_state(9).distance_cm is None
