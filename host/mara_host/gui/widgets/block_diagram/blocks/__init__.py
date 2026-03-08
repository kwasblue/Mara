# mara_host/gui/widgets/block_diagram/blocks/__init__.py
"""
Hardware and control blocks for diagrams.

AUTO-DISCOVERY: Blocks are lazily imported.
To add a new block type:
1. Create blocks/myblock.py with MyBlock class
2. Add to _EXPORTS below

OR for control blocks (preferred):
1. Add entry to tools/schema/control/_controllers.py (or _observers.py, _filters.py)
2. Run: mara generate control
3. Your block is auto-generated in _generated.py

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
    # Control blocks (manual)
    "PIDBlock": "pid",
    "create_pid_config": "pid",
    "ObserverBlock": "observer",
    "create_observer_config": "observer",
    # Signal blocks (manual)
    "SignalSourceBlock": "signal",
    "SignalSinkBlock": "signal",
    "SumBlock": "signal",
    "GainBlock": "signal",
    "IntegratorBlock": "signal",
    "DerivativeBlock": "signal",
    "SaturationBlock": "signal",
    "FilterBlock": "signal",
    "DelayBlock": "signal",
    # Service blocks
    "MotorServiceBlock": "service",
    "ServoServiceBlock": "service",
    "GPIOServiceBlock": "service",
}

# Auto-generated control blocks from registry
# These are added dynamically from _generated.py
_GENERATED_EXPORTS = {
    # Controllers
    "LqrBlock": "_generated",
    "KalmanLqgBlock": "_generated",
    "StateSpaceBlock": "_generated",
    "CascadePidBlock": "_generated",
    "MpcBlock": "_generated",
    "FeedforwardBlock": "_generated",
    # Observers
    "KalmanBlock": "_generated",
    "EkfBlock": "_generated",
    "ComplementaryBlock": "_generated",
    "VelocityObserverBlock": "_generated",
    "DisturbanceObserverBlock": "_generated",
    # Filters
    "NotchFilterBlock": "_generated",
    "MovingAverageBlock": "_generated",
    "DeadzoneBlock": "_generated",
    "RateLimiterBlock": "_generated",
    "TransportDelayBlock": "_generated",
}

_cache: dict[str, Any] = {}

# Merge all exports
_ALL_EXPORTS = {**_EXPORTS, **_GENERATED_EXPORTS}


def __getattr__(name: str) -> Any:
    if name in _ALL_EXPORTS:
        module_name = _ALL_EXPORTS[name]
        if module_name not in _cache:
            _cache[module_name] = importlib.import_module(
                f".{module_name}", package=__name__
            )
        return getattr(_cache[module_name], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(_ALL_EXPORTS.keys())


__all__ = list(_ALL_EXPORTS.keys())
