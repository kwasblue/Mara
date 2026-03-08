# mara_host/gui/widgets/__init__.py
"""
Reusable GUI widgets for the MARA Control application.

AUTO-DISCOVERY: Widgets are lazily imported from subpackages.
To add a new widget:
1. Create the widget file in controls/ or displays/
2. Add to _EXPORTS in the subpackage __init__.py
3. Add to _WIDGETS below for top-level access

Example:
    from mara_host.gui.widgets import MotorSliderGroup
    # or
    from mara_host.gui.widgets.controls import MotorSliderGroup
"""

import importlib
from typing import Any

# Map widget names to their subpackage
_WIDGETS = {
    # Standalone
    "JoystickWidget": ("joystick", None),
    # Controls
    "MotorSliderGroup": ("controls", "MotorSliderGroup"),
    "ServoSliderGroup": ("controls", "ServoSliderGroup"),
    "ParameterGrid": ("controls", "ParameterGrid"),
    "ParameterSpec": ("controls", "ParameterSpec"),
    "SpinBoxRow": ("controls", "SpinBoxRow"),
    # Displays
    "LabelDisplay": ("displays", "LabelDisplay"),
    "TelemetryGrid": ("displays", "TelemetryGrid"),
    "TelemetrySpec": ("displays", "TelemetrySpec"),
    "ProgressIndicator": ("displays", "ProgressIndicator"),
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    if name in _WIDGETS:
        module_name, attr_name = _WIDGETS[name]
        if module_name not in _cache:
            _cache[module_name] = importlib.import_module(
                f".{module_name}", package=__name__
            )
        # If attr_name is None, the module itself exports the class
        if attr_name is None:
            return getattr(_cache[module_name], name)
        return getattr(_cache[module_name], attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(_WIDGETS.keys())


__all__ = list(_WIDGETS.keys())
