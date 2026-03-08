# schema/control/__init__.py
"""
Control Block Registry - Single Source of Truth for MARA Control Blocks.

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

Auto-generates:
    - GUI: Block diagram blocks + palette entries
    - Firmware: Controller slot configs + state-space mapping
    - Python: Control service bindings
"""

from typing import Any

# Import control definitions by category
from ._controllers import CONTROLLER_BLOCKS
from ._observers import OBSERVER_BLOCKS
from ._filters import FILTER_BLOCKS

# Merge all control definitions into single registry
CONTROL_BLOCKS: dict[str, dict[str, Any]] = {
    **CONTROLLER_BLOCKS,
    **OBSERVER_BLOCKS,
    **FILTER_BLOCKS,
}


def get_block_config(block_type: str) -> dict[str, Any] | None:
    """Get configuration for a control block type."""
    return CONTROL_BLOCKS.get(block_type)


def get_blocks_by_category(category: str) -> dict[str, dict[str, Any]]:
    """Get all blocks of a specific category (controller, observer, filter)."""
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
    "get_block_config",
    "get_blocks_by_category",
    "get_palette_entries",
]
