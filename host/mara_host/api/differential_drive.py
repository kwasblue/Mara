# mara_host/api/differential_drive.py
"""
Motion primitives for differential drive robots - Public API.

This is the public interface for differential drive control. For internal use,
see mara_host.motor.motion.MotionHostModule.

Example:
    from mara_host import Robot, DifferentialDrive

    async with Robot("/dev/ttyUSB0") as robot:
        drive = DifferentialDrive(robot, wheel_radius=0.05, wheel_base=0.2)
        await drive.drive_straight(distance=1.0, speed=0.3)
        await drive.turn(angle_deg=90, speed=1.0)
        await drive.arc(radius=0.5, angle_deg=180)
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class DriveConfig:
    """Configuration for differential drive kinematics."""
    wheel_radius: float = 0.05  # meters
    wheel_base: float = 0.2     # meters (distance between wheels)
    max_linear_vel: float = 1.0  # m/s
    max_angular_vel: float = 3.0  # rad/s


class DifferentialDrive:
    """
    Motion primitives for differential drive robots.

    Public API for differential drive control. Wraps the internal MotionHostModule
    and provides high-level motion commands using velocity streaming.

    Args:
        robot: Connected Robot instance
        wheel_radius: Wheel radius in meters (default: 0.05)
        wheel_base: Distance between wheels in meters (default: 0.2)
        max_linear_vel: Maximum linear velocity in m/s (default: 1.0)
        max_angular_vel: Maximum angular velocity in rad/s (default: 3.0)
        control_rate_hz: Internal control loop rate (default: 50.0)

    Example:
        drive = DifferentialDrive(robot, wheel_radius=0.05, wheel_base=0.2)

        # Drive forward 1 meter at 0.3 m/s
        await drive.drive_straight(distance=1.0, speed=0.3)

        # Turn 90 degrees in place at 1.0 rad/s
        await drive.turn(angle_deg=90, speed=1.0)

        # Drive in an arc (radius 0.5m, sweep 180 degrees)
        await drive.arc(radius=0.5, angle_deg=180)

        # Direct velocity control
        await drive.set_velocity(vx=0.3, omega=0.5)
        await drive.stop()
    """

    def __init__(
        self,
        robot: Robot,
        wheel_radius: float = 0.05,
        wheel_base: float = 0.2,
        max_linear_vel: float = 1.0,
        max_angular_vel: float = 3.0,
        control_rate_hz: float = 50.0,
    ) -> None:
        from ..motor.motion import MotionHostModule

        self._robot = robot
        self._module = MotionHostModule(robot.bus, robot.client)
        self._config = DriveConfig(
            wheel_radius=wheel_radius,
            wheel_base=wheel_base,
            max_linear_vel=max_linear_vel,
            max_angular_vel=max_angular_vel,
        )
        self._control_rate_hz = control_rate_hz
        self._control_period = 1.0 / control_rate_hz
        self._is_moving = False
        self._last_vx = 0.0
        self._last_omega = 0.0

    @property
    def config(self) -> DriveConfig:
        """Drive configuration parameters."""
        return self._config

    @property
    def is_moving(self) -> bool:
        """Whether the robot is currently executing a motion command."""
        return self._is_moving

    @property
    def current_velocity(self) -> tuple[float, float]:
        """Last commanded velocity (vx, omega)."""
        return (self._last_vx, self._last_omega)

    def _clamp_velocity(self, vx: float, omega: float) -> tuple[float, float]:
        """Clamp velocities to configured limits."""
        vx = max(-self._config.max_linear_vel, min(vx, self._config.max_linear_vel))
        omega = max(-self._config.max_angular_vel, min(omega, self._config.max_angular_vel))
        return vx, omega

    async def set_velocity(self, vx: float, omega: float) -> None:
        """
        Set robot velocity directly.

        Args:
            vx: Linear velocity in m/s (positive = forward)
            omega: Angular velocity in rad/s (positive = counter-clockwise)
        """
        vx, omega = self._clamp_velocity(vx, omega)
        await self._module.set_velocity(vx, omega)
        self._last_vx = vx
        self._last_omega = omega
        self._is_moving = (vx != 0.0 or omega != 0.0)

    async def stop(self) -> None:
        """Stop all motion."""
        await self._module.stop()
        self._last_vx = 0.0
        self._last_omega = 0.0
        self._is_moving = False

    async def drive_straight(
        self,
        distance: float,
        speed: float = 0.3,
    ) -> None:
        """
        Drive straight for a given distance.

        Args:
            distance: Distance in meters (positive = forward, negative = backward)
            speed: Speed in m/s (always positive, direction from distance sign)

        Note:
            This is open-loop and depends on timing accuracy.
            For precise positioning, use encoder feedback.
        """
        if distance == 0.0:
            return

        speed = min(abs(speed), self._config.max_linear_vel)
        vx = speed if distance > 0 else -speed
        duration = abs(distance) / speed

        self._is_moving = True
        try:
            await self._execute_timed_motion(vx, 0.0, duration)
        finally:
            await self.stop()

    async def turn(
        self,
        angle_deg: float,
        speed: float = 1.0,
    ) -> None:
        """
        Turn in place by a given angle.

        Args:
            angle_deg: Angle in degrees (positive = counter-clockwise)
            speed: Angular speed in rad/s (always positive)

        Note:
            This is open-loop and depends on timing accuracy.
            For precise turns, use IMU or encoder feedback.
        """
        if angle_deg == 0.0:
            return

        angle_rad = math.radians(angle_deg)
        speed = min(abs(speed), self._config.max_angular_vel)
        omega = speed if angle_rad > 0 else -speed
        duration = abs(angle_rad) / speed

        self._is_moving = True
        try:
            await self._execute_timed_motion(0.0, omega, duration)
        finally:
            await self.stop()

    async def arc(
        self,
        radius: float,
        angle_deg: float,
        speed: float = 0.2,
    ) -> None:
        """
        Drive in an arc (curved path).

        Args:
            radius: Arc radius in meters (must be positive)
            angle_deg: Arc angle in degrees (positive = counter-clockwise)
            speed: Linear speed in m/s (magnitude; robot always moves forward)

        The robot drives along a circular arc of the given radius,
        sweeping through the specified angle. The robot always travels
        forward; use a negative angle to curve right instead of left.

        Note:
            To drive backward in an arc, use set_velocity() directly with
            negative linear velocity.
        """
        if angle_deg == 0.0 or radius <= 0:
            return

        angle_rad = math.radians(angle_deg)
        speed = min(abs(speed), self._config.max_linear_vel)

        # For an arc: omega = vx / radius
        omega = speed / radius
        omega = min(omega, self._config.max_angular_vel)

        # Adjust linear speed if omega was clamped
        if omega == self._config.max_angular_vel:
            speed = omega * radius

        # Apply direction from angle sign
        if angle_rad < 0:
            omega = -omega

        # Arc length = radius * |angle|, duration = arc_length / speed
        arc_length = radius * abs(angle_rad)
        duration = arc_length / speed

        self._is_moving = True
        try:
            await self._execute_timed_motion(speed, omega, duration)
        finally:
            await self.stop()

    async def _execute_timed_motion(
        self,
        vx: float,
        omega: float,
        duration: float,
    ) -> None:
        """Execute a motion for a fixed duration using velocity streaming."""
        import time
        start_time = time.monotonic()
        end_time = start_time + duration
        while time.monotonic() < end_time:
            await self.set_velocity(vx, omega)
            await asyncio.sleep(self._control_period)

    def __repr__(self) -> str:
        status = "moving" if self._is_moving else "stopped"
        return (
            f"DifferentialDrive({status}, "
            f"wheel_r={self._config.wheel_radius}m, "
            f"wheel_base={self._config.wheel_base}m)"
        )
