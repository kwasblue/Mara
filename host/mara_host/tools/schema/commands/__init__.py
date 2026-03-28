"""
JSON command definitions for the robot platform.

AUTO-DISCOVERY: Command modules are automatically discovered.
To add new commands, create a file `_mycommands.py` with either:
- a legacy dict named `MYCOMMANDS_COMMANDS`, or
- a typed-object dict named `MYCOMMANDS_COMMAND_OBJECTS`.

The commands will be auto-merged into COMMANDS, while typed sources are also
exposed via COMMAND_OBJECTS for incremental migration.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from .core import CommandDef, export_command_dicts


def _discover_commands() -> tuple[dict[str, dict], dict[str, dict], dict[str, CommandDef], dict[str, dict[str, CommandDef]]]:
    """
    Auto-discover command modules and merge their command registries.

    Returns:
        (merged_commands, legacy_groups, merged_objects, object_groups)
    """
    merged: dict[str, dict] = {}
    groups: dict[str, dict] = {}
    merged_objects: dict[str, CommandDef] = {}
    object_groups: dict[str, dict[str, CommandDef]] = {}

    package_dir = Path(__file__).parent
    package_name = __name__ if __name__ != "__main__" else "mara_host.tools.schema.commands"

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

                if attr_name.endswith("_COMMAND_OBJECTS") and isinstance(value, dict):
                    if all(isinstance(spec, CommandDef) for spec in value.values()):
                        merged_objects.update(value)
                        object_groups[attr_name] = value

                elif attr_name.endswith("_COMMANDS") and isinstance(value, dict):
                    merged.update(value)
                    groups[attr_name] = value

        except ImportError as e:
            import warnings
            warnings.warn(f"Failed to import command module {module_name}: {e}")

    for attr_name, obj_group in object_groups.items():
        legacy_name = attr_name.removesuffix("_OBJECTS")
        if legacy_name not in groups:
            groups[legacy_name] = export_command_dicts(obj_group)

    merged_from_objects = export_command_dicts(merged_objects)
    merged.update(merged_from_objects)

    return merged, groups, merged_objects, object_groups


COMMANDS, _COMMAND_GROUPS, COMMAND_OBJECTS, _COMMAND_OBJECT_GROUPS = _discover_commands()


def __getattr__(name: str) -> Any:
    """Lazy access to individual command groups."""
    if name in _COMMAND_GROUPS:
        return _COMMAND_GROUPS[name]
    if name in _COMMAND_OBJECT_GROUPS:
        return _COMMAND_OBJECT_GROUPS[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes including discovered command groups."""
    return ["COMMANDS", "COMMAND_OBJECTS"] + list(_COMMAND_GROUPS.keys()) + list(_COMMAND_OBJECT_GROUPS.keys())


__all__ = ["COMMANDS", "COMMAND_OBJECTS"] + list(_COMMAND_GROUPS.keys()) + list(_COMMAND_OBJECT_GROUPS.keys())
