# mara_host/gui/panels/__init__.py
"""
GUI panels for the MARA Control application.

AUTO-DISCOVERY: Panels are automatically discovered by main_window.py.
To add a new panel, create a file with PANEL_META:

    # gui/panels/mypanel.py
    PANEL_META = {
        "id": "mypanel",
        "label": "My Panel",
        "order": 50,  # Lower = higher in sidebar
    }

    class MyPanelPanel(QWidget):
        def __init__(self, signals, controller, settings):
            ...

The panel will be auto-discovered and added to the sidebar.
No edits to __init__.py or main_window.py needed!
"""

# Lazy imports for direct access
import importlib
from typing import Any

_PANELS = {
    "DashboardPanel": "dashboard",
    "ControlPanel": "control",
    "CameraPanel": "camera",
    "CommandsPanel": "commands",
    "CalibrationPanel": "calibration",
    "TestingPanel": "testing",
    "AdvancedPanel": "advanced",
    "DiagramPanel": "diagram",
    "SessionPanel": "session",
    "PinoutPanel": "pinout",
    "FirmwarePanel": "firmware",
    "ConfigPanel": "config",
    "LogsPanel": "logs",
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    """Lazy import of panel classes."""
    if name in _PANELS:
        module_name = _PANELS[name]
        if module_name not in _cache:
            _cache[module_name] = importlib.import_module(
                f".{module_name}", package=__name__
            )
        return getattr(_cache[module_name], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(_PANELS.keys())


__all__ = list(_PANELS.keys())
