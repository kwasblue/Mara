# schema/discovery.py
"""
Unified auto-discovery framework for schema definitions.

This module provides a generic discovery mechanism that all schema types
can use for consistent auto-discovery of definition files.

Usage:
    from ..discovery import discover_defs, DiscoveryConfig

    SENSORS = discover_defs(
        __file__, __name__,
        DiscoveryConfig(
            export_name="SENSOR",
            expected_type=SensorDef,
            key_attr="name",
            unique_attrs=["name"],
        )
    )

Patterns:
- All discoverable schemas use `_*.py` files
- Each file exports a single definition object
- Discovery validates uniqueness constraints
- Errors on duplicates (not warnings)
"""

from __future__ import annotations

import importlib
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generic, Type, TypeVar


T = TypeVar("T")


@dataclass
class DiscoveryConfig(Generic[T]):
    """
    Configuration for schema auto-discovery.

    Attributes:
        export_name: Name of the export to look for (e.g., "SENSOR", "SECTION")
        expected_type: Expected type of the exported object
        key_attr: Attribute to use as the registry key (e.g., "name", "kind")
        unique_attrs: List of attributes that must be unique across all entries
        subdirs: Optional list of subdirectories to search (for multi-category schemas)
        on_import_error: How to handle import errors ("error", "warn", "ignore")
    """
    export_name: str
    expected_type: Type[T]
    key_attr: str = "name"
    unique_attrs: tuple[str, ...] = ("name",)
    subdirs: tuple[str, ...] = ()
    on_import_error: str = "warn"  # "error", "warn", "ignore"


def discover_defs(
    package_file: str,
    package_name: str,
    config: DiscoveryConfig[T],
) -> dict[str, T]:
    """
    Auto-discover schema definitions from _*.py files.

    Args:
        package_file: __file__ of the package (use __file__)
        package_name: __name__ of the package (use __name__)
        config: Discovery configuration

    Returns:
        Dictionary mapping key attribute values to definition objects

    Raises:
        TypeError: If an export is not of the expected type
        ValueError: If uniqueness constraints are violated
        ImportError: If on_import_error="error" and import fails
    """
    registry: dict[str, T] = {}
    seen_values: dict[str, dict[Any, str]] = {attr: {} for attr in config.unique_attrs}

    package_dir = Path(package_file).parent

    # Determine directories to search
    if config.subdirs:
        search_dirs = [(package_dir / subdir, f"{package_name}.{subdir}") for subdir in config.subdirs]
    else:
        search_dirs = [(package_dir, package_name)]

    for search_dir, search_package in search_dirs:
        if not search_dir.exists():
            continue

        for module_file in sorted(search_dir.glob("_*.py")):
            if module_file.name.startswith("__"):
                continue

            module_name = module_file.stem
            full_module_name = f"{search_package}.{module_name}"

            # Import the module
            try:
                module = importlib.import_module(full_module_name)
            except ImportError as e:
                if config.on_import_error == "error":
                    raise ImportError(f"Failed to import {full_module_name}: {e}") from e
                elif config.on_import_error == "warn":
                    warnings.warn(f"Failed to import {full_module_name}: {e}")
                continue

            # Get the export
            exported = getattr(module, config.export_name, None)
            if exported is None:
                continue

            # Type check
            if not isinstance(exported, config.expected_type):
                raise TypeError(
                    f"{full_module_name}.{config.export_name} must be a "
                    f"{config.expected_type.__name__}, got {type(exported).__name__}"
                )

            # Get the key
            key = getattr(exported, config.key_attr)

            # Check uniqueness constraints
            for attr in config.unique_attrs:
                value = getattr(exported, attr)
                if value in seen_values[attr]:
                    existing_module = seen_values[attr][value]
                    raise ValueError(
                        f"Duplicate {attr}={value!r}: found in both "
                        f"{existing_module} and {full_module_name}"
                    )
                seen_values[attr][value] = full_module_name

            registry[key] = exported

    return registry


def discover_multi_export(
    package_file: str,
    package_name: str,
    export_suffix: str,
    expected_type: Type[T],
    key_attr: str = "name",
    on_import_error: str = "warn",
) -> dict[str, T]:
    """
    Auto-discover schema definitions with multiple exports per file.

    This is used for patterns like Commands where a file can export
    multiple definitions (e.g., SERVO_COMMAND_OBJECTS, DC_MOTOR_COMMAND_OBJECTS).

    Args:
        package_file: __file__ of the package
        package_name: __name__ of the package
        export_suffix: Suffix to look for in export names (e.g., "_COMMAND_OBJECTS")
        expected_type: Expected type of dict values
        key_attr: Not used (keys come from dict keys)
        on_import_error: How to handle import errors

    Returns:
        Merged dictionary of all discovered definitions
    """
    merged: dict[str, T] = {}
    package_dir = Path(package_file).parent

    for module_file in sorted(package_dir.glob("_*.py")):
        if module_file.name.startswith("__"):
            continue

        module_name = module_file.stem
        full_module_name = f"{package_name}.{module_name}"

        try:
            module = importlib.import_module(full_module_name)
        except ImportError as e:
            if on_import_error == "error":
                raise ImportError(f"Failed to import {full_module_name}: {e}") from e
            elif on_import_error == "warn":
                warnings.warn(f"Failed to import {full_module_name}: {e}")
            continue

        # Look for exports ending with the suffix
        for attr_name in dir(module):
            if not attr_name.endswith(export_suffix):
                continue
            if not attr_name.isupper():
                continue

            value = getattr(module, attr_name)
            if not isinstance(value, dict):
                continue

            # Validate all values are of expected type
            for k, v in value.items():
                if not isinstance(v, expected_type):
                    raise TypeError(
                        f"{full_module_name}.{attr_name}[{k!r}] must be a "
                        f"{expected_type.__name__}, got {type(v).__name__}"
                    )
                if k in merged:
                    raise ValueError(f"Duplicate key {k!r} in {full_module_name}.{attr_name}")

            merged.update(value)

    return merged


__all__ = ["DiscoveryConfig", "discover_defs", "discover_multi_export"]
