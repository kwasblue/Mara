# mara_host/services/control/ultrasonic_service.py
"""
Ultrasonic sensor service.

Provides high-level control for ultrasonic distance sensors.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Any

from mara_host.core.result import ServiceResult
from mara_host.services.control.service_base import ConfigurableService
from mara_host.command.payloads import (
    UltrasonicAttachPayload,
    UltrasonicDetachPayload,
    UltrasonicReadPayload,
)
from mara_host.services.types import (
    UltrasonicAttachResponse,
    UltrasonicDetachResponse,
    UltrasonicReadResponse,
)

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
    distance_cm: Optional[float] = None  # Last measured distance
    attached: bool = False
    degraded: bool = False
    last_error: Optional[str] = None


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
        payload = UltrasonicAttachPayload(
            sensor_id=sensor_id,
            trig_pin=trig_pin,
            echo_pin=echo_pin,
            max_distance_cm=max_distance_cm,
        )
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            self.configure(sensor_id, trig_pin, echo_pin, max_distance_cm)
            state = self.get_state(sensor_id)
            state.attached = True
            state.degraded = False
            state.last_error = None
            return ServiceResult.success(
                data=UltrasonicAttachResponse(
                    sensor_id=sensor_id,
                    trig_pin=trig_pin,
                    echo_pin=echo_pin,
                )
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
        payload = UltrasonicDetachPayload(sensor_id=sensor_id)
        ok, error = await self.client.send_reliable(payload._cmd, payload.to_dict())

        if ok:
            state = self.get_state(sensor_id)
            state.attached = False
            state.distance_cm = None
            state.degraded = False
            state.last_error = None
            return ServiceResult.success(data=UltrasonicDetachResponse(sensor_id=sensor_id))
        else:
            return ServiceResult.failure(
                error=error or f"Failed to detach ultrasonic sensor {sensor_id}"
            )

    async def read(self, sensor_id: int) -> ServiceResult:
        """
        Request distance reading from MCU.

        A no-echo ultrasonic timeout is treated as an expected degraded hardware
        state rather than a generic transport/software failure.

        Args:
            sensor_id: Sensor ID

        Returns:
            ServiceResult
        """
        loop = asyncio.get_running_loop()
        ack_future: asyncio.Future[Any] = loop.create_future()
        topic = "cmd.CMD_ULTRASONIC_READ"

        def _handler(data: Any) -> None:
            if not ack_future.done():
                ack_future.set_result(data)

        cmd_payload = UltrasonicReadPayload(sensor_id=sensor_id)
        self.client.bus.subscribe(topic, _handler)
        try:
            ok, error = await self.client.send_reliable(cmd_payload._cmd, cmd_payload.to_dict())

            # Always wait for ACK payload - even if ok=False, the MCU may have
            # returned useful information (e.g., error="read_failed" for no-echo)
            ack_data: dict[str, Any] | None
            try:
                ack_data = await asyncio.wait_for(ack_future, timeout=0.1)
            except asyncio.TimeoutError:
                ack_data = None
        finally:
            self.client.bus.unsubscribe(topic, _handler)

        state = self.get_state(sensor_id)
        response = dict(ack_data or {"sensor_id": sensor_id})
        distance_cm = response.get("distance_cm")
        ack_error = response.get("error")

        # Check for degraded hardware state first (no-echo timeout from MCU)
        # The MCU returns ok=False with error="read_failed" when sensor is
        # attached but no echo was measured - this is expected sensor behavior
        if ack_error == "read_failed":
            state.attached = bool(response.get("attached", state.attached or self.has_config(sensor_id)))
            state.distance_cm = None
            state.degraded = True
            state.last_error = ack_error
            degraded_response = {
                **response,
                "sensor_id": sensor_id,
                "distance_cm": None,
                "degraded": True,
                "expected": True,
                "reason": "no_echo",
                "message": f"Ultrasonic sensor {sensor_id} attached but no echo was measured; treating as degraded hardware state.",
            }
            return ServiceResult.success(data=degraded_response)

        # Transport failure (no ACK or unrecognized error)
        if not ok:
            state.last_error = error or ack_error
            return ServiceResult.failure(
                error=error or ack_error or f"Failed to read ultrasonic sensor {sensor_id}",
                data=response,
            )

        # Normal success path
        state.attached = bool(response.get("attached", state.attached or self.has_config(sensor_id)))
        state.distance_cm = float(distance_cm) if distance_cm is not None else state.distance_cm
        state.degraded = False
        state.last_error = None
        return ServiceResult.success(data=response)

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

    def update_reading(self, sensor_id: int, distance_cm: Optional[float]) -> None:
        """
        Update last reading (called from telemetry handler).

        Args:
            sensor_id: Sensor ID
            distance_cm: Measured distance in centimeters, or None when unavailable
        """
        state = self.get_state(sensor_id)
        state.distance_cm = distance_cm
        state.degraded = distance_cm is None
        state.last_error = None if distance_cm is not None else "read_failed"
