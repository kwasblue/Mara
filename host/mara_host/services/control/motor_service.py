# mara_host/services/control/motor_service.py
"""
DC motor control service.

Provides high-level control for DC motors with safety limits.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mara_host.core.result import ServiceResult
from mara_host.services.control.service_base import ConfigurableService

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
            min_speed=max(-1.0, min(0, min_speed)),
            max_speed=max(0, min(1.0, max_speed)),
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
            speed = max(config.min_speed, min(config.max_speed, speed))

        if request_ack:
            ok, error = await self.client.send_reliable(
                "CMD_DC_SET_SPEED",
                {"motor_id": motor_id, "speed": speed},
            )
            if not ok:
                return ServiceResult.failure(error=error or f"Failed to set motor {motor_id} speed")
        else:
            # Fire-and-forget - don't wait for ACK
            await self.client.send_auto(
                "CMD_DC_SET_SPEED",
                {"motor_id": motor_id, "speed": speed},
            )

        # Update local state
        state = self.get_state(motor_id)
        state.speed = speed
        return ServiceResult.success(data={"motor_id": motor_id, "speed": speed})

    # Backwards compatibility alias
    async def set_speed_fast(
        self,
        motor_id: int,
        speed: float,
        clamp: bool = True,
    ) -> ServiceResult:
        """Deprecated: Use set_speed(..., request_ack=False) instead."""
        return await self.set_speed(motor_id, speed, clamp, request_ack=False)

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
        Stop a specific motor.

        Args:
            motor_id: Motor ID

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_DC_STOP",
            {"motor_id": motor_id},
        )

        if ok:
            state = self.get_state(motor_id)
            state.speed = 0.0
            return ServiceResult.success(data={"motor_id": motor_id})
        else:
            return ServiceResult.failure(error=error or f"Failed to stop motor {motor_id}")

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
            # Try to stop left motor on failure
            await self.stop(left_motor)
            return right_result

        return ServiceResult.success(
            data={
                "left": {"motor_id": left_motor, "speed": left_speed},
                "right": {"motor_id": right_motor, "speed": right_speed},
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

        # Find max for normalization
        max_omega = max(abs(left_omega), abs(right_omega), 1e-6)

        # Normalize to [-1, 1] then scale to max_speed
        # Assuming max wheel omega corresponds to max_speed=1.0
        # This is a simplified model
        left_speed = (left_omega / max_omega) * max_speed if max_omega > 1e-6 else 0
        right_speed = (right_omega / max_omega) * max_speed if max_omega > 1e-6 else 0

        # Preserve magnitude relationship
        scale = min(1.0, max_speed / max(abs(left_speed), abs(right_speed), 1e-6))
        left_speed *= scale
        right_speed *= scale

        return left_speed, right_speed
