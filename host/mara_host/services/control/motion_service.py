# mara_host/services/control/motion_service.py
"""
Motion control service for velocity and trajectory commands.

Provides a high-level interface for robot motion control.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class Velocity:
    """Velocity command in robot frame."""

    vx: float  # Linear velocity (m/s)
    omega: float  # Angular velocity (rad/s)

    @classmethod
    def zero(cls) -> "Velocity":
        """Create zero velocity."""
        return cls(vx=0.0, omega=0.0)


class MotionService:
    """
    Service for robot motion control.

    Handles velocity commands and motion primitives.

    Example:
        motion = MotionService(client)

        # Set velocity (fire-and-forget for real-time)
        await motion.set_velocity(0.5, 0.0)  # Forward at 0.5 m/s

        # Rotate in place
        await motion.set_velocity(0.0, 0.5)  # Rotate at 0.5 rad/s

        # Stop motion
        await motion.stop()
    """

    def __init__(self, client: "MaraClient"):
        """
        Initialize motion service.

        Args:
            client: Connected MaraClient instance
        """
        self.client = client
        self._last_velocity = Velocity.zero()
        self._velocity_limit_linear = 1.0  # m/s
        self._velocity_limit_angular = 2.0  # rad/s

        # Rate limiting for GUI/joystick use
        # Pre-compute interval to avoid division in hot path
        self._rate_limit_hz = 50.0
        self._min_interval_s = 1.0 / self._rate_limit_hz
        self._last_send_time = 0.0

        # Re-entrancy protection: serialize concurrent velocity commands
        self._command_lock = asyncio.Lock()

    @property
    def last_velocity(self) -> Velocity:
        """Get the last commanded velocity."""
        return self._last_velocity

    @property
    def velocity_limit_linear(self) -> float:
        """Get linear velocity limit (m/s)."""
        return self._velocity_limit_linear

    @velocity_limit_linear.setter
    def velocity_limit_linear(self, value: float) -> None:
        """Set linear velocity limit (m/s)."""
        self._velocity_limit_linear = abs(value)

    @property
    def velocity_limit_angular(self) -> float:
        """Get angular velocity limit (rad/s)."""
        return self._velocity_limit_angular

    @velocity_limit_angular.setter
    def velocity_limit_angular(self, value: float) -> None:
        """Set angular velocity limit (rad/s)."""
        self._velocity_limit_angular = abs(value)

    @property
    def rate_limit_hz(self) -> float:
        """Get command rate limit (Hz)."""
        return self._rate_limit_hz

    @rate_limit_hz.setter
    def rate_limit_hz(self, value: float) -> None:
        """Set command rate limit (Hz)."""
        self._rate_limit_hz = max(1.0, abs(value))
        # Pre-compute interval to avoid division in hot path
        self._min_interval_s = 1.0 / self._rate_limit_hz

    def set_limits(
        self,
        linear: Optional[float] = None,
        angular: Optional[float] = None,
        rate_hz: Optional[float] = None,
    ) -> None:
        """
        Configure velocity and rate limits.

        Args:
            linear: Linear velocity limit in m/s (default: unchanged)
            angular: Angular velocity limit in rad/s (default: unchanged)
            rate_hz: Command rate limit in Hz for GUI use (default: unchanged)

        Example:
            motion.set_limits(linear=0.5, angular=1.0, rate_hz=30)
        """
        if linear is not None:
            self._velocity_limit_linear = abs(linear)
        if angular is not None:
            self._velocity_limit_angular = abs(angular)
        if rate_hz is not None:
            self._rate_limit_hz = max(1.0, abs(rate_hz))
            self._min_interval_s = 1.0 / self._rate_limit_hz

    def _check_rate_limit(self) -> bool:
        """
        Check if rate limit allows sending a command.

        Returns:
            True if enough time has passed since last send

        Optimized: Uses pre-computed interval and time.monotonic() for lower overhead.
        """
        now = time.monotonic()
        if now - self._last_send_time >= self._min_interval_s:
            self._last_send_time = now
            return True
        return False

    async def set_velocity(
        self,
        vx: float,
        omega: float,
        clamp: bool = True,
        binary: bool = True,
        respect_rate_limit: bool = False,
    ) -> bool:
        """
        Set robot velocity (fire-and-forget for real-time control).

        Args:
            vx: Linear velocity in m/s (positive = forward)
            omega: Angular velocity in rad/s (positive = counter-clockwise)
            clamp: If True, clamp velocities to limits
            binary: If True, use binary encoding (lower latency for 50+ Hz).
                    All commands still flow through commander for event logging.
            respect_rate_limit: If True, skip command if rate limit exceeded.
                               Useful for GUI joystick input that may fire
                               faster than desired command rate.

        Returns:
            True if command was sent, False if skipped due to rate limit
        """
        # Check rate limit if requested (outside lock for fast rejection)
        if respect_rate_limit and not self._check_rate_limit():
            return False

        if clamp:
            vx = max(-self._velocity_limit_linear, min(self._velocity_limit_linear, vx))
            omega = max(
                -self._velocity_limit_angular, min(self._velocity_limit_angular, omega)
            )

        # Serialize concurrent velocity commands to prevent interleaving
        async with self._command_lock:
            # All commands flow through commander (binary or JSON)
            await self.client.send_stream(
                "CMD_SET_VEL",
                {"vx": vx, "omega": omega},
                request_ack=False,
                binary=binary,
            )

            self._last_velocity = Velocity(vx=vx, omega=omega)
        return True

    async def set_velocity_reliable(
        self,
        vx: float,
        omega: float,
        clamp: bool = True,
    ) -> ServiceResult:
        """
        Set robot velocity with acknowledgment.

        Use this when you need confirmation the command was received.

        Args:
            vx: Linear velocity in m/s
            omega: Angular velocity in rad/s
            clamp: If True, clamp velocities to limits

        Returns:
            ServiceResult with success/failure
        """
        if clamp:
            vx = max(-self._velocity_limit_linear, min(self._velocity_limit_linear, vx))
            omega = max(
                -self._velocity_limit_angular, min(self._velocity_limit_angular, omega)
            )

        # Serialize concurrent velocity commands
        async with self._command_lock:
            ok, error = await self.client.set_vel(vx, omega)
            self._last_velocity = Velocity(vx=vx, omega=omega)

        if ok:
            return ServiceResult.success(
                data={"vx": vx, "omega": omega},
            )
        else:
            return ServiceResult.failure(error=error or "Failed to set velocity")

    async def stop(self) -> ServiceResult:
        """
        Stop all motion (set velocity to zero).

        Returns:
            ServiceResult with success/failure
        """
        ok, error = await self.client.cmd_stop()

        if ok:
            self._last_velocity = Velocity.zero()
            return ServiceResult.success()
        else:
            return ServiceResult.failure(error=error or "Failed to stop")

    async def forward(self, speed: float = 0.5) -> None:
        """
        Move forward at specified speed.

        Args:
            speed: Forward speed in m/s
        """
        await self.set_velocity(abs(speed), 0.0)

    async def backward(self, speed: float = 0.5) -> None:
        """
        Move backward at specified speed.

        Args:
            speed: Backward speed in m/s
        """
        await self.set_velocity(-abs(speed), 0.0)

    async def rotate_left(self, speed: float = 0.5) -> None:
        """
        Rotate left (counter-clockwise) at specified speed.

        Args:
            speed: Angular speed in rad/s
        """
        await self.set_velocity(0.0, abs(speed))

    async def rotate_right(self, speed: float = 0.5) -> None:
        """
        Rotate right (clockwise) at specified speed.

        Args:
            speed: Angular speed in rad/s
        """
        await self.set_velocity(0.0, -abs(speed))

    def compute_arcade_drive(
        self,
        throttle: float,
        steering: float,
        max_linear: Optional[float] = None,
        max_angular: Optional[float] = None,
    ) -> Velocity:
        """
        Compute velocity from arcade-style joystick inputs.

        Args:
            throttle: Forward/backward input (-1.0 to 1.0)
            steering: Left/right input (-1.0 to 1.0)
            max_linear: Max linear velocity (defaults to velocity_limit_linear)
            max_angular: Max angular velocity (defaults to velocity_limit_angular)

        Returns:
            Velocity command
        """
        if max_linear is None:
            max_linear = self._velocity_limit_linear
        if max_angular is None:
            max_angular = self._velocity_limit_angular

        # Clamp inputs
        throttle = max(-1.0, min(1.0, throttle))
        steering = max(-1.0, min(1.0, steering))

        # Convert to velocity
        vx = throttle * max_linear
        omega = steering * max_angular

        return Velocity(vx=vx, omega=omega)

    async def arcade_drive(
        self,
        throttle: float,
        steering: float,
        max_linear: Optional[float] = None,
        max_angular: Optional[float] = None,
    ) -> None:
        """
        Set velocity from arcade-style joystick inputs.

        Args:
            throttle: Forward/backward input (-1.0 to 1.0)
            steering: Left/right input (-1.0 to 1.0)
            max_linear: Max linear velocity (uses limit if not specified)
            max_angular: Max angular velocity (uses limit if not specified)
        """
        vel = self.compute_arcade_drive(throttle, steering, max_linear, max_angular)
        await self.set_velocity(vel.vx, vel.omega, clamp=False)
