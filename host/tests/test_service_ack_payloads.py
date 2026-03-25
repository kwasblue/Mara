import pytest
from unittest.mock import AsyncMock

from mara_host.core.event_bus import EventBus
from mara_host.services.control.encoder_service import EncoderService
from mara_host.services.control.gpio_service import GpioService
from mara_host.services.control.ultrasonic_service import UltrasonicService


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
            self.bus.publish(f"cmd.{command}", {
                "src": "mcu",
                "cmd": command,
                "ok": True,
                "sensor_id": payload["sensor_id"],
                "distance_cm": 55.5,
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
