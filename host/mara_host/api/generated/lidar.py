# AUTO-GENERATED from SensorDef("lidar")
# Do not edit directly - modify schema/hardware/_sensors.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sensor_base import TelemetrySensor

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class LidarReading:
    """LiDAR time-of-flight distance sensor reading."""
    online: int = 0
    ok: int = 0
    dist_mm: int = 0
    signal: int = 0
    ts_ms: int = 0


class Lidar(TelemetrySensor[LidarReading]):
    """
    LiDAR time-of-flight distance sensor

    Interface: uart
    Telemetry topic: telemetry.lidar
    """

    telemetry_topic = "telemetry.lidar"

    def __init__(
        self,
        robot: "Robot",
        sensor_id: int = 0,
        auto_subscribe: bool = True,
    ) -> None:
        super().__init__(robot, sensor_id, auto_subscribe)

    def _parse_reading(self, data: dict) -> LidarReading:
        return LidarReading(
            online=data.get("online", 0),
            ok=data.get("ok", 0),
            dist_mm=data.get("dist_mm", 0),
            signal=data.get("signal", 0),
            ts_ms=data.get("ts_ms", 0),
        )
