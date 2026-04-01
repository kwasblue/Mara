# AUTO-GENERATED from SensorDef("imu")
# Do not edit directly - modify schema/hardware/_sensors.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sensor_base import TelemetrySensor

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class ImuReading:
    """Inertial Measurement Unit (accelerometer, gyroscope, temperature) reading."""
    online: int = 0
    ok: int = 0
    ax_mg: int = 0
    ay_mg: int = 0
    az_mg: int = 0
    gx_mdps: int = 0
    gy_mdps: int = 0
    gz_mdps: int = 0
    temp_c_centi: int = 0
    ts_ms: int = 0


class Imu(TelemetrySensor[ImuReading]):
    """
    Inertial Measurement Unit (accelerometer, gyroscope, temperature)

    Interface: i2c
    Telemetry topic: telemetry.imu
    """

    telemetry_topic = "telemetry.imu"

    def __init__(
        self,
        robot: "Robot",
        sensor_id: int = 0,
        auto_subscribe: bool = True,
    ) -> None:
        super().__init__(robot, sensor_id, auto_subscribe)

    def _parse_reading(self, data: dict) -> ImuReading:
        return ImuReading(
            online=data.get("online", 0),
            ok=data.get("ok", 0),
            ax_mg=data.get("ax_mg", 0),
            ay_mg=data.get("ay_mg", 0),
            az_mg=data.get("az_mg", 0),
            gx_mdps=data.get("gx_mdps", 0),
            gy_mdps=data.get("gy_mdps", 0),
            gz_mdps=data.get("gz_mdps", 0),
            temp_c_centi=data.get("temp_c_centi", 0),
            ts_ms=data.get("ts_ms", 0),
        )
