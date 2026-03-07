# mara_host/api/servo.py
"""
Servo motor control.

Example:
    from mara_host import Robot, Servo

    async with Robot("/dev/ttyUSB0") as robot:
        servo = Servo(robot, servo_id=0, channel=0)
        await servo.attach()
        await servo.set_angle(90)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..robot import Robot


class Servo:
    """
    Servo motor controller.

    Controls standard hobby servos via PWM. Supports angle-based positioning
    and optional smooth transitions.

    Args:
        robot: Connected Robot instance
        servo_id: Servo identifier (0-based index)
        channel: PWM channel on the MCU
        min_us: Minimum pulse width in microseconds (default: 500)
        max_us: Maximum pulse width in microseconds (default: 2500)
        min_angle: Angle corresponding to min_us (default: 0)
        max_angle: Angle corresponding to max_us (default: 180)

    Example:
        servo = Servo(robot, servo_id=0, channel=0)
        await servo.attach()

        # Set to center position
        await servo.set_angle(90)

        # Sweep with duration
        await servo.set_angle(0, duration_ms=500)
        await servo.set_angle(180, duration_ms=500)

        # Detach when done
        await servo.detach()
    """

    def __init__(
        self,
        robot: Robot,
        servo_id: int = 0,
        channel: int = 0,
        min_us: int = 500,
        max_us: int = 2500,
        min_angle: float = 0.0,
        max_angle: float = 180.0,
    ) -> None:
        self._robot = robot
        self.servo_id = servo_id
        self.channel = channel
        self.min_us = min_us
        self.max_us = max_us
        self.min_angle = min_angle
        self.max_angle = max_angle
        self._attached = False
        self._current_angle: Optional[float] = None

    @property
    def client(self):
        """Access underlying client."""
        return self._robot.client

    @property
    def is_attached(self) -> bool:
        """Whether the servo is attached."""
        return self._attached

    @property
    def current_angle(self) -> Optional[float]:
        """Last commanded angle (None if never set)."""
        return self._current_angle

    async def attach(self) -> None:
        """
        Attach the servo to its PWM channel.

        Must be called before setting angles.
        """
        await self.client.cmd_servo_attach(
            servo_id=self.servo_id,
            channel=self.channel,
            min_us=self.min_us,
            max_us=self.max_us,
        )
        self._attached = True

    async def detach(self) -> None:
        """
        Detach the servo from its PWM channel.

        The servo will no longer hold its position.
        """
        await self.client.cmd_servo_detach(servo_id=self.servo_id)
        self._attached = False

    async def set_angle(
        self,
        angle: float,
        duration_ms: int = 0,
        auto_attach: bool = True,
    ) -> None:
        """
        Set servo to specified angle.

        Args:
            angle: Target angle in degrees
            duration_ms: Transition duration (0 = immediate)
            auto_attach: Automatically attach if not attached

        Raises:
            ValueError: If angle is outside configured range
        """
        if angle < self.min_angle or angle > self.max_angle:
            raise ValueError(
                f"Angle {angle} outside range [{self.min_angle}, {self.max_angle}]"
            )

        if auto_attach and not self._attached:
            await self.attach()

        await self.client.cmd_servo_set_angle(
            servo_id=self.servo_id,
            angle_deg=float(angle),
            duration_ms=int(duration_ms),
        )

        self._current_angle = angle

    async def set_pulse(self, pulse_us: int) -> None:
        """
        Set servo by raw pulse width.

        Args:
            pulse_us: Pulse width in microseconds

        For advanced use when direct pulse control is needed.
        This converts pulse to angle and uses set_angle internally.
        """
        angle = self.pulse_to_angle(pulse_us)
        await self.set_angle(angle)

    def angle_to_pulse(self, angle: float) -> int:
        """Convert angle to pulse width."""
        ratio = (angle - self.min_angle) / (self.max_angle - self.min_angle)
        return int(self.min_us + ratio * (self.max_us - self.min_us))

    def pulse_to_angle(self, pulse_us: int) -> float:
        """Convert pulse width to angle."""
        ratio = (pulse_us - self.min_us) / (self.max_us - self.min_us)
        return self.min_angle + ratio * (self.max_angle - self.min_angle)

    def __repr__(self) -> str:
        status = "attached" if self._attached else "detached"
        angle_str = f"{self._current_angle:.1f}°" if self._current_angle else "?"
        return f"Servo(id={self.servo_id}, {status}, angle={angle_str})"
