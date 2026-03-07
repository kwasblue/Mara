# mara_host/api/gpio.py
"""
Digital GPIO control - Public API.

This is the public interface for GPIO control. For internal/advanced use,
see mara_host.hw.gpio.GpioHostModule.

Example:
    from mara_host import Robot, GPIO

    async with Robot("/dev/ttyUSB0") as robot:
        gpio = GPIO(robot)
        await gpio.register(channel=0, pin=2, mode="output")
        await gpio.write(0, 1)
        await gpio.toggle(0)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict

if TYPE_CHECKING:
    from ..robot import Robot


class GPIO:
    """
    Digital I/O controller with channel registration.

    Public API for GPIO control. Wraps the internal GpioHostModule
    and adds channel tracking, validation, and convenience methods.

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
        from ..hw.gpio import GpioHostModule

        self._robot = robot
        self._module = GpioHostModule(robot.bus, robot.client)
        self._channels: Dict[int, Dict] = {}  # channel -> {pin, mode}

    @property
    def registered_channels(self) -> list[int]:
        """List of registered channel IDs."""
        return list(self._channels.keys())

    def is_registered(self, channel: int) -> bool:
        """Check if a channel is registered."""
        return channel in self._channels

    def get_mode(self, channel: int) -> Optional[str]:
        """Get the mode of a registered channel ('input' or 'output')."""
        info = self._channels.get(channel)
        return info["mode"] if info else None

    def get_pin(self, channel: int) -> Optional[int]:
        """Get the physical pin of a registered channel."""
        info = self._channels.get(channel)
        return info["pin"] if info else None

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
            ValueError: If mode is not 'input' or 'output'
        """
        if mode not in ("input", "output"):
            raise ValueError(f"Mode must be 'input' or 'output', got '{mode}'")

        await self._robot.client.cmd_gpio_register_channel(
            channel=channel,
            pin=pin,
            mode=mode,
        )
        self._channels[channel] = {"pin": pin, "mode": mode}

    async def write(self, channel: int, value: int) -> None:
        """
        Write a digital value to a channel.

        Args:
            channel: Channel ID (must be registered)
            value: 0 or 1

        Raises:
            ValueError: If channel is not registered
        """
        if channel not in self._channels:
            raise ValueError(f"Channel {channel} is not registered")
        await self._module.write(channel, value)

    async def read(self, channel: int) -> None:
        """
        Request a read of a channel's value.

        The result is returned via telemetry events.

        Args:
            channel: Channel ID (must be registered)

        Raises:
            ValueError: If channel is not registered
        """
        if channel not in self._channels:
            raise ValueError(f"Channel {channel} is not registered")
        await self._module.read(channel)

    async def toggle(self, channel: int) -> None:
        """
        Toggle a channel's output state.

        Args:
            channel: Channel ID (must be registered)

        Raises:
            ValueError: If channel is not registered
        """
        if channel not in self._channels:
            raise ValueError(f"Channel {channel} is not registered")
        await self._module.toggle(channel)

    async def high(self, channel: int) -> None:
        """Set a channel's output high (1)."""
        await self.write(channel, 1)

    async def low(self, channel: int) -> None:
        """Set a channel's output low (0)."""
        await self.write(channel, 0)

    def __repr__(self) -> str:
        return f"GPIO(channels={len(self._channels)})"
