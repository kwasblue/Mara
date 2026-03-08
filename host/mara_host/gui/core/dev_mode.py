# mara_host/gui/core/dev_mode.py
"""
Dev mode flag for the GUI.

Separated into its own module to avoid circular imports.
"""

_DEV_MODE = False


def is_dev_mode() -> bool:
    """Check if running in dev mode."""
    return _DEV_MODE


def set_dev_mode(enabled: bool) -> None:
    """Set the dev mode flag."""
    global _DEV_MODE
    _DEV_MODE = enabled
