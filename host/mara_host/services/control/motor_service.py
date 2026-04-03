# mara_host/services/control/motor_service.py
"""
DC motor control service.

Provides high-level control for DC motors with safety limits.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mara_host.core.result import ServiceResult
from mara_host.core.utils import clamp as clamp_value
from mara_host.services.control.service_base import ConfigurableService
from mara_host.command.payloads import DcSetSpeedPayload, DcStopPayload
from mara_host.services.types import MotorSetSpeedResponse, MotorStopResponse

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class MotorConfig:
    """Configuration for a DC motor."""

    motor_id: int
    min_speed: float = -1.0  # -100% to -1.0
    max_speed: float = 1.0  # 1.0 to 100%
    inverted: bool = False


@dataclass
class MotorState:
    """Current state of a motor."""

    motor_id: int
    speed: float = 0.0  # -1.0 to 1.0
    enabled: bool = True


class MotorService(ConfigurableService[MotorConfig, MotorState]):
    """
    Service for DC motor control.

    Manages individual motor speed commands with configurable
    limits and inversion.

    Example:
        motor_svc = MotorService(client)

        # Set motor speed
        await motor_svc.set_speed(0, 0.5)  # 50% forward

        # Configure motor
        motor_svc.configure(0, max_speed=0.8, inverted=True)

        # Stop all
        await motor_svc.stop_all()
    """

    config_class = MotorConfig
    state_class = MotorState
    id_field = "motor_id"

    def configure(
        self,
        motor_id: int,
        min_speed: float = -1.0,
        max_speed: float = 1.0,
        inverted: bool = False,
    ) -> None:
        """
        Configure a motor.

        Args:
            motor_id: Motor ID (0-3)
            min_speed: Minimum speed limit (-1.0 to 0)
            max_speed: Maximum speed limit (0 to 1.0)
            inverted: If True, invert speed sign
        """
        self._configs[motor_id] = MotorConfig(
            motor_id=motor_id,
            min_speed=clamp_value(min_speed, -1.0, 0),
            max_speed=clamp_value(max_speed, 0, 1.0),
            inverted=inverted,
        )

    async def set_speed(
        self,
        motor_id: int,
        speed: float,
        clamp: bool = True,
        request_ack: bool = True,
    ) -> ServiceResult:
        """
        Set motor speed.

        Args:
            motor_id: Motor ID (0-3)
            speed: Speed from -1.0 to 1.0 (sign = direction)
            clamp: If True, clamp to configured limits
            request_ack: If True, wait for ACK (reliable). If False, fire-and-forget (fast).

        Returns:
            ServiceResult with success/failure (always success if request_ack=False)
        """
        config = self.get_config(motor_id)

        # Apply inversion
        if config.inverted:
            speed = -speed

        # Clamp to limits
        if clamp:
            speed = clamp_value(speed, config.min_speed, config.max_speed)

        payload = DcSetSpeedPayload(motor_id=motor_id, speed=speed)

        if request_ack:
            ok, error = await self.client.send_reliable(
                payload._cmd,
                payload.to_dict(),
            )
            if not ok:
                return ServiceResult.failure(error=error or f"Failed to set motor {motor_id} speed")
        else:
            # Fire-and-forget mode: command is sent without waiting for ACK.
            # This provides lower latency for high-rate control loops but means
            # errors are not reported back. The local state update below is
            # optimistic and may diverge from firmware state if the command fails.
            await self.client.send_auto(
                payload._cmd,
                payload.to_dict(),
            )

        # Update local state (optimistic - may diverge from firmware if fire-and-forget fails)
        state = self.get_state(motor_id)
        state.speed = speed
        return ServiceResult.success(data=MotorSetSpeedResponse(motor_id=motor_id, speed=speed))

    async def set_speed_percent(
        self,
        motor_id: int,
        percent: float,
        clamp: bool = True,
    ) -> ServiceResult:
        """
        Set motor speed as percentage (-100 to 100).

        Args:
            motor_id: Motor ID
            percent: Speed in percent (-100 to 100)
            clamp: If True, clamp to limits

        Returns:
            ServiceResult
        """
        speed = percent / 100.0
        return await self.set_speed(motor_id, speed, clamp)

    async def stop(self, motor_id: int) -> ServiceResult:
        """
        Stop a specific motor (coast).

        Args:
            motor_id: Motor ID

        Returns:
            ServiceResult
        """
        payload = DcStopPayload(motor_id=motor_id)
        ok, error = await self.client.send_reliable(
            payload._cmd,
            payload.to_dict(),
        )

        if ok:
            state = self.get_state(motor_id)
            state.speed = 0.0
            return ServiceResult.success(data=MotorStopResponse(motor_id=motor_id, brake=False))
        else:
            return ServiceResult.failure(error=error or f"Failed to stop motor {motor_id}")

    async def brake(self, motor_id: int) -> ServiceResult:
        """
        Active brake a motor (short windings).

        Args:
            motor_id: Motor ID

        Returns:
            ServiceResult
        """
        # Note: brake parameter not in schema yet, using extended payload
        payload = {**DcStopPayload(motor_id=motor_id).to_dict(), "brake": True}
        ok, error = await self.client.send_reliable("CMD_DC_STOP", payload)

        if ok:
            state = self.get_state(motor_id)
            state.speed = 0.0
            return ServiceResult.success(data=MotorStopResponse(motor_id=motor_id, brake=True))
        else:
            return ServiceResult.failure(error=error or f"Failed to brake motor {motor_id}")

    async def stop_all(self) -> ServiceResult:
        """
        Stop all motors.

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable("CMD_STOP", {})

        if ok:
            for state in self._states.values():
                state.speed = 0.0
            return ServiceResult.success()
        else:
            return ServiceResult.failure(error=error or "Failed to stop all motors")

    async def set_differential_drive(
        self,
        left_speed: float,
        right_speed: float,
        left_motor: int = 0,
        right_motor: int = 1,
    ) -> ServiceResult:
        """
        Set differential drive motor speeds.

        Args:
            left_speed: Left motor speed (-1.0 to 1.0)
            right_speed: Right motor speed (-1.0 to 1.0)
            left_motor: Left motor ID (default 0)
            right_motor: Right motor ID (default 1)

        Returns:
            ServiceResult
        """
        left_result = await self.set_speed(left_motor, left_speed)
        if not left_result.ok:
            return left_result

        right_result = await self.set_speed(right_motor, right_speed)
        if not right_result.ok:
            # Try to stop left motor on failure - log if stop also fails
            stop_result = await self.stop(left_motor)
            if not stop_result.ok:
                # Chain the errors so caller knows left motor may still be running
                return ServiceResult.failure(
                    error=f"{right_result.error}; additionally, failed to stop left motor: {stop_result.error}"
                )
            return right_result

        return ServiceResult.success(
            data={
                "left": MotorSetSpeedResponse(motor_id=left_motor, speed=left_speed),
                "right": MotorSetSpeedResponse(motor_id=right_motor, speed=right_speed),
            }
        )

    def compute_diff_drive(
        self,
        vx: float,
        omega: float,
        track_width: float = 0.2,
        wheel_radius: float = 0.05,
        max_speed: float = 1.0,
    ) -> tuple[float, float]:
        """
        Compute differential drive wheel speeds from velocity.

        Args:
            vx: Linear velocity (m/s)
            omega: Angular velocity (rad/s)
            track_width: Distance between wheels (m)
            wheel_radius: Wheel radius (m)
            max_speed: Maximum motor speed

        Returns:
            (left_speed, right_speed) normalized to [-max_speed, max_speed]
        """
        # Compute wheel angular velocities (rad/s)
        left_omega = (vx - (omega * track_width / 2)) / wheel_radius
        right_omega = (vx + (omega * track_width / 2)) / wheel_radius

        # Find max for normalization - normalize such that the larger wheel
        # speed maps to max_speed while preserving the ratio between them
        max_omega = max(abs(left_omega), abs(right_omega), 1e-6)

        # Normalize to [-max_speed, max_speed] preserving ratio
        left_speed = (left_omega / max_omega) * max_speed
        right_speed = (right_omega / max_omega) * max_speed

        return left_speed, right_speed
