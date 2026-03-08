# mara_host/api/sensor_base.py
"""
Base class for telemetry-based sensors.

Provides common functionality for sensors that receive data via telemetry:
- Automatic telemetry subscription
- Callback management
- Last reading caching

Example:
    @dataclass
    class IMUReading:
        ax: float
        ay: float
        az: float

    class IMU(TelemetrySensor[IMUReading]):
        telemetry_topic = "telemetry.imu"

        def _parse_reading(self, data: dict) -> IMUReading:
            return IMUReading(
                ax=data.get("ax", 0.0),
                ay=data.get("ay", 0.0),
                az=data.get("az", 0.0),
            )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Generic, Optional, TypeVar

if TYPE_CHECKING:
    from ..robot import Robot

# Type variable for the reading type
T = TypeVar("T")


class TelemetrySensor(ABC, Generic[T]):
    """
    Base class for sensors that receive telemetry updates.

    This class handles the common patterns for telemetry-based sensors:
    - Subscribing to telemetry topics on the event bus
    - Managing callbacks for reading updates
    - Caching the last reading for synchronous access

    Subclasses must implement:
    - telemetry_topic: Class attribute specifying the event bus topic
    - _parse_reading(): Method to convert raw telemetry dict to typed reading

    Attributes:
        telemetry_topic: Event bus topic to subscribe to (e.g., "telemetry.imu")

    Example:
        class DistanceSensor(TelemetrySensor[DistanceReading]):
            telemetry_topic = "telemetry.distance"

            def _parse_reading(self, data: dict) -> DistanceReading:
                return DistanceReading(
                    distance_cm=data.get("distance_cm", 0.0),
                    ok=data.get("ok", False),
                )

        # Usage
        sensor = DistanceSensor(robot, sensor_id=0)
        print(f"Distance: {sensor.reading.distance_cm} cm")

        @sensor.on_reading
        def handle_reading(reading: DistanceReading):
            print(f"New reading: {reading}")
    """

    telemetry_topic: str = ""

    def __init__(
        self,
        robot: "Robot",
        sensor_id: int = 0,
        auto_subscribe: bool = True,
    ) -> None:
        """
        Initialize the sensor.

        Args:
            robot: Connected Robot instance
            sensor_id: Sensor identifier for multi-instance sensors
            auto_subscribe: Whether to subscribe to telemetry immediately
        """
        self._robot = robot
        self._sensor_id = sensor_id
        self._last_reading: Optional[T] = None
        self._callbacks: list[Callable[[T], None]] = []
        self._subscribed = False

        if auto_subscribe and self.telemetry_topic:
            self._subscribe()

    @property
    def robot(self) -> "Robot":
        """Access the robot instance."""
        return self._robot

    @property
    def client(self):
        """Access underlying MaraClient."""
        return self._robot.client

    @property
    def sensor_id(self) -> int:
        """Sensor identifier."""
        return self._sensor_id

    @property
    def reading(self) -> Optional[T]:
        """
        Last received reading.

        Returns None if no reading has been received yet.
        """
        return self._last_reading

    @property
    def has_reading(self) -> bool:
        """Whether a reading has been received."""
        return self._last_reading is not None

    @abstractmethod
    def _parse_reading(self, data: dict) -> T:
        """
        Parse raw telemetry dict into typed reading.

        Args:
            data: Raw telemetry data from event bus

        Returns:
            Parsed reading object
        """
        ...

    def _filter_telemetry(self, data: dict) -> bool:
        """
        Filter telemetry data for this sensor instance.

        Override this method for sensors that need to filter by sensor_id
        or other criteria.

        Args:
            data: Raw telemetry data

        Returns:
            True if this data is for this sensor instance
        """
        # Default: accept all data
        return True

    def _subscribe(self) -> None:
        """Subscribe to telemetry topic."""
        if self._subscribed:
            return

        topic = self._get_topic()
        self._robot.on(topic, self._on_telemetry)
        self._subscribed = True

    def _get_topic(self) -> str:
        """
        Get the telemetry topic to subscribe to.

        Override this for sensors with dynamic topics (e.g., per-sensor-id).
        """
        return self.telemetry_topic

    def _on_telemetry(self, data: dict) -> None:
        """Handle incoming telemetry data."""
        # Filter for this sensor instance
        if not self._filter_telemetry(data):
            return

        # Parse the reading
        try:
            reading = self._parse_reading(data)
        except Exception:
            return  # Silently ignore parse errors

        # Cache the reading
        self._last_reading = reading

        # Notify callbacks
        self._notify_callbacks(reading)

    def _notify_callbacks(self, reading: T) -> None:
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(reading)
            except Exception:
                pass  # Don't let callback errors break telemetry

    def on_reading(
        self, callback: Callable[[T], None]
    ) -> Callable[[T], None]:
        """
        Register a callback for reading updates.

        Can be used as a decorator:

            @sensor.on_reading
            def handle_reading(reading):
                print(f"New reading: {reading}")

        Or called directly:

            sensor.on_reading(handle_reading)

        Args:
            callback: Function called with reading on each update

        Returns:
            The callback (for decorator usage)
        """
        self._callbacks.append(callback)
        return callback

    def on_update(self, callback: Callable[[T], None]) -> None:
        """
        Register a callback for reading updates.

        Alias for on_reading() for backward compatibility.

        Args:
            callback: Function called with reading on each update
        """
        self.on_reading(callback)

    def remove_callback(self, callback: Callable[[T], None]) -> bool:
        """
        Remove a previously registered callback.

        Args:
            callback: The callback to remove

        Returns:
            True if callback was found and removed
        """
        try:
            self._callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def clear_callbacks(self) -> None:
        """Remove all registered callbacks."""
        self._callbacks.clear()
