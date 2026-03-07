# schema/__init__.py
"""
Platform schema definitions.

This package is the single source of truth for the robot platform schema:
- COMMANDS: JSON command definitions
- BINARY_COMMANDS: High-rate streaming commands
- TELEMETRY_SECTIONS: Binary telemetry section IDs
- GPIO_CHANNELS: Logical GPIO channel mapping
- CAN_*: CAN bus message definitions
- PINS: Pin assignments (from pins.json)
- VERSION: Firmware/protocol version info
- CAPABILITIES: Feature flags

Usage:
    from mara_host.tools.schema import COMMANDS, PINS, VERSION
"""

# Output paths
from .paths import (
    ROOT,
    PY_CONFIG_DIR,
    PY_COMMAND_DIR,
    PY_TELEMETRY_DIR,
    PY_TRANSPORT_DIR,
    FIRMWARE_INCLUDE,
    CPP_CONFIG_DIR,
    CPP_COMMAND_DIR,
    CPP_TELEMETRY_DIR,
    PINS_JSON,
)

# Version and capabilities
from .version import (
    VERSION,
    CAPABILITIES,
    CAPABILITIES_MASK,
)

# Pin configuration
from .pins import PINS

# Command definitions
from .commands import COMMANDS

# Telemetry sections
from .telemetry import TELEMETRY_SECTIONS

# Binary commands
from .binary import BINARY_COMMANDS

# CAN bus definitions
from .can import (
    CAN_CONFIG,
    CAN_MESSAGE_IDS,
    CAN_MESSAGES,
    CAN_NODE_STATES,
)

# GPIO channels
from .gpio_channels import (
    GPIO_CHANNELS,
    validate_gpio_channels,
)

__all__ = [
    # Paths
    "ROOT",
    "PY_CONFIG_DIR",
    "PY_COMMAND_DIR",
    "PY_TELEMETRY_DIR",
    "PY_TRANSPORT_DIR",
    "FIRMWARE_INCLUDE",
    "CPP_CONFIG_DIR",
    "CPP_COMMAND_DIR",
    "CPP_TELEMETRY_DIR",
    "PINS_JSON",
    # Version
    "VERSION",
    "CAPABILITIES",
    "CAPABILITIES_MASK",
    # Pins
    "PINS",
    # Commands
    "COMMANDS",
    # Telemetry
    "TELEMETRY_SECTIONS",
    # Binary
    "BINARY_COMMANDS",
    # CAN
    "CAN_CONFIG",
    "CAN_MESSAGE_IDS",
    "CAN_MESSAGES",
    "CAN_NODE_STATES",
    # GPIO
    "GPIO_CHANNELS",
    "validate_gpio_channels",
]
