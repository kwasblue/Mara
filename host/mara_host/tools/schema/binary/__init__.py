# schema/binary/__init__.py
"""
Binary command definitions with auto-discovery.

Binary commands are compact fixed-format messages for high-rate control loops.
Use JSON commands for setup/config, binary for real-time streaming (50+ Hz).

To add a new binary command:
    1. Create _mycommand.py with a COMMAND export
    2. Run: mara generate all
"""

from __future__ import annotations

from typing import Any

from ..discovery import DiscoveryConfig, discover_defs
from .core import BinaryCommandDef, BinaryFieldDef, TYPE_INFO

_config = DiscoveryConfig(
    export_name="COMMAND",
    expected_type=BinaryCommandDef,
    key_attr="name",
    unique_attrs=("name", "opcode"),
    on_import_error="error",
)

BINARY_COMMAND_DEFS = discover_defs(__file__, __name__, _config)


def _build_legacy_dict() -> dict[str, dict[str, Any]]:
    """Build legacy BINARY_COMMANDS dict."""
    return {name: cmd.to_legacy_dict() for name, cmd in BINARY_COMMAND_DEFS.items()}


# Legacy export for backward compatibility
BINARY_COMMANDS: dict[str, dict[str, Any]] = _build_legacy_dict()


__all__ = ["BINARY_COMMAND_DEFS", "BINARY_COMMANDS", "BinaryCommandDef", "BinaryFieldDef", "TYPE_INFO"]
