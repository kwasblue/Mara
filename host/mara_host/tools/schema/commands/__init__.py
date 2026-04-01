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


def _discover_legacy_commands(package_name: str, typed_keys: set[str]) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict[str, CommandDef]]]:
    """Discover legacy dict-based commands (for backward compatibility).

    Returns:
        (merged_commands, legacy_groups, object_groups)
    """
    merged: dict[str, dict] = {}
    legacy_groups: dict[str, dict] = {}
    object_groups: dict[str, dict[str, CommandDef]] = {}
    package_dir = Path(__file__).parent

    for module_file in sorted(package_dir.glob("_*.py")):
        if module_file.name.startswith("__"):
            continue
        module_name = module_file.stem

        try:
            module = importlib.import_module(f"{package_name}.{module_name}")
            for attr_name in dir(module):
                if not attr_name.isupper():
                    continue
                value = getattr(module, attr_name)
                if not isinstance(value, dict):
                    continue

                # Track typed object groups
                if attr_name.endswith("_COMMAND_OBJECTS"):
                    if all(isinstance(v, CommandDef) for v in value.values()):
                        object_groups[attr_name] = value
                        # Also create legacy dict version
                        legacy_name = attr_name.removesuffix("_OBJECTS")
                        if legacy_name not in legacy_groups:
                            legacy_groups[legacy_name] = export_command_dicts(value)
                    continue

                # Track legacy command groups
                if attr_name.endswith("_COMMANDS"):
                    legacy_groups[attr_name] = value
                    # Merge into flat dict, skipping typed keys
                    for k, v in value.items():
                        if k in typed_keys:
                            continue
                        if k in merged:
                            raise ValueError(f"Duplicate legacy command name: {k!r}")
                        merged[k] = v
        except ImportError:
            pass  # Handled by typed discovery

    return merged, legacy_groups, object_groups


def _do_discovery() -> tuple[dict[str, dict], dict[str, CommandDef], dict[str, dict], dict[str, dict[str, CommandDef]]]:
    """Full discovery returning all registries."""
    package_name = __name__ if __name__ != "__main__" else "mara_host.tools.schema.commands"

    # Discover typed CommandDef objects (validates uniqueness)
    command_objects = discover_multi_export(
        __file__,
        package_name,
        export_suffix="_COMMAND_OBJECTS",
        expected_type=CommandDef,
        on_import_error="error",
    )

    # Also discover legacy dict-based commands for backward compatibility
    legacy_merged, legacy_groups, object_groups = _discover_legacy_commands(
        package_name, set(command_objects.keys())
    )

    # Merge: typed objects take precedence
    merged_legacy = dict(legacy_merged)
    merged_legacy.update(export_command_dicts(command_objects))

    return merged_legacy, command_objects, legacy_groups, object_groups


COMMANDS, COMMAND_OBJECTS, _COMMAND_GROUPS, _COMMAND_OBJECT_GROUPS = _do_discovery()


def __getattr__(name: str) -> Any:
    """Lazy access to individual command groups (e.g., SAFETY_COMMANDS, DC_MOTOR_COMMANDS)."""
    if name in _COMMAND_GROUPS:
        return _COMMAND_GROUPS[name]
    if name in _COMMAND_OBJECT_GROUPS:
        return _COMMAND_OBJECT_GROUPS[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes including discovered command groups."""
    base = ["COMMANDS", "COMMAND_OBJECTS", "CommandDef", "export_command_dicts"]
    return base + list(_COMMAND_GROUPS.keys()) + list(_COMMAND_OBJECT_GROUPS.keys())


__all__ = ["COMMANDS", "COMMAND_OBJECTS", "CommandDef", "export_command_dicts"]
