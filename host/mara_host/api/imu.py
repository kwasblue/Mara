# mara_host/api/imu.py
"""
Inertial Measurement Unit (IMU) interface.

Example:
    from mara_host import Robot, IMU

    async with Robot("/dev/ttyUSB0") as robot:
        imu = IMU(robot)

        # Read latest values
        print(f"Roll: {imu.roll_deg:.1f}°, Pitch: {imu.pitch_deg:.1f}°")
        print(f"Accel: {imu.acceleration}")

        # Subscribe to updates
        imu.on_update(lambda data: print(f"IMU: {data}"))
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Tuple

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class IMUReading:
    """IMU telemetry reading."""
    ts_ms: int
    online: bool
    ok: bool

    # Accelerometer (g)
    ax: float
    ay: float
    az: float

    # Gyroscope (deg/s)
    gx: float
    gy: float
    gz: float

    # Temperature
    temp_c: float

    # Derived orientation (degrees)
    roll_deg: float
    pitch_deg: float


class IMU:
    """
    Inertial Measurement Unit interface.

    Provides access to accelerometer and gyroscope data from the MCU's IMU.
    Data is received via telemetry and cached for synchronous access.

    Args:
        robot: Connected Robot instance
        apply_bias: Whether to apply bias correction (default: True)

    Example:
        imu = IMU(robot)

        # Check if IMU is online
        if imu.is_online:
            # Read accelerometer (in g)
            ax, ay, az = imu.acceleration

            # Read gyroscope (in deg/s)
            gx, gy, gz = imu.gyro

            # Read derived orientation
            print(f"Roll: {imu.roll_deg:.1f}°")
            print(f"Pitch: {imu.pitch_deg:.1f}°")

        # Subscribe to updates
        def on_imu(reading: IMUReading):
            print(f"Orientation: roll={reading.roll_deg:.1f}, pitch={reading.pitch_deg:.1f}")

        imu.on_update(on_imu)

        # Calibrate bias (keep IMU still)
        await imu.calibrate_bias(samples=100)
    """

    def __init__(
        self,
        robot: Robot,
        apply_bias: bool = True,
    ) -> None:
        self._robot = robot
        self._apply_bias = apply_bias

        # Bias correction
        self._accel_bias = (0.0, 0.0, 0.0)
        self._gyro_bias = (0.0, 0.0, 0.0)

        # Cached state
        self._online = False
        self._ok = False
        self._ts_ms = 0
        self._ax = 0.0
        self._ay = 0.0
        self._az = 0.0
        self._gx = 0.0
        self._gy = 0.0
        self._gz = 0.0
        self._temp_c = 0.0

        self._callbacks: list[Callable[[IMUReading], None]] = []

        # Subscribe to telemetry
        robot.on("telemetry.imu", self._on_telemetry)

    def _on_telemetry(self, data: dict) -> None:
        """Handle incoming IMU telemetry."""
        self._online = data.get("online", False)
        self._ok = data.get("ok", False)
        self._ts_ms = data.get("ts_ms", 0)

        # Raw values
        ax = data.get("ax_g", 0.0)
        ay = data.get("ay_g", 0.0)
        az = data.get("az_g", 0.0)
        gx = data.get("gx_dps", 0.0)
        gy = data.get("gy_dps", 0.0)
        gz = data.get("gz_dps", 0.0)

        # Apply bias correction
        if self._apply_bias:
            ax -= self._accel_bias[0]
            ay -= self._accel_bias[1]
            az -= self._accel_bias[2]
            gx -= self._gyro_bias[0]
            gy -= self._gyro_bias[1]
            gz -= self._gyro_bias[2]

        self._ax, self._ay, self._az = ax, ay, az
        self._gx, self._gy, self._gz = gx, gy, gz
        self._temp_c = data.get("temp_c", 0.0)

        # Notify callbacks
        if self._callbacks:
            reading = IMUReading(
                ts_ms=self._ts_ms,
                online=self._online,
                ok=self._ok,
                ax=self._ax,
                ay=self._ay,
                az=self._az,
                gx=self._gx,
                gy=self._gy,
                gz=self._gz,
                temp_c=self._temp_c,
                roll_deg=self.roll_deg,
                pitch_deg=self.pitch_deg,
            )
            for callback in self._callbacks:
                try:
                    callback(reading)
                except Exception:
                    pass

    @property
    def is_online(self) -> bool:
        """Whether the IMU is online and responding."""
        return self._online

    @property
    def is_ok(self) -> bool:
        """Whether the IMU data is valid."""
        return self._ok

    @property
    def acceleration(self) -> Tuple[float, float, float]:
        """Acceleration vector (ax, ay, az) in g."""
        return (self._ax, self._ay, self._az)

    @property
    def gyro(self) -> Tuple[float, float, float]:
        """Gyroscope vector (gx, gy, gz) in degrees/second."""
        return (self._gx, self._gy, self._gz)

    @property
    def temperature(self) -> float:
        """IMU temperature in Celsius."""
        return self._temp_c

    @property
    def roll_deg(self) -> float:
        """Roll angle in degrees (derived from accelerometer)."""
        return math.degrees(math.atan2(self._ay, self._az))

    @property
    def pitch_deg(self) -> float:
        """Pitch angle in degrees (derived from accelerometer)."""
        return math.degrees(
            math.atan2(-self._ax, math.sqrt(self._ay**2 + self._az**2))
        )

    @property
    def roll_rad(self) -> float:
        """Roll angle in radians."""
        return math.atan2(self._ay, self._az)

    @property
    def pitch_rad(self) -> float:
        """Pitch angle in radians."""
        return math.atan2(-self._ax, math.sqrt(self._ay**2 + self._az**2))

    def set_bias(
        self,
        accel_bias: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        gyro_bias: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> None:
        """
        Set bias correction values.

        Args:
            accel_bias: (ax, ay, az) accelerometer bias in g
            gyro_bias: (gx, gy, gz) gyroscope bias in deg/s
        """
        self._accel_bias = accel_bias
        self._gyro_bias = gyro_bias

    def on_update(self, callback: Callable[[IMUReading], None]) -> None:
        """
        Register callback for IMU updates.

        Args:
            callback: Function called with IMUReading on each update
        """
        self._callbacks.append(callback)

    def __repr__(self) -> str:
        status = "online" if self._online else "offline"
        return f"IMU({status}, roll={self.roll_deg:.1f}°, pitch={self.pitch_deg:.1f}°)"
