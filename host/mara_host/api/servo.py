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

    Internally uses ServoService for state tracking and communication.

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
        from ..services.control.servo_service import ServoService

        self._robot = robot
        self._servo_id = servo_id
        self._channel = channel
        self._min_us = min_us
        self._max_us = max_us
        self._min_angle = min_angle
        self._max_angle = max_angle

        # Create/get service instance
        self._service = ServoService(robot.client)
        # Pre-configure this servo
        self._service.configure(
            servo_id=servo_id,
            channel=channel,
            min_angle=min_angle,
            max_angle=max_angle,
            min_us=min_us,
            max_us=max_us,
        )

    @property
    def servo_id(self) -> int:
        """Servo identifier."""
        return self._servo_id

    @property
    def channel(self) -> int:
        """PWM channel."""
        return self._channel

    @property
    def min_us(self) -> int:
        """Minimum pulse width."""
        return self._min_us

    @property
    def max_us(self) -> int:
        """Maximum pulse width."""
        return self._max_us

    @property
    def min_angle(self) -> float:
        """Minimum angle."""
        return self._min_angle

    @property
    def max_angle(self) -> float:
        """Maximum angle."""
        return self._max_angle

    @property
    def client(self):
        """Access underlying client."""
        return self._robot.client

    @property
    def is_attached(self) -> bool:
        """Whether the servo is attached."""
        state = self._service.get_state(self._servo_id)
        return state.attached

    @property
    def current_angle(self) -> Optional[float]:
        """Last commanded angle (None if never set)."""
        state = self._service.get_state(self._servo_id)
        return state.angle if state.attached else None

    async def attach(self) -> None:
        """
        Attach the servo to its PWM channel.

        Must be called before setting angles.

        Raises:
            RuntimeError: If attach fails
        """
        result = await self._service.attach(
            servo_id=self._servo_id,
            channel=self._channel,
            min_us=self._min_us,
            max_us=self._max_us,
        )
        if not result.ok:
            raise RuntimeError(result.error)

    async def detach(self) -> None:
        """
        Detach the servo from its PWM channel.

        The servo will no longer hold its position.

        Raises:
            RuntimeError: If detach fails
        """
        result = await self._service.detach(self._servo_id)
        if not result.ok:
            raise RuntimeError(result.error)

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
            RuntimeError: If command fails
        """
        if angle < self._min_angle or angle > self._max_angle:
            raise ValueError(
                f"Angle {angle} outside range [{self._min_angle}, {self._max_angle}]"
            )

        if auto_attach and not self.is_attached:
            await self.attach()

        result = await self._service.set_angle(
            servo_id=self._servo_id,
            angle=angle,
            duration_ms=duration_ms,
            clamp=False,  # We already validated
        )
        if not result.ok:
            raise RuntimeError(result.error)

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
        ratio = (angle - self._min_angle) / (self._max_angle - self._min_angle)
        return int(self._min_us + ratio * (self._max_us - self._min_us))

    def pulse_to_angle(self, pulse_us: int) -> float:
        """Convert pulse width to angle."""
        ratio = (pulse_us - self._min_us) / (self._max_us - self._min_us)
        return self._min_angle + ratio * (self._max_angle - self._min_angle)

    def __repr__(self) -> str:
        status = "attached" if self.is_attached else "detached"
        angle = self.current_angle
        angle_str = f"{angle:.1f}" if angle is not None else "?"
        return f"Servo(id={self._servo_id}, {status}, angle={angle_str})"
