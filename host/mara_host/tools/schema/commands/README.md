# Command Schema Definitions

This directory contains all command definitions for the MARA platform, organized by domain.

## Structure

```
commands/
├── __init__.py      # Merges all domains into COMMANDS dict
├── _safety.py       # Safety/state machine (9 commands)
├── _rates.py        # Loop rate configuration (4 commands)
├── _control.py      # Signal bus, slot configuration (13 commands)
├── _motion.py       # SET_MODE, SET_VEL (2 commands)
├── _gpio.py         # LED, GPIO, PWM (7 commands)
├── _servo.py        # Servo commands (3 commands)
├── _stepper.py      # Stepper commands (3 commands)
├── _sensors.py      # Encoder, ultrasonic (5 commands)
├── _dc_motor.py     # DC motor + velocity PID (5 commands)
├── _observer.py     # Luenberger state observer (6 commands)
├── _telemetry.py    # Telemetry configuration (2 commands)
└── _camera.py       # ESP32-CAM over HTTP (20 commands)
```

## Adding Commands

### To an Existing Domain

Edit the appropriate `_domain.py` file:

```python
# In _sensors.py
SENSOR_COMMANDS: dict[str, dict] = {
    # ... existing commands ...

    "CMD_MY_NEW_SENSOR": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Description of what this command does.",
        "payload": {
            "sensor_id": {"type": "int", "required": True},
            "threshold": {"type": "float", "required": False, "default": 0.0},
        },
    },
}
```

### Creating a New Domain

1. Create `_my_domain.py`:

```python
# schema/commands/_my_domain.py
"""My domain command definitions."""

MY_DOMAIN_COMMANDS: dict[str, dict] = {
    "CMD_MY_COMMAND": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "...",
        "payload": {...},
    },
}
```

2. Register in `__init__.py`:

```python
from ._my_domain import MY_DOMAIN_COMMANDS

COMMANDS: dict[str, dict] = {
    # ... existing domains ...
    **MY_DOMAIN_COMMANDS,
}

__all__ = [
    "COMMANDS",
    # ... existing exports ...
    "MY_DOMAIN_COMMANDS",
]
```

3. Regenerate:

```bash
mara generate all
```

## Command Definition Format

```python
"CMD_NAME": {
    "kind": "cmd",                    # Always "cmd"
    "direction": "host->mcu",         # Or "mcu->host" for responses
    "description": "What the command does.",
    "payload": {
        "param_name": {
            "type": "int",            # int, float, string, bool, array
            "required": True,         # True or False
            "default": 0,             # Default value (if required=False)
            "min": 0,                 # Optional: minimum value
            "max": 100,               # Optional: maximum value
            "enum": ["a", "b"],       # Optional: allowed values
            "description": "...",     # Optional: parameter description
        },
    },
},
```

## Type Mappings

| Schema Type | C++ Type | Python Type |
|-------------|----------|-------------|
| `int` | `int` | `int` |
| `float` | `float` | `float` |
| `string` | `const char*` | `str` |
| `bool` | `bool` | `bool` |
| `array` | varies | `list` |

## Domain Selection Guide

| If your command involves... | Use domain |
|----------------------------|------------|
| System identity, heartbeat, arm/disarm, e-stop | `_safety.py` |
| Loop rate configuration | `_rates.py` |
| Signal bus, control slots | `_control.py` |
| Robot mode, velocity setpoints | `_motion.py` |
| LEDs, GPIO pins, PWM | `_gpio.py` |
| Servo motors | `_servo.py` |
| Stepper motors | `_stepper.py` |
| Encoders, ultrasonic sensors | `_sensors.py` |
| DC motors, velocity PID | `_dc_motor.py` |
| State observers (Luenberger) | `_observer.py` |
| Telemetry intervals, log levels | `_telemetry.py` |
| ESP32-CAM control | `_camera.py` |

## See Also

- [ADDING_COMMANDS.md](../../../../docs/ADDING_COMMANDS.md) - Complete workflow
- [CODEGEN.md](../../../../docs/CODEGEN.md) - Code generation system
- [EXTENDING.md](../../../../docs/EXTENDING.md) - Adding new features
