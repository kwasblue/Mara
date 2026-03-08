# mara_host/gui/widgets/block_diagram/blocks/__init__.py
"""
Hardware and control blocks for diagrams.

AUTO-DISCOVERY: Blocks are lazily imported.
To add a new block type:
1. Create blocks/myblock.py with MyBlock class
2. Add to _EXPORTS below

The block will be available via:
    from mara_host.gui.widgets.block_diagram.blocks import MyBlock
"""

import importlib
from typing import Any

_EXPORTS = {
    # Hardware blocks
    "ESP32Block": "esp32",
    "create_esp32_config": "esp32",
    "MotorBlock": "motor",
    "create_motor_config": "motor",
    "EncoderBlock": "encoder",
    "create_encoder_config": "encoder",
    "ServoBlock": "servo",
    "create_servo_config": "servo",
    "SensorBlock": "sensor",
    "create_sensor_config": "sensor",
    "SENSOR_TYPES": "sensor",
    # Control blocks
    "PIDBlock": "pid",
    "create_pid_config": "pid",
    "ObserverBlock": "observer",
    "create_observer_config": "observer",
    "SignalSourceBlock": "signal",
    "SignalSinkBlock": "signal",
    "SumBlock": "signal",
    "GainBlock": "signal",
    # Service blocks
    "MotorServiceBlock": "service",
    "ServoServiceBlock": "service",
    "GPIOServiceBlock": "service",
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
