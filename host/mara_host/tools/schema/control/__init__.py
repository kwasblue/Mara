# schema/control/__init__.py
"""
Control Block Registry - Single Source of Truth for MARA Control Blocks.

Uses unified discovery pattern with validation.

┌─────────────────────────────────────────────────────────────┐
│  Adding a new control block? Edit ONE file:                  │
│                                                             │
│    _controllers.py - Controllers (PID, Kalman, LQR, etc.)   │
│    _observers.py   - Observers (Luenberger, EKF, etc.)      │
│    _filters.py     - Filters (LP, HP, Notch, etc.)          │
│                                                             │
│  Then run: mara generate all                                 │
│                                                             │
│  See docs/ADDING_CONTROL.md for full guide.                  │
└─────────────────────────────────────────────────────────────┘

Validation:
- Duplicate block names raise ValueError at import time
- Category must be one of: controller, observer, filter, signal

Auto-generates:
    - GUI: Block diagram blocks + palette entries
    - Firmware: Controller slot configs + state-space mapping
    - Python: Control service bindings
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from .core import ControlBlockDef


def _discover_control_blocks() -> dict[str, dict[str, Any]]:
    """
    Auto-discover control block definitions from _*.py files.

    Validates:
    - No duplicate block names
    - All blocks have a valid category

    Returns:
        Merged dictionary of all control blocks

    Raises:
        ValueError: If duplicate block names or invalid categories found
    """
    merged: dict[str, dict[str, Any]] = {}
    valid_categories = {"controller", "observer", "filter", "signal"}

    package_dir = Path(__file__).parent
    package_name = __name__

    for module_file in sorted(package_dir.glob("_*.py")):
        if module_file.name.startswith("__"):
            continue

        module_name = module_file.stem
        full_module_name = f"{package_name}.{module_name}"

        try:
            module = importlib.import_module(full_module_name)
        except ImportError as e:
            raise ImportError(f"Failed to import control module {full_module_name}: {e}") from e

        # Look for *_BLOCKS exports
        for attr_name in dir(module):
            if not attr_name.endswith("_BLOCKS") or not attr_name.isupper():
                continue

            blocks = getattr(module, attr_name)
            if not isinstance(blocks, dict):
                continue

            for block_name, block_config in blocks.items():
                # Handle typed ControlBlockDef
                if isinstance(block_config, ControlBlockDef):
                    block_dict = block_config.to_dict()
                    actual_name = block_config.name
                else:
                    # Legacy dict-based definition
                    block_dict = block_config
                    actual_name = block_name

                # Validate category
                category = block_dict.get("category")
                if category not in valid_categories:
                    raise ValueError(
                        f"Invalid category '{category}' for block '{block_name}' in {full_module_name}. "
                        f"Must be one of: {', '.join(sorted(valid_categories))}"
                    )

                # Check for duplicates
                if block_name in merged:
                    raise ValueError(f"Duplicate control block name: '{block_name}'")

                merged[block_name] = block_dict

    return merged


# Discover and validate all control blocks at import time
CONTROL_BLOCKS = _discover_control_blocks()

# Export by category for convenience
CONTROLLER_BLOCKS: dict[str, dict[str, Any]] = {
    k: v for k, v in CONTROL_BLOCKS.items() if v.get("category") == "controller"
}
OBSERVER_BLOCKS: dict[str, dict[str, Any]] = {
    k: v for k, v in CONTROL_BLOCKS.items() if v.get("category") == "observer"
}
FILTER_BLOCKS: dict[str, dict[str, Any]] = {
    k: v for k, v in CONTROL_BLOCKS.items() if v.get("category") in ("filter", "signal")
}


def get_block_config(block_type: str) -> dict[str, Any] | None:
    """Get configuration for a control block type."""
    return CONTROL_BLOCKS.get(block_type)


def get_blocks_by_category(category: str) -> dict[str, dict[str, Any]]:
    """Get all blocks of a specific category (controller, observer, filter, signal)."""
    return {
        key: config
        for key, config in CONTROL_BLOCKS.items()
        if config.get("category") == category
    }


def get_palette_entries() -> list[dict[str, Any]]:
    """Generate palette entries for GUI from registry."""
    entries = []
    for key, config in CONTROL_BLOCKS.items():
        gui = config.get("gui", {})
        entries.append({
            "type": key,
            "label": gui.get("label", key.title()),
            "description": gui.get("description", ""),
            "color": gui.get("color", "#71717A"),
        })
    return entries


__all__ = [
    "CONTROL_BLOCKS",
    "CONTROLLER_BLOCKS",
    "OBSERVER_BLOCKS",
    "FILTER_BLOCKS",
    "ControlBlockDef",
    "get_block_config",
    "get_blocks_by_category",
    "get_palette_entries",
]
