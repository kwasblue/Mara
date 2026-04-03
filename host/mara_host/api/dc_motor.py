# mara_host/api/dc_motor.py
"""
DC motor control with PWM speed.

Example:
    from mara_host import Robot, DCMotor

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

    Internally uses MotorService for state tracking and communication.

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
        self._motor_id = motor_id

    @property
    def _service(self):
        """Use shared service from Robot (lazy access)."""
        return self._robot.motor_service

    @property
    def motor_id(self) -> int:
        """Motor identifier."""
        return self._motor_id

    @property
    def client(self):
        """Access underlying client."""
        return self._robot.client

    @property
    def current_speed(self) -> float:
        """Last commanded speed (-1.0 to 1.0)."""
        state = self._service.get_state(self._motor_id)
        return state.speed

    @property
    def is_moving(self) -> bool:
        """Whether motor is currently commanded to move."""
        return self.current_speed != 0.0

    async def set_speed(self, speed: float) -> None:
        """
        Set motor speed.

        Args:
            speed: Normalized speed from -1.0 (full reverse) to 1.0 (full forward)

        Raises:
            ValueError: If speed is outside [-1.0, 1.0] range
            RuntimeError: If command fails
        """
        if speed < -1.0 or speed > 1.0:
            raise ValueError(f"Speed {speed} must be between -1.0 and 1.0")

        result = await self._service.set_speed(self._motor_id, speed)
        if not result.ok:
            raise RuntimeError(result.error)

    async def stop(self) -> None:
        """
        Stop the motor (coast).

        Motor will coast to a stop with no active braking.
        """
        result = await self._service.stop(self._motor_id)
        if not result.ok:
            raise RuntimeError(result.error)

    async def brake(self) -> None:
        """
        Stop the motor with active braking.

        Uses motor driver's brake command to short motor windings,
        providing rapid deceleration compared to coast stop.
        """
        result = await self._service.brake(self._motor_id)
        if not result.ok:
            raise RuntimeError(result.error)

    async def set_speed_percent(self, percent: float) -> None:
        """
        Set motor speed as percentage.

        Args:
            percent: Speed from -100 to 100

        Convenience method for those who prefer percentage notation.
        """
        await self.set_speed(percent / 100.0)

    def __repr__(self) -> str:
        speed = self.current_speed
        direction = "fwd" if speed > 0 else "rev" if speed < 0 else "stopped"
        return f"DCMotor(id={self._motor_id}, {direction}, speed={speed:.2f})"
