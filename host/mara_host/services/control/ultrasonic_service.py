# mara_host/services/control/ultrasonic_service.py
"""
Ultrasonic sensor service.

Provides high-level control for ultrasonic distance sensors.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult
from mara_host.services.control.service_base import ConfigurableService

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class UltrasonicConfig:
    """Configuration for an ultrasonic sensor."""

    sensor_id: int
    trig_pin: int = 0  # Trigger pin
    echo_pin: int = 0  # Echo pin
    max_distance_cm: float = 400.0  # Maximum measurable distance


@dataclass
class UltrasonicState:
    """Current state of an ultrasonic sensor."""

    sensor_id: int
    distance_cm: float = 0.0  # Last measured distance
    attached: bool = False


class UltrasonicService(ConfigurableService[UltrasonicConfig, UltrasonicState]):
    """
    Service for ultrasonic sensor control.

    Manages ultrasonic distance sensors with attach/detach and read operations.

    Example:
        us_svc = UltrasonicService(client)

        # Attach sensor to pins
        await us_svc.attach(0, trig_pin=12, echo_pin=14)

        # Read distance
        result = await us_svc.read(0)

        # Detach when done
        await us_svc.detach(0)
    """

    config_class = UltrasonicConfig
    state_class = UltrasonicState
    id_field = "sensor_id"

    def configure(
        self,
        sensor_id: int,
        trig_pin: int,
        echo_pin: int,
        max_distance_cm: float = 400.0,
    ) -> UltrasonicConfig:
        """
        Configure an ultrasonic sensor locally.

        Args:
            sensor_id: Sensor ID (0-3)
            trig_pin: Trigger GPIO pin
            echo_pin: Echo GPIO pin
            max_distance_cm: Maximum measurable distance

        Returns:
            UltrasonicConfig
        """
        config = UltrasonicConfig(
            sensor_id=sensor_id,
            trig_pin=trig_pin,
            echo_pin=echo_pin,
            max_distance_cm=max_distance_cm,
        )
        self._configs[sensor_id] = config
        return config

    def get_attached_sensors(self) -> list[int]:
        """Get list of attached sensor IDs."""
        return [sid for sid, state in self._states.items() if state.attached]

    @staticmethod
    def cm_to_meters(cm: float) -> float:
        """Convert centimeters to meters."""
        return cm / 100.0

    @staticmethod
    def cm_to_inches(cm: float) -> float:
        """Convert centimeters to inches."""
        return cm / 2.54

    async def attach(
        self,
        sensor_id: int,
        trig_pin: int,
        echo_pin: int,
        max_distance_cm: float = 400.0,
    ) -> ServiceResult:
        """
        Attach an ultrasonic sensor to GPIO pins.

        Args:
            sensor_id: Sensor ID (0-3)
            trig_pin: Trigger GPIO pin
            echo_pin: Echo GPIO pin
            max_distance_cm: Maximum measurable distance

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_ULTRASONIC_ATTACH",
            {
                "sensor_id": sensor_id,
                "trig_pin": trig_pin,
                "echo_pin": echo_pin,
                "max_distance_cm": max_distance_cm,
            },
        )

        if ok:
            self.configure(sensor_id, trig_pin, echo_pin, max_distance_cm)
            state = self.get_state(sensor_id)
            state.attached = True
            return ServiceResult.success(
                data={
                    "sensor_id": sensor_id,
                    "trig_pin": trig_pin,
                    "echo_pin": echo_pin,
                }
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to attach ultrasonic sensor {sensor_id}"
            )

    async def detach(self, sensor_id: int) -> ServiceResult:
        """
        Detach an ultrasonic sensor.

        Args:
            sensor_id: Sensor ID

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_ULTRASONIC_DETACH",
            {"sensor_id": sensor_id},
        )

        if ok:
            state = self.get_state(sensor_id)
            state.attached = False
            return ServiceResult.success(data={"sensor_id": sensor_id})
        else:
            return ServiceResult.failure(
                error=error or f"Failed to detach ultrasonic sensor {sensor_id}"
            )

    async def read(self, sensor_id: int) -> ServiceResult:
        """
        Request distance reading from MCU.

        Note: The actual value comes via telemetry.

        Args:
            sensor_id: Sensor ID

        Returns:
            ServiceResult
        """
        result = await self._send_reliable_with_ack_payload(
            "CMD_ULTRASONIC_READ",
            {"sensor_id": sensor_id},
            error_message=f"Failed to read ultrasonic sensor {sensor_id}",
        )

        if result.ok:
            return ServiceResult.success(data=result.data or {"sensor_id": sensor_id})
        else:
            return result

    async def detach_all(self) -> ServiceResult:
        """
        Detach all attached sensors.

        Returns:
            ServiceResult
        """
        errors = []
        for sensor_id in self.get_attached_sensors():
            result = await self.detach(sensor_id)
            if not result.ok:
                errors.append(f"Sensor {sensor_id}: {result.error}")

        if errors:
            return ServiceResult.failure(error="; ".join(errors))
        return ServiceResult.success()

    def update_reading(self, sensor_id: int, distance_cm: float) -> None:
        """
        Update last reading (called from telemetry handler).

        Args:
            sensor_id: Sensor ID
            distance_cm: Measured distance in centimeters
        """
        state = self.get_state(sensor_id)
        state.distance_cm = distance_cm
