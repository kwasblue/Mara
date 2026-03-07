# mara_host/sensor/imu.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from mara_host.core.event_bus import EventBus
from mara_host.core.host_module import EventHostModule


@dataclass
class ImuState:
    ts_ms: Optional[int]
    online: bool
    ok: bool
    ax_g: float
    ay_g: float
    az_g: float
    gx_dps: float
    gy_dps: float
    gz_dps: float
    temp_c: float
    acc_mag_g: float
    roll_rad: float
    pitch_rad: float
    roll_deg: float
    pitch_deg: float


class ImuHostModule(EventHostModule):
    """Subscribe to telemetry.imu_raw and publish processed IMU state."""

    module_name = "imu"

    def __init__(self, bus: EventBus) -> None:
        self._accel_bias = np.zeros(3, dtype=float)
        self._gyro_bias = np.zeros(3, dtype=float)
        super().__init__(bus)

    def subscriptions(self) -> List[str]:
        return ["telemetry.imu_raw"]

    def set_biases(self, accel_bias, gyro_bias) -> None:
        self._accel_bias = np.asarray(accel_bias, dtype=float)
        self._gyro_bias = np.asarray(gyro_bias, dtype=float)

    def _on_imu_raw(self, msg: dict) -> None:
        ts_ms = msg.get("ts_ms")
        imu = msg.get("imu", {})

        online = imu.get("online", False)
        ok = imu.get("ok", False)

        if not online or not ok:
            self._bus.publish(
                "imu.state",
                ImuState(
                    ts_ms=ts_ms,
                    online=online,
                    ok=ok,
                    ax_g=0.0, ay_g=0.0, az_g=0.0,
                    gx_dps=0.0, gy_dps=0.0, gz_dps=0.0,
                    temp_c=float(imu.get("temp_c", 0.0)),
                    acc_mag_g=0.0,
                    roll_rad=0.0, pitch_rad=0.0,
                    roll_deg=0.0, pitch_deg=0.0,
                ),
            )
            return

        acc = np.array([
            float(imu.get("ax_g", 0.0)),
            float(imu.get("ay_g", 0.0)),
            float(imu.get("az_g", 0.0)),
        ]) - self._accel_bias

        gyro = np.array([
            float(imu.get("gx_dps", 0.0)),
            float(imu.get("gy_dps", 0.0)),
            float(imu.get("gz_dps", 0.0)),
        ]) - self._gyro_bias

        ax, ay, az = acc
        gx, gy, gz = gyro

        acc_mag = np.linalg.norm(acc)
        roll_rad = np.arctan2(ay, az)
        pitch_rad = np.arctan2(-ax, np.sqrt(ay * ay + az * az))

        roll_deg = np.degrees(roll_rad)
        pitch_deg = np.degrees(pitch_rad)

        state = ImuState(
            ts_ms=ts_ms,
            online=online,
            ok=ok,
            ax_g=float(ax),
            ay_g=float(ay),
            az_g=float(az),
            gx_dps=float(gx),
            gy_dps=float(gy),
            gz_dps=float(gz),
            temp_c=float(imu.get("temp_c", 0.0)),
            acc_mag_g=float(acc_mag),
            roll_rad=float(roll_rad),
            pitch_rad=float(pitch_rad),
            roll_deg=float(roll_deg),
            pitch_deg=float(pitch_deg),
        )

        self._bus.publish("imu.state", state)
