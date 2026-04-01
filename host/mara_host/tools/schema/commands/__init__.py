"""
JSON command definitions for the robot platform.

AUTO-DISCOVERY: Command modules are automatically discovered using unified discovery.
To add new commands, create a file `_mycommands.py` with either:
- a legacy dict named `MYCOMMANDS_COMMANDS`, or
- a typed-object dict named `MYCOMMANDS_COMMAND_OBJECTS`.

The commands will be auto-merged into COMMANDS, while typed sources are also
exposed via COMMAND_OBJECTS for incremental migration.

Validation:
- Duplicate command names raise ValueError at import time
- Type mismatches raise TypeError at import time
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from ..discovery import discover_multi_export
from .core import CommandDef, export_command_dicts


def _discover_commands() -> tuple[dict[str, dict], dict[str, CommandDef]]:
    """
    Auto-discover command modules using unified discovery.

    Returns:
        (merged_legacy_commands, merged_command_objects)

    Raises:
        ValueError: If duplicate command names are found
        TypeError: If exports contain non-CommandDef values
    """
    package_name = __name__ if __name__ != "__main__" else "mara_host.tools.schema.commands"

    # Discover typed CommandDef objects (validates uniqueness)
    command_objects = discover_multi_export(
        __file__,
        package_name,
        export_suffix="_COMMAND_OBJECTS",
        expected_type=CommandDef,
        on_import_error="error",  # Fail fast on import errors
    )

    # Also discover legacy dict-based commands for backward compatibility
    legacy_commands = _discover_legacy_commands(package_name, set(command_objects.keys()))

    # Merge: typed objects take precedence
    merged_legacy = dict(legacy_commands)
    merged_legacy.update(export_command_dicts(command_objects))

    return merged_legacy, command_objects


def _discover_legacy_commands(package_name: str, typed_keys: set[str]) -> dict[str, dict]:
    """Discover legacy dict-based commands (for backward compatibility)."""
    merged: dict[str, dict] = {}
    package_dir = Path(__file__).parent

    for module_file in sorted(package_dir.glob("_*.py")):
        if module_file.name.startswith("__"):
            continue
        module_name = module_file.stem

        try:
            module = importlib.import_module(f"{package_name}.{module_name}")
            for attr_name in dir(module):
                if not attr_name.isupper() or not attr_name.endswith("_COMMANDS"):
                    continue
                # Skip if this is a typed export (ends with _COMMAND_OBJECTS)
                if attr_name.endswith("_COMMAND_OBJECTS"):
                    continue
                value = getattr(module, attr_name)
                if not isinstance(value, dict):
                    continue
                # Skip keys that are already typed
                for k, v in value.items():
                    if k in typed_keys:
                        continue
                    if k in merged:
                        raise ValueError(f"Duplicate legacy command name: {k!r}")
                    merged[k] = v
        except ImportError:
            pass  # Handled by typed discovery

    return merged


COMMANDS, COMMAND_OBJECTS = _discover_commands()


__all__ = ["COMMANDS", "COMMAND_OBJECTS", "CommandDef", "export_command_dicts"]
