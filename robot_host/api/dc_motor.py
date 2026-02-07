# robot_host/api/dc_motor.py
"""
DC motor control with PWM speed.

Example:
    from robot_host import Robot, DCMotor

    async with Robot("/dev/ttyUSB0") as robot:
        motor = DCMotor(robot, motor_id=0)
        await motor.set_speed(0.5)   # 50% forward
        await motor.set_speed(-0.5)  # 50% reverse
        await motor.stop()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..robot import Robot


class DCMotor:
    """
    DC motor controller with PWM speed control.

    Controls DC motors via H-bridge or motor driver. Speed is specified
    as a normalized value from -1.0 (full reverse) to 1.0 (full forward).

    Args:
        robot: Connected Robot instance
        motor_id: Motor identifier (0-based index)

    Example:
        motor = DCMotor(robot, motor_id=0)

        # Set speed (normalized -1.0 to 1.0)
        await motor.set_speed(0.75)   # 75% forward
        await motor.set_speed(-0.5)   # 50% reverse
        await motor.set_speed(0)      # Stop

        # Convenience methods
        await motor.stop()   # Coast to stop
        await motor.brake()  # Active braking
    """

    def __init__(
        self,
        robot: Robot,
        motor_id: int = 0,
    ) -> None:
        self._robot = robot
        self.motor_id = motor_id
        self._current_speed: float = 0.0

    @property
    def client(self):
        """Access underlying client."""
        return self._robot.client

    @property
    def current_speed(self) -> float:
        """Last commanded speed (-1.0 to 1.0)."""
        return self._current_speed

    @property
    def is_moving(self) -> bool:
        """Whether motor is currently commanded to move."""
        return self._current_speed != 0.0

    async def set_speed(self, speed: float) -> None:
        """
        Set motor speed.

        Args:
            speed: Normalized speed from -1.0 (full reverse) to 1.0 (full forward)

        Raises:
            ValueError: If speed is outside [-1.0, 1.0] range
        """
        if speed < -1.0 or speed > 1.0:
            raise ValueError(f"Speed {speed} must be between -1.0 and 1.0")

        await self.client.cmd_dc_set_speed(
            motor_id=self.motor_id,
            speed=float(speed),
        )
        self._current_speed = speed

    async def stop(self) -> None:
        """
        Stop the motor (coast).

        Motor will coast to a stop with no active braking.
        """
        await self.set_speed(0.0)

    async def brake(self) -> None:
        """
        Stop the motor with active braking.

        Uses motor driver's stop command.
        """
        await self.client.cmd_dc_stop(motor_id=self.motor_id)
        self._current_speed = 0.0

    async def set_speed_percent(self, percent: float) -> None:
        """
        Set motor speed as percentage.

        Args:
            percent: Speed from -100 to 100

        Convenience method for those who prefer percentage notation.
        """
        await self.set_speed(percent / 100.0)

    def __repr__(self) -> str:
        direction = "fwd" if self._current_speed > 0 else "rev" if self._current_speed < 0 else "stopped"
        return f"DCMotor(id={self.motor_id}, {direction}, speed={self._current_speed:.2f})"
