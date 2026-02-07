# robot_host/api/pid_controller.py
"""
PID controller for DC motor velocity control - Public API.

Example:
    from robot_host import Robot, PIDController

    async with Robot("/dev/ttyUSB0") as robot:
        pid = PIDController(robot, motor_id=0)
        await pid.set_gains(kp=1.0, ki=0.1, kd=0.01)
        await pid.enable()
        await pid.set_target(10.0)  # rad/s
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class PIDGains:
    """PID controller gains."""
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0


class PIDController:
    """
    Velocity PID controller for DC motors.

    Public API for motor velocity control. Wraps the firmware's built-in
    velocity PID control for DC motors, providing closed-loop velocity tracking.

    Args:
        robot: Connected Robot instance
        motor_id: Motor identifier (0-based index)

    Example:
        pid = PIDController(robot, motor_id=0)

        # Configure gains
        await pid.set_gains(kp=1.0, ki=0.1, kd=0.01)

        # Enable closed-loop control
        await pid.enable()

        # Set target velocity
        await pid.set_target(10.0)  # rad/s

        # Stop and disable
        await pid.stop()
        await pid.disable()
    """

    def __init__(
        self,
        robot: Robot,
        motor_id: int = 0,
    ) -> None:
        self._robot = robot
        self.motor_id = motor_id
        self._enabled = False
        self._target_omega: float = 0.0
        self._gains = PIDGains()

    @property
    def is_enabled(self) -> bool:
        """Whether PID control is enabled."""
        return self._enabled

    @property
    def target_omega(self) -> float:
        """Current target angular velocity in rad/s."""
        return self._target_omega

    @property
    def gains(self) -> PIDGains:
        """Current PID gains."""
        return self._gains

    async def enable(self) -> None:
        """
        Enable closed-loop velocity PID control.

        Motor will track the target velocity using the configured gains.
        """
        await self._robot.client.cmd_dc_vel_pid_enable(
            motor_id=self.motor_id,
            enable=True,
        )
        self._enabled = True

    async def disable(self) -> None:
        """
        Disable closed-loop velocity PID control.

        Motor reverts to open-loop speed control.
        """
        await self._robot.client.cmd_dc_vel_pid_enable(
            motor_id=self.motor_id,
            enable=False,
        )
        self._enabled = False

    async def set_gains(
        self,
        kp: float,
        ki: float = 0.0,
        kd: float = 0.0,
    ) -> None:
        """
        Set PID controller gains.

        Args:
            kp: Proportional gain
            ki: Integral gain (default: 0.0)
            kd: Derivative gain (default: 0.0)
        """
        await self._robot.client.cmd_dc_set_vel_gains(
            motor_id=self.motor_id,
            kp=kp,
            ki=ki,
            kd=kd,
        )
        self._gains = PIDGains(kp=kp, ki=ki, kd=kd)

    async def set_target(self, omega: float) -> None:
        """
        Set target angular velocity.

        Args:
            omega: Target velocity in rad/s (positive = forward)
        """
        await self._robot.client.cmd_dc_set_vel_target(
            motor_id=self.motor_id,
            omega=omega,
        )
        self._target_omega = omega

    async def stop(self) -> None:
        """Stop the motor (set target velocity to zero)."""
        await self.set_target(0.0)

    def __repr__(self) -> str:
        status = "enabled" if self._enabled else "disabled"
        return (
            f"PIDController(motor={self.motor_id}, {status}, "
            f"target={self._target_omega:.2f} rad/s)"
        )
