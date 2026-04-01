# AUTO-GENERATED from SensorDef("ultrasonic")
# Do not edit directly - modify schema/hardware/_sensors.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sensor_base import TelemetrySensor

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class UltrasonicReading:
    """Ultrasonic distance sensor (HC-SR04 compatible) reading."""
    sensor_id: int = 0
    attached: int = 0
    ok: int = 0
    dist_mm: int = 0
    ts_ms: int = 0


class Ultrasonic(TelemetrySensor[UltrasonicReading]):
    """
    Ultrasonic distance sensor (HC-SR04 compatible)

    Interface: gpio
    Telemetry topic: telemetry.ultrasonic
    """

    telemetry_topic = "telemetry.ultrasonic"

    def __init__(
        self,
        robot: "Robot",
        sensor_id: int = 0,
        auto_subscribe: bool = True,
    ) -> None:
        super().__init__(robot, sensor_id, auto_subscribe)

    def _parse_reading(self, data: dict) -> UltrasonicReading:
        return UltrasonicReading(
            sensor_id=data.get("sensor_id", 0),
            attached=data.get("attached", 0),
            ok=data.get("ok", 0),
            dist_mm=data.get("dist_mm", 0),
            ts_ms=data.get("ts_ms", 0),
        )
