# mara_host/gui/widgets/controls/__init__.py
"""
Reusable control widgets for the MARA GUI.

AUTO-DISCOVERY: Widgets are lazily imported.
To add a new widget, create a file and add to _EXPORTS.

Example:
    # widgets/controls/mywidget.py
    class MyWidget(QWidget):
        ...

Then add to _EXPORTS: "MyWidget": "mywidget"
"""

import importlib
from typing import Any

_EXPORTS = {
    "RangeSliderWidget": "slider_base",
    "MotorSliderGroup": "motor_slider",
    "ServoSliderGroup": "servo_slider",
    "ParameterGrid": "parameter_grid",
    "ParameterSpec": "parameter_grid",
    "SpinBoxRow": "spinbox_row",
}

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    if name in _EXPORTS:
        module_name = _EXPORTS[name]
        if module_name not in _cache:
            _cache[module_name] = importlib.import_module(
                f".{module_name}", package=__name__
            )
        return getattr(_cache[module_name], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(_EXPORTS.keys())


__all__ = list(_EXPORTS.keys())
