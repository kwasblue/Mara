# mara_host/api/ultrasonic.py
"""
Ultrasonic distance sensor interface.

Example:
    from mara_host import Robot, Ultrasonic

    async with Robot("/dev/ttyUSB0") as robot:
        sensor = Ultrasonic(robot, sensor_id=0)
        await sensor.attach()

        # Read distance
        print(f"Distance: {sensor.distance_cm:.1f} cm")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .sensor_base import TelemetrySensor

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class UltrasonicReading:
    """Ultrasonic sensor reading."""

    sensor_id: int
    distance_cm: float
    ok: bool
    ts_ms: int


class Ultrasonic(TelemetrySensor[UltrasonicReading]):
    """
    Ultrasonic distance sensor interface.

    Reads distance measurements from ultrasonic sensors (e.g., HC-SR04).
    Distance data is received via telemetry and cached for synchronous access.

    Args:
        robot: Connected Robot instance
        sensor_id: Sensor identifier (0-based index)
        max_distance_cm: Maximum valid distance reading

    Example:
        sensor = Ultrasonic(robot, sensor_id=0)
        await sensor.attach()

        # Read cached distance
        if sensor.is_ok:
            print(f"Distance: {sensor.distance_cm:.1f} cm")
            print(f"Distance: {sensor.distance_m:.2f} m")

        # Trigger a new reading
        await sensor.read()

        # Subscribe to updates
        def on_distance(reading: UltrasonicReading):
            print(f"Distance: {reading.distance_cm:.1f} cm")

        sensor.on_update(on_distance)
    """

    telemetry_topic = "telemetry.ultrasonic"

    def __init__(
        self,
        robot: "Robot",
        sensor_id: int = 0,
        max_distance_cm: float = 400.0,
    ) -> None:
        self.max_distance_cm = max_distance_cm

        self._attached = False
        self._distance_cm: float = 0.0
        self._ok = False
        self._ts_ms: int = 0

        # Initialize base class
        super().__init__(robot, sensor_id=sensor_id, auto_subscribe=True)

    def _filter_telemetry(self, data: dict) -> bool:
        """Filter telemetry by sensor_id."""
        data_sensor_id = data.get("sensor_id", self._sensor_id)
        return data_sensor_id == self._sensor_id

    def _parse_reading(self, data: dict) -> UltrasonicReading:
        """Parse raw telemetry into UltrasonicReading."""
        self._distance_cm = data.get("distance_cm", self._distance_cm)
        self._ok = data.get("ok", self._ok)
        self._ts_ms = data.get("ts_ms", self._ts_ms)

        return UltrasonicReading(
            sensor_id=self._sensor_id,
            distance_cm=self._distance_cm,
            ok=self._ok,
            ts_ms=self._ts_ms,
        )

    @property
    def distance_cm(self) -> float:
        """Distance in centimeters."""
        return self._distance_cm

    @property
    def distance_m(self) -> float:
        """Distance in meters."""
        return self._distance_cm / 100.0

    @property
    def distance_inches(self) -> float:
        """Distance in inches."""
        return self._distance_cm / 2.54

    @property
    def is_ok(self) -> bool:
        """Whether the last reading was valid."""
        return self._ok

    @property
    def is_attached(self) -> bool:
        """Whether the sensor is attached."""
        return self._attached

    @property
    def is_in_range(self) -> bool:
        """Whether reading is within valid range."""
        return self._ok and 0 < self._distance_cm < self.max_distance_cm

    async def attach(self) -> None:
        """Attach the ultrasonic sensor."""
        await self.client.cmd_ultrasonic_attach(sensor_id=self._sensor_id)
        self._attached = True

    async def read(self) -> None:
        """Trigger a new distance reading."""
        await self.client.cmd_ultrasonic_read(sensor_id=self._sensor_id)

    def __repr__(self) -> str:
        status = "attached" if self._attached else "detached"
        if self._ok:
            return f"Ultrasonic(id={self._sensor_id}, {status}, {self._distance_cm:.1f}cm)"
        return f"Ultrasonic(id={self._sensor_id}, {status}, no reading)"
