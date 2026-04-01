# AUTO-GENERATED from SensorDef("temp")
# Do not edit directly - modify schema/hardware/_sensors.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sensor_base import TelemetrySensor

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class TemperatureReading:
    """I2C temperature sensor reading."""
    sensor_id: int = 0
    ok: int = 0
    temp_centi: int = 0
    ts_ms: int = 0


class Temperature(TelemetrySensor[TemperatureReading]):
    """
    I2C temperature sensor

    Interface: i2c
    Telemetry topic: telemetry.temp
    """

    telemetry_topic = "telemetry.temp"

    def __init__(
        self,
        robot: "Robot",
        sensor_id: int = 0,
        auto_subscribe: bool = True,
    ) -> None:
        super().__init__(robot, sensor_id, auto_subscribe)

    def _parse_reading(self, data: dict) -> TemperatureReading:
        return TemperatureReading(
            sensor_id=data.get("sensor_id", 0),
            ok=data.get("ok", 0),
            temp_centi=data.get("temp_centi", 0),
            ts_ms=data.get("ts_ms", 0),
        )
