# AUTO-GENERATED from SensorDef("ir")
# Do not edit directly - modify schema/hardware/_sensors.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sensor_base import TelemetrySensor

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class IrReading:
    """Infrared proximity/reflectance sensor reading."""
    sensor_id: int = 0
    ok: int = 0
    value: int = 0
    ts_ms: int = 0


class IrSensor(TelemetrySensor[IrReading]):
    """
    Infrared proximity/reflectance sensor

    Interface: adc
    Telemetry topic: telemetry.ir
    """

    telemetry_topic = "telemetry.ir"

    def __init__(
        self,
        robot: "Robot",
        sensor_id: int = 0,
        auto_subscribe: bool = True,
    ) -> None:
        super().__init__(robot, sensor_id, auto_subscribe)

    def _parse_reading(self, data: dict) -> IrReading:
        return IrReading(
            sensor_id=data.get("sensor_id", 0),
            ok=data.get("ok", 0),
            value=data.get("value", 0),
            ts_ms=data.get("ts_ms", 0),
        )
