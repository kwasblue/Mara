# mara_host/api/pwm.py
"""
PWM output control - Public API.

This is the public interface for PWM control. For internal/advanced use,
see mara_host.hw.pwm.PwmHostModule.

Example:
    from mara_host import Robot, PWM

    async with Robot("/dev/ttyUSB0") as robot:
        pwm = PWM(robot)
        await pwm.set(channel=0, duty=0.5, freq_hz=1000)
        await pwm.set_duty(0, 0.75)
        await pwm.stop(0)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict

if TYPE_CHECKING:
    from ..robot import Robot


class PWM:
    """
    PWM output controller.

    Public API for PWM control. Wraps the internal PwmHostModule
    and adds state tracking, validation, and convenience methods.

    Args:
        robot: Connected Robot instance
        default_freq_hz: Default frequency for channels (default: 1000.0 Hz)

    Example:
        pwm = PWM(robot)

        # Set channel 0 to 50% duty at 1kHz
        await pwm.set(channel=0, duty=0.5, freq_hz=1000)

        # Just change duty cycle (keep frequency)
        await pwm.set_duty(0, 0.75)

        # Set using percentage (0-100)
        await pwm.set_percent(0, 75)

        # Stop (set duty to 0)
        await pwm.stop(0)
    """

    def __init__(
        self,
        robot: Robot,
        default_freq_hz: float = 1000.0,
    ) -> None:
        from ..hw.pwm import PwmHostModule

        self._robot = robot
        self._module = PwmHostModule(robot.bus, robot.client)
        self._default_freq_hz = default_freq_hz
        self._channels: Dict[int, Dict] = {}  # channel -> {duty, freq_hz}

    @property
    def active_channels(self) -> list[int]:
        """List of channels that have been configured."""
        return list(self._channels.keys())

    def get_duty(self, channel: int) -> Optional[float]:
        """Get the last set duty cycle for a channel (0.0 to 1.0)."""
        info = self._channels.get(channel)
        return info["duty"] if info else None

    def get_frequency(self, channel: int) -> Optional[float]:
        """Get the last set frequency for a channel in Hz."""
        info = self._channels.get(channel)
        return info["freq_hz"] if info else None

    async def set(
        self,
        channel: int,
        duty: float,
        freq_hz: Optional[float] = None,
    ) -> None:
        """
        Set PWM duty cycle and optionally frequency.

        Args:
            channel: PWM channel ID
            duty: Duty cycle from 0.0 (off) to 1.0 (fully on)
            freq_hz: Optional frequency in Hz (uses default if not specified)

        Raises:
            ValueError: If duty is not between 0.0 and 1.0
        """
        if duty < 0.0 or duty > 1.0:
            raise ValueError(f"Duty {duty} must be between 0.0 and 1.0")

        effective_freq = freq_hz if freq_hz is not None else self._default_freq_hz
        await self._module.set(channel, duty, effective_freq)
        self._channels[channel] = {"duty": duty, "freq_hz": effective_freq}

    async def set_duty(self, channel: int, duty: float) -> None:
        """
        Set duty cycle only, keeping the current frequency.

        Args:
            channel: PWM channel ID
            duty: Duty cycle from 0.0 to 1.0

        Raises:
            ValueError: If duty is not between 0.0 and 1.0
        """
        if duty < 0.0 or duty > 1.0:
            raise ValueError(f"Duty {duty} must be between 0.0 and 1.0")

        current_freq = self.get_frequency(channel) or self._default_freq_hz
        await self._module.set(channel, duty, current_freq)
        self._channels[channel] = {"duty": duty, "freq_hz": current_freq}

    async def set_percent(self, channel: int, percent: float) -> None:
        """
        Set duty cycle as percentage (0-100).

        Args:
            channel: PWM channel ID
            percent: Duty cycle as percentage (0 to 100)
        """
        await self.set_duty(channel, percent / 100.0)

    async def stop(self, channel: int) -> None:
        """Stop PWM output on a channel (set duty to 0)."""
        await self.set_duty(channel, 0.0)

    def __repr__(self) -> str:
        return f"PWM(channels={len(self._channels)}, default_freq={self._default_freq_hz}Hz)"
