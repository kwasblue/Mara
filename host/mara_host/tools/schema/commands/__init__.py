# schema/commands/__init__.py
"""
JSON command definitions for the robot platform.

AUTO-DISCOVERY: Command modules are automatically discovered.
To add new commands, create a file `_mycommands.py` with a dict
named `MYCOMMANDS_COMMANDS` (or any `*_COMMANDS` pattern).

Example:
    # _myfeature.py
    MYFEATURE_COMMANDS: dict[str, dict] = {
        "CMD_MY_THING": {
            "kind": "cmd",
            "direction": "host->mcu",
            "description": "Does a thing",
            "payload": {"param": {"type": "int", "default": 0}},
        },
    }

The commands will be auto-merged into COMMANDS.
"""

import importlib
from pathlib import Path
from typing import Any


def _discover_commands() -> tuple[dict[str, dict], dict[str, dict]]:
    """
    Auto-discover command modules and merge their *_COMMANDS dicts.

    Returns:
        (merged_commands, individual_groups)
    """
    merged: dict[str, dict] = {}
    groups: dict[str, dict] = {}

    # Get the directory containing this __init__.py
    package_dir = Path(__file__).parent

    # Determine the full package name for imports
    # This works whether imported as mara_host.tools.schema.commands or directly
    package_name = __name__ if __name__ != "__main__" else "mara_host.tools.schema.commands"

    # Find all _*.py files (command modules by convention)
    # Exclude __init__.py and __pycache__ entries
    for module_file in sorted(package_dir.glob("_*.py")):
        if module_file.name.startswith("__"):
            continue
        module_name = module_file.stem  # e.g., "_safety"

        try:
            # Import the module using full path
            full_module_name = f"{package_name}.{module_name}"
            module = importlib.import_module(full_module_name)

            # Find all *_COMMANDS dicts in the module
            for attr_name in dir(module):
                if attr_name.endswith("_COMMANDS") and attr_name.isupper():
                    commands_dict = getattr(module, attr_name)
                    if isinstance(commands_dict, dict):
                        # Merge into main dict
                        merged.update(commands_dict)
                        # Keep reference to individual group
                        groups[attr_name] = commands_dict

        except ImportError as e:
            import warnings
            warnings.warn(f"Failed to import command module {module_name}: {e}")

    return merged, groups


# Auto-discover and merge all command modules
COMMANDS, _COMMAND_GROUPS = _discover_commands()

# Export individual groups for selective imports
# These are dynamically added to module namespace
def __getattr__(name: str) -> Any:
    """Lazy access to individual command groups."""
    if name in _COMMAND_GROUPS:
        return _COMMAND_GROUPS[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes including discovered command groups."""
    return ["COMMANDS"] + list(_COMMAND_GROUPS.keys())


__all__ = ["COMMANDS"] + list(_COMMAND_GROUPS.keys())
