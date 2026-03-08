# schema/version.py
"""Version and capability definitions."""

from typing import Any

# === VERSION INFO ===
VERSION: dict[str, Any] = {
    "firmware": "0.5.0",
    "protocol": 1,
    "schema_version": 1,
    "board": "esp32",
    "name": "robot",
}

# === CAPABILITIES ===
# Bitfield for feature advertisement (matches MCU Version.h)
CAPABILITIES: dict[str, int] = {
    "BINARY_PROTOCOL": 0x0001,
    "INTENT_BUFFERING": 0x0002,
    "STATE_SPACE_CTRL": 0x0004,
    "OBSERVERS": 0x0008,
}

# Combined capability mask (must match MCU)
CAPABILITIES_MASK: int = (
    CAPABILITIES["BINARY_PROTOCOL"]
    | CAPABILITIES["INTENT_BUFFERING"]
    | CAPABILITIES["STATE_SPACE_CTRL"]
    | CAPABILITIES["OBSERVERS"]
)
