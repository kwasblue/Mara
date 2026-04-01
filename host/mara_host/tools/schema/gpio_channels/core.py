# schema/gpio_channels/core.py
"""
Core typed dataclass definitions for GPIO channel mappings.

GPIO channels map logical names to physical pins for host GPIO operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class GpioChannelDef:
    """
    Definition of a GPIO channel mapping.

    Attributes:
        name: Logical channel name (e.g., "LED_STATUS")
        channel: Logical channel ID (0-255)
        pin_name: Physical pin name from PINS (e.g., "LED_STATUS")
        mode: GPIO mode ("output", "input", "input_pullup")
        description: Human-readable description
    """
    name: str
    channel: int
    pin_name: str
    mode: Literal["output", "input", "input_pullup"]
    description: str = ""

    def __post_init__(self) -> None:
        if not 0 <= self.channel <= 255:
            raise ValueError(f"channel must be 0-255, got {self.channel}")
        if self.mode not in ("output", "input", "input_pullup"):
            raise ValueError(f"Invalid mode: {self.mode}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format."""
        return {
            "name": self.name,
            "channel": self.channel,
            "pin_name": self.pin_name,
            "mode": self.mode,
        }

    @classmethod
    def output(cls, name: str, channel: int, pin_name: str, description: str = "") -> "GpioChannelDef":
        """Create an output channel."""
        return cls(name, channel, pin_name, "output", description)

    @classmethod
    def input(cls, name: str, channel: int, pin_name: str, description: str = "") -> "GpioChannelDef":
        """Create an input channel."""
        return cls(name, channel, pin_name, "input", description)

    @classmethod
    def input_pullup(cls, name: str, channel: int, pin_name: str, description: str = "") -> "GpioChannelDef":
        """Create an input with pullup channel."""
        return cls(name, channel, pin_name, "input_pullup", description)


__all__ = ["GpioChannelDef"]
