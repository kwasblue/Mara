# robot_host/api/encoder.py
"""
Quadrature encoder interface.

Example:
    from robot_host import Robot, Encoder

    async with Robot("/dev/ttyUSB0") as robot:
        encoder = Encoder(robot, encoder_id=0, pin_a=32, pin_b=33)
        await encoder.attach()

        # Read current count
        print(f"Ticks: {encoder.count}")

        # Subscribe to updates
        encoder.on_update(lambda e: print(f"Count: {e.count}"))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class EncoderReading:
    """Encoder telemetry reading."""
    encoder_id: int
    count: int
    velocity: float  # counts per second
    ts_ms: int


class Encoder:
    """
    Quadrature encoder interface.

    Reads quadrature encoder signals for position and velocity tracking.
    Position updates come via telemetry and are cached locally.

    Args:
        robot: Connected Robot instance
        encoder_id: Encoder identifier (0-based index)
        pin_a: GPIO pin for channel A
        pin_b: GPIO pin for channel B
        counts_per_rev: Encoder counts per revolution (for unit conversion)

    Example:
        encoder = Encoder(robot, encoder_id=0, pin_a=32, pin_b=33)
        await encoder.attach()

        # Access cached count (updated via telemetry)
        print(f"Position: {encoder.count} ticks")
        print(f"Revolutions: {encoder.revolutions:.2f}")

        # Subscribe to updates
        def on_encoder(reading: EncoderReading):
            print(f"Encoder {reading.encoder_id}: {reading.count}")

        encoder.on_update(on_encoder)

        # Reset to zero
        await encoder.reset()
    """

    def __init__(
        self,
        robot: Robot,
        encoder_id: int = 0,
        pin_a: int = 32,
        pin_b: int = 33,
        counts_per_rev: Optional[int] = None,
    ) -> None:
        self._robot = robot
        self.encoder_id = encoder_id
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.counts_per_rev = counts_per_rev

        self._attached = False
        self._count: int = 0
        self._velocity: float = 0.0
        self._ts_ms: int = 0
        self._callbacks: list[Callable[[EncoderReading], None]] = []

        # Subscribe to telemetry
        topic = f"telemetry.encoder{encoder_id}"
        robot.on(topic, self._on_telemetry)

    @property
    def client(self):
        """Access underlying client."""
        return self._robot.client

    @property
    def count(self) -> int:
        """Current encoder count (updated via telemetry)."""
        return self._count

    @property
    def velocity(self) -> float:
        """Current velocity in counts per second."""
        return self._velocity

    @property
    def revolutions(self) -> Optional[float]:
        """Current position in revolutions (if counts_per_rev is set)."""
        if self.counts_per_rev is None:
            return None
        return self._count / self.counts_per_rev

    @property
    def is_attached(self) -> bool:
        """Whether encoder is attached."""
        return self._attached

    def _on_telemetry(self, data: dict) -> None:
        """Handle incoming encoder telemetry."""
        self._count = data.get("ticks", self._count)
        self._velocity = data.get("velocity", self._velocity)
        self._ts_ms = data.get("ts_ms", self._ts_ms)

        # Notify callbacks
        if self._callbacks:
            reading = EncoderReading(
                encoder_id=self.encoder_id,
                count=self._count,
                velocity=self._velocity,
                ts_ms=self._ts_ms,
            )
            for callback in self._callbacks:
                try:
                    callback(reading)
                except Exception:
                    pass  # Don't let callback errors break telemetry

    async def attach(self) -> None:
        """
        Attach the encoder to its GPIO pins.

        Must be called before reading position.
        """
        await self.client.cmd_encoder_attach(
            encoder_id=self.encoder_id,
            pin_a=self.pin_a,
            pin_b=self.pin_b,
        )
        self._attached = True

    async def reset(self) -> None:
        """Reset encoder count to zero."""
        await self.client.cmd_encoder_reset(encoder_id=self.encoder_id)
        self._count = 0

    def on_update(self, callback: Callable[[EncoderReading], None]) -> None:
        """
        Register callback for encoder updates.

        Args:
            callback: Function called with EncoderReading on each update
        """
        self._callbacks.append(callback)

    def __repr__(self) -> str:
        status = "attached" if self._attached else "detached"
        return f"Encoder(id={self.encoder_id}, {status}, count={self._count})"
