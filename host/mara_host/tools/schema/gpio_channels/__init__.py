# schema/gpio_channels/__init__.py
"""
GPIO channel definitions with auto-discovery and validation.

GPIO channels map logical names to physical pins for host GPIO operations.

To add a new GPIO channel:
    1. Create _mychannel.py with a CHANNEL export
    2. Run: mara generate all
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from ..discovery import DiscoveryConfig, discover_defs
from ..pins import PINS
from .core import GpioChannelDef


# Auto-discover GPIO channel definitions
_config = DiscoveryConfig(
    export_name="CHANNEL",
    expected_type=GpioChannelDef,
    key_attr="name",
    unique_attrs=("name", "channel"),
    on_import_error="error",
)

GPIO_CHANNEL_DEFS = discover_defs(__file__, __name__, _config)


def validate_gpio_channels() -> None:
    """
    Validate GPIO channels against PINS.

    Called at import time to catch configuration errors early.
    """
    for name, channel in GPIO_CHANNEL_DEFS.items():
        if channel.pin_name not in PINS:
            raise ValueError(
                f"GPIO_CHANNEL {name}: pin_name '{channel.pin_name}' not in PINS"
            )


# Run validation at import time
validate_gpio_channels()


def _build_legacy_list() -> List[Dict[str, Any]]:
    """Build legacy GPIO_CHANNELS list."""
    # Sort by channel number for consistent ordering
    sorted_channels = sorted(GPIO_CHANNEL_DEFS.values(), key=lambda c: c.channel)
    return [ch.to_dict() for ch in sorted_channels]


# Legacy export for backward compatibility
GPIO_CHANNELS: List[Dict[str, Any]] = _build_legacy_list()


__all__ = ["GPIO_CHANNEL_DEFS", "GPIO_CHANNELS", "GpioChannelDef", "validate_gpio_channels"]
