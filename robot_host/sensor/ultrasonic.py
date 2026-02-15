# robot_host/sensor/ultrasonic.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from robot_host.command.client import AsyncRobotClient
from robot_host.core.event_bus import EventBus
from robot_host.core.host_module import CommandHostModule


@dataclass
class UltrasonicDefaults:
    sensor_id: int = 0


class UltrasonicHostModule(CommandHostModule):
    """
    Host-side wrapper around ultrasonic commands + telemetry.

    Commands:
      - CMD_ULTRASONIC_ATTACH
      - CMD_ULTRASONIC_READ

    Telemetry:
      - subscribes to 'telemetry.raw'
      - when it sees data['ultrasonic'], republishes on 'telemetry.ultrasonic'
    """

    module_name = "ultrasonic"

    def __init__(
        self,
        bus: EventBus,
        client: AsyncRobotClient,
        defaults: UltrasonicDefaults | None = None,
        auto_subscribe: bool = True,
    ) -> None:
        super().__init__(bus, client)
        self._defaults = defaults or UltrasonicDefaults()

        if auto_subscribe:
            self._bus.subscribe("telemetry.raw", self._on_telemetry_raw)

    # -------- Commands --------

    async def attach(self, sensor_id: int | None = None) -> None:
        sid = sensor_id if sensor_id is not None else self._defaults.sensor_id
        await self._client.cmd_ultrasonic_attach(sensor_id=int(sid))

    async def read(self, sensor_id: int | None = None) -> None:
        """
        Trigger a single ultrasonic measurement.

        The result is expected to show up in telemetry on the MCU side
        (e.g., via data['ultrasonic']), which we rebroadcast as
        'telemetry.ultrasonic'.
        """
        sid = sensor_id if sensor_id is not None else self._defaults.sensor_id
        await self._client.cmd_ultrasonic_read(sensor_id=int(sid))

    # -------- Telemetry fan-out --------

    def _on_telemetry_raw(self, msg: dict[str, Any]) -> None:
        """
        Look for an 'ultrasonic' block in telemetry.raw and fan it out
        to a more specific topic.
        """
        data = msg.get("data", {})
        ultra = data.get("ultrasonic")
        if ultra is None:
            return

        # Optionally filter by sensor_id, if present
        sid = ultra.get("sensor_id")
        if sid is None or sid == self._defaults.sensor_id:
            # Re-publish a cleaner ultrasonic event
            self._bus.publish("telemetry.ultrasonic", ultra)
