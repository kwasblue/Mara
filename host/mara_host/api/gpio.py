# mara_host/api/gpio.py
"""
Digital GPIO control - Public API.

This is the public interface for GPIO control. Internally uses GpioService.

Example:
    from mara_host import Robot, GPIO

    async with Robot("/dev/ttyUSB0") as robot:
        gpio = GPIO(robot)
        await gpio.register(channel=0, pin=2, mode="output")
        await gpio.write(0, 1)
        await gpio.toggle(0)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..robot import Robot


class GPIO:
    """
    Digital I/O controller with channel registration.

    Public API for GPIO control. Wraps GpioService internally.

    Args:
        robot: Connected Robot instance

    Example:
        gpio = GPIO(robot)

        # Register channel 0 as output on pin 2
        await gpio.register(channel=0, pin=2, mode="output")

        # Write, toggle, and read
        await gpio.write(0, 1)
        await gpio.toggle(0)
        await gpio.high(0)
        await gpio.low(0)
    """

    def __init__(self, robot: Robot) -> None:
        from ..services.control.gpio_service import GpioService

        self._robot = robot
        self._service = GpioService(robot.client)

    @property
    def registered_channels(self) -> list[int]:
        """List of registered channel IDs."""
        return list(self._service.get_all_channels().keys())

    def is_registered(self, channel: int) -> bool:
        """Check if a channel is registered."""
        return self._service.get_channel(channel) is not None

    def get_mode(self, channel: int) -> Optional[str]:
        """Get the mode of a registered channel ('input' or 'output')."""
        ch = self._service.get_channel(channel)
        return ch.mode.value if ch else None

    def get_pin(self, channel: int) -> Optional[int]:
        """Get the physical pin of a registered channel."""
        ch = self._service.get_channel(channel)
        return ch.pin if ch else None

    async def register(
        self,
        channel: int,
        pin: int,
        mode: str = "output",
    ) -> None:
        """
        Register a logical GPIO channel to a physical pin.

        Args:
            channel: Logical channel ID (0-based)
            pin: Physical GPIO pin number
            mode: Pin mode - "input" or "output" (default: "output")

        Raises:
            ValueError: If mode is not valid
            RuntimeError: If registration fails
        """
        if mode not in ("input", "output", "input_pullup", "input_pulldown"):
            raise ValueError(f"Invalid mode: '{mode}'")

        result = await self._service.register(channel, pin, mode)
        if not result.ok:
            raise RuntimeError(result.error)

    async def write(self, channel: int, value: int) -> None:
        """
        Write a digital value to a channel.

        Args:
            channel: Channel ID (must be registered)
            value: 0 or 1

        Raises:
            ValueError: If channel is not registered
            RuntimeError: If write fails
        """
        if not self.is_registered(channel):
            raise ValueError(f"Channel {channel} is not registered")

        # Direct client call (validated above, skip service re-validation)
        value = 1 if value else 0
        ok, error = await self._robot.client.send_reliable(
            "CMD_GPIO_WRITE",
            {"channel": channel, "value": value},
        )
        if ok:
            ch = self._service.get_channel(channel)
            if ch:
                ch.value = value
        else:
            raise RuntimeError(error or f"Failed to write GPIO channel {channel}")

    async def read(self, channel: int) -> None:
        """
        Request a read of a channel's value.

        The result is returned via telemetry events.

        Args:
            channel: Channel ID (must be registered)

        Raises:
            ValueError: If channel is not registered
            RuntimeError: If read fails
        """
        if not self.is_registered(channel):
            raise ValueError(f"Channel {channel} is not registered")

        # Direct client call (validated above, skip service re-validation)
        ok, error = await self._robot.client.send_reliable(
            "CMD_GPIO_READ",
            {"channel": channel},
        )
        if not ok:
            raise RuntimeError(error or f"Failed to read GPIO channel {channel}")

    async def toggle(self, channel: int) -> None:
        """
        Toggle a channel's output state.

        Args:
            channel: Channel ID (must be registered)

        Raises:
            ValueError: If channel is not registered
            RuntimeError: If toggle fails
        """
        if not self.is_registered(channel):
            raise ValueError(f"Channel {channel} is not registered")

        # Direct client call (validated above, skip service re-validation)
        ok, error = await self._robot.client.send_reliable(
            "CMD_GPIO_TOGGLE",
            {"channel": channel},
        )
        if ok:
            ch = self._service.get_channel(channel)
            if ch:
                ch.value = 1 - ch.value  # Toggle local state
        else:
            raise RuntimeError(error or f"Failed to toggle GPIO channel {channel}")

    async def high(self, channel: int) -> None:
        """Set a channel's output high (1)."""
        await self.write(channel, 1)

    async def low(self, channel: int) -> None:
        """Set a channel's output low (0)."""
        await self.write(channel, 0)

    def __repr__(self) -> str:
        return f"GPIO(channels={len(self.registered_channels)})"
