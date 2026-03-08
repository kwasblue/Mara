# schema/hardware/__init__.py
"""
Hardware Registry - Single Source of Truth for MARA Hardware.

┌─────────────────────────────────────────────────────────────┐
│  Adding new hardware? Edit ONE file:                        │
│                                                             │
│    _sensors.py   - Sensors (IMU, ultrasonic, temp, etc.)   │
│    _actuators.py - Motors, servos, steppers (future)       │
│                                                             │
│  Then run: mara generate all                                │
│                                                             │
│  See docs/ADDING_HARDWARE.md for full guide.                │
└─────────────────────────────────────────────────────────────┘

Auto-generates:
    - C++: CommandDefs.h, TelemetrySections.h
    - Python: client_commands.py, telemetry parser
    - GUI: Block diagram palette entries
"""

from typing import Any

# Import hardware definitions by category
from ._sensors import SENSOR_HARDWARE

# Future: from ._actuators import ACTUATOR_HARDWARE

# Merge all hardware definitions into single registry
HARDWARE: dict[str, dict[str, Any]] = {
    **SENSOR_HARDWARE,
    # **ACTUATOR_HARDWARE,  # Future
}

__all__ = ["HARDWARE", "SENSOR_HARDWARE"]
