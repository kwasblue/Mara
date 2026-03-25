# mara_host/services/control/servo_service.py
"""
Servo control service.

Provides high-level control for servo motors with angle management.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
import asyncio

from mara_host.core.result import ServiceResult
from mara_host.core.utils import clamp as clamp_value
from mara_host.services.control.service_base import ConfigurableService

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class ServoConfig:
    """Configuration for a servo."""

    servo_id: int
    channel: int = 0  # GPIO channel/pin
    min_angle: float = 0.0
    max_angle: float = 180.0
    min_us: int = 500
    max_us: int = 2500
    inverted: bool = False


@dataclass
class ServoState:
    """Current state of a servo."""

    servo_id: int
    angle: float = 90.0
    attached: bool = False


class ServoService(ConfigurableService[ServoConfig, ServoState]):
    """
    Service for servo motor control.

    Manages servo attachment, angle control, and movement sequences.

    Example:
        servo_svc = ServoService(client)

        # Attach and configure
        await servo_svc.attach(0, channel=13)

        # Set angle
        await servo_svc.set_angle(0, 45)

        # Sweep
        await servo_svc.sweep(0, start=0, end=180, step=10)

        # Detach when done
        await servo_svc.detach(0)
    """

    config_class = ServoConfig
    state_class = ServoState
    id_field = "servo_id"

    def configure(
        self,
        servo_id: int,
        channel: int,
        min_angle: float = 0.0,
        max_angle: float = 180.0,
        min_us: int = 500,
        max_us: int = 2500,
        inverted: bool = False,
    ) -> ServoConfig:
        """
        Configure a servo.

        Args:
            servo_id: Servo ID (0-15)
            channel: GPIO channel/pin
            min_angle: Minimum angle in degrees
            max_angle: Maximum angle in degrees
            min_us: Minimum pulse width (microseconds)
            max_us: Maximum pulse width (microseconds)
            inverted: If True, invert angle direction

        Returns:
            ServoConfig
        """
        config = ServoConfig(
            servo_id=servo_id,
            channel=channel,
            min_angle=min_angle,
            max_angle=max_angle,
            min_us=min_us,
            max_us=max_us,
            inverted=inverted,
        )
        self._configs[servo_id] = config
        return config

    def get_attached_servos(self) -> list[int]:
        """Get list of attached servo IDs."""
        return [sid for sid, state in self._states.items() if state.attached]

    async def attach(
        self,
        servo_id: int,
        channel: int,
        min_us: int = 500,
        max_us: int = 2500,
        initial_angle: Optional[float] = None,
    ) -> ServiceResult:
        """
        Attach a servo to a GPIO channel.

        Args:
            servo_id: Servo ID (0-15)
            channel: GPIO channel/pin
            min_us: Minimum pulse width (microseconds)
            max_us: Maximum pulse width (microseconds)
            initial_angle: Initial angle to set (optional)

        Returns:
            ServiceResult
        """
        # Configure if not already configured
        if servo_id not in self._configs:
            self.configure(servo_id, channel, min_us=min_us, max_us=max_us)
        else:
            config = self._configs[servo_id]
            config.channel = channel
            config.min_us = min_us
            config.max_us = max_us

        ok, error = await self.client.send_reliable(
            "CMD_SERVO_ATTACH",
            {
                "servo_id": servo_id,
                "channel": channel,
                "min_us": min_us,
                "max_us": max_us,
            },
        )

        if ok:
            state = self.get_state(servo_id)
            state.attached = True

            # Set initial angle if specified
            if initial_angle is not None:
                await self.set_angle(servo_id, initial_angle)

            return ServiceResult.success(data={"servo_id": servo_id, "channel": channel, "pin": channel})
        else:
            return ServiceResult.failure(error=error or f"Failed to attach servo {servo_id}")

    async def detach(self, servo_id: int) -> ServiceResult:
        """
        Detach a servo.

        Args:
            servo_id: Servo ID

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_SERVO_DETACH",
            {"servo_id": servo_id},
        )

        if ok:
            state = self.get_state(servo_id)
            state.attached = False
            return ServiceResult.success(data={"servo_id": servo_id})
        else:
            return ServiceResult.failure(error=error or f"Failed to detach servo {servo_id}")

    async def detach_all(self) -> ServiceResult:
        """
        Detach all attached servos.

        Returns:
            ServiceResult
        """
        errors = []
        for servo_id in self.get_attached_servos():
            result = await self.detach(servo_id)
            if not result.ok:
                errors.append(f"Servo {servo_id}: {result.error}")

        if errors:
            return ServiceResult.failure(error="; ".join(errors))
        return ServiceResult.success()

    async def set_angle(
        self,
        servo_id: int,
        angle: float,
        duration_ms: int = 0,
        clamp: bool = True,
        request_ack: bool = True,
    ) -> ServiceResult:
        """
        Set servo angle.

        Args:
            servo_id: Servo ID
            angle: Target angle in degrees
            duration_ms: Movement duration (0 = immediate)
            clamp: If True, clamp to configured limits
            request_ack: If True, wait for ACK (reliable). If False, fire-and-forget (fast).

        Returns:
            ServiceResult (always success if request_ack=False)
        """
        config = self.get_config(servo_id)

        # Apply clamping
        if clamp and config:
            angle = clamp_value(angle, config.min_angle, config.max_angle)

        # Apply inversion
        if config and config.inverted:
            angle = config.max_angle - (angle - config.min_angle)

        payload = {
            "servo_id": servo_id,
            "angle_deg": angle,
            "duration_ms": duration_ms,
        }

        if request_ack:
            ok, error = await self.client.send_reliable("CMD_SERVO_SET_ANGLE", payload)
            if not ok:
                return ServiceResult.failure(error=error or f"Failed to set servo {servo_id} angle")
        else:
            # Fire-and-forget - don't wait for ACK
            await self.client.send_auto("CMD_SERVO_SET_ANGLE", payload)

        # Update local state
        state = self.get_state(servo_id)
        state.angle = angle
        return ServiceResult.success(data={"servo_id": servo_id, "angle": angle})

    async def center(self, servo_id: int, duration_ms: int = 0) -> ServiceResult:
        """
        Center a servo (move to middle of range).

        Args:
            servo_id: Servo ID
            duration_ms: Movement duration

        Returns:
            ServiceResult
        """
        config = self.get_config(servo_id)
        if config:
            center_angle = (config.min_angle + config.max_angle) / 2
        else:
            center_angle = 90.0

        return await self.set_angle(servo_id, center_angle, duration_ms)

    async def set_pulse(
        self,
        servo_id: int,
        pulse_us: int,
        request_ack: bool = True,
    ) -> ServiceResult:
        """
        Set raw pulse width in microseconds.

        Args:
            servo_id: Servo ID
            pulse_us: Pulse width in microseconds
            request_ack: If True, wait for ACK

        Returns:
            ServiceResult
        """
        payload = {"servo_id": servo_id, "pulse_us": pulse_us}

        if request_ack:
            ok, error = await self.client.send_reliable("CMD_SERVO_SET_PULSE", payload)
            if not ok:
                return ServiceResult.failure(error=error or f"Failed to set servo {servo_id} pulse")
        else:
            await self.client.send_auto("CMD_SERVO_SET_PULSE", payload)

        return ServiceResult.success(data={"servo_id": servo_id, "pulse_us": pulse_us})

    async def sweep(
        self,
        servo_id: int,
        start: float = 0,
        end: float = 180,
        step: float = 10,
        delay_s: float = 0.1,
    ) -> ServiceResult:
        """
        Sweep a servo through a range of angles.

        Args:
            servo_id: Servo ID
            start: Starting angle
            end: Ending angle
            step: Angle increment per step
            delay_s: Delay between steps

        Returns:
            ServiceResult
        """
        state = self.get_state(servo_id)
        if not state.attached:
            return ServiceResult.failure(error=f"Servo {servo_id} not attached")

        direction = 1 if end > start else -1
        step = abs(step) * direction
        angle = start

        while (direction > 0 and angle <= end) or (direction < 0 and angle >= end):
            result = await self.set_angle(servo_id, angle)
            if not result.ok:
                return result
            await asyncio.sleep(delay_s)
            angle += step

        return ServiceResult.success(
            data={"servo_id": servo_id, "start": start, "end": end}
        )

    async def set_multiple(
        self,
        angles: dict[int, float],
        duration_ms: int = 0,
    ) -> ServiceResult:
        """
        Set multiple servo angles simultaneously.

        Args:
            angles: Dict of {servo_id: angle}
            duration_ms: Movement duration

        Returns:
            ServiceResult
        """
        errors = []
        results = {}

        for servo_id, angle in angles.items():
            result = await self.set_angle(servo_id, angle, duration_ms)
            if result.ok:
                results[servo_id] = angle
            else:
                errors.append(f"Servo {servo_id}: {result.error}")

        if errors:
            return ServiceResult.failure(error="; ".join(errors))
        return ServiceResult.success(data={"angles": results})
