# mara_host/api/stepper.py
"""
Stepper motor control.

Example:
    from mara_host import Robot, Stepper

    async with Robot("/dev/ttyUSB0") as robot:
        motor = Stepper(robot, motor_id=0, steps_per_rev=200)
        await motor.enable()
        await motor.move(steps=100, speed_rps=0.5)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..robot import Robot


class Stepper:
    """
    Stepper motor controller.

    Provides high-level control of stepper motors connected to the MCU.
    Handles conversion between user-friendly units (revolutions per second)
    and MCU units (steps per second).

    Args:
        robot: Connected Robot instance
        motor_id: Motor identifier (0-based index)
        steps_per_rev: Steps per full revolution (e.g., 200 for 1.8° motor)

    Example:
        motor = Stepper(robot, motor_id=0, steps_per_rev=200)

        # Enable and move
        await motor.enable()
        await motor.move(steps=400, speed_rps=1.0)  # 2 revolutions at 1 rev/sec

        # Move by angle
        await motor.move_degrees(180)  # Half revolution

        # Disable when done
        await motor.disable()
    """

    def __init__(
        self,
        robot: Robot,
        motor_id: int = 0,
        steps_per_rev: int = 200,
    ) -> None:
        self._robot = robot
        self.motor_id = motor_id
        self.steps_per_rev = steps_per_rev
        self._enabled = False
        self._position = 0  # Track position in steps

    @property
    def client(self):
        """Access underlying client."""
        return self._robot.client

    @property
    def is_enabled(self) -> bool:
        """Whether the stepper motor driver is enabled."""
        return self._enabled

    @property
    def position(self) -> int:
        """Current position in steps (tracked locally)."""
        return self._position

    @property
    def position_degrees(self) -> float:
        """Current position in degrees."""
        return (self._position / self.steps_per_rev) * 360.0

    @property
    def position_revolutions(self) -> float:
        """Current position in revolutions."""
        return self._position / self.steps_per_rev

    async def enable(self) -> None:
        """
        Enable the stepper motor driver.

        Raises:
            RuntimeError: If enable fails
        """
        result = await self.client.cmd_stepper_enable(
            motor_id=self.motor_id,
            enable=True,
        )
        if result is not None and hasattr(result, "ok") and not result.ok:
            raise RuntimeError(getattr(result, "error", None) or "Stepper enable failed")
        self._enabled = True

    async def disable(self) -> None:
        """
        Disable the stepper motor driver (releases holding torque).

        Raises:
            RuntimeError: If disable fails
        """
        result = await self.client.cmd_stepper_enable(
            motor_id=self.motor_id,
            enable=False,
        )
        if result is not None and hasattr(result, "ok") and not result.ok:
            raise RuntimeError(getattr(result, "error", None) or "Stepper disable failed")
        self._enabled = False

    async def move(
        self,
        steps: int,
        speed_rps: float = 1.0,
        auto_enable: bool = True,
    ) -> None:
        """
        Move relative number of steps.

        Args:
            steps: Number of steps to move (positive = forward, negative = reverse)
            speed_rps: Speed in revolutions per second
            auto_enable: Automatically enable motor if not enabled
        """
        if auto_enable and not self._enabled:
            await self.enable()

        speed_steps_s = abs(speed_rps) * self.steps_per_rev

        result = await self.client.cmd_stepper_move_rel(
            motor_id=self.motor_id,
            steps=int(steps),
            speed_steps_s=float(speed_steps_s),
        )
        if result is not None and hasattr(result, "ok") and not result.ok:
            raise RuntimeError(getattr(result, "error", None) or "Stepper move failed")

        self._position += steps

    async def move_degrees(
        self,
        degrees: float,
        speed_rps: float = 1.0,
        auto_enable: bool = True,
    ) -> None:
        """
        Move by angle in degrees.

        Args:
            degrees: Angle to move (positive = forward)
            speed_rps: Speed in revolutions per second
            auto_enable: Automatically enable motor if not enabled
        """
        steps = int(round((degrees / 360.0) * self.steps_per_rev))
        await self.move(steps, speed_rps, auto_enable)

    async def move_revolutions(
        self,
        revolutions: float,
        speed_rps: float = 1.0,
        auto_enable: bool = True,
    ) -> None:
        """
        Move by number of revolutions.

        Args:
            revolutions: Number of revolutions (positive = forward)
            speed_rps: Speed in revolutions per second
            auto_enable: Automatically enable motor if not enabled
        """
        steps = int(round(revolutions * self.steps_per_rev))
        await self.move(steps, speed_rps, auto_enable)

    async def stop(self) -> None:
        """
        Stop motor immediately.

        Raises:
            RuntimeError: If stop fails
        """
        result = await self.client.cmd_stepper_stop(motor_id=self.motor_id)
        if result is not None and hasattr(result, "ok") and not result.ok:
            raise RuntimeError(getattr(result, "error", None) or "Stepper stop failed")

    def reset_position(self, position: int = 0) -> None:
        """
        Reset the local position counter.

        Args:
            position: New position value (default: 0)
        """
        self._position = position

    def __repr__(self) -> str:
        status = "enabled" if self._enabled else "disabled"
        return f"Stepper(motor_id={self.motor_id}, {status}, pos={self._position})"
