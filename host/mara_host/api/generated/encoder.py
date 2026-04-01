# AUTO-GENERATED from SensorDef("encoder")
# Do not edit directly - modify schema/hardware/_sensors.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sensor_base import TelemetrySensor

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class EncoderReading:
    """Quadrature rotary encoder reading."""
    ticks: int = 0
    ts_ms: int = 0


class Encoder(TelemetrySensor[EncoderReading]):
    """
    Quadrature rotary encoder

    Interface: gpio
    Telemetry topic: telemetry.encoder
    """

    telemetry_topic = "telemetry.encoder"

    def __init__(
        self,
        robot: "Robot",
        sensor_id: int = 0,
        auto_subscribe: bool = True,
    ) -> None:
        super().__init__(robot, sensor_id, auto_subscribe)

    def _parse_reading(self, data: dict) -> EncoderReading:
        return EncoderReading(
            ticks=data.get("ticks", 0),
            ts_ms=data.get("ts_ms", 0),
        )
