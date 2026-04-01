# schema/hardware/__init__.py
"""
Hardware Registry - Single Source of Truth for MARA Hardware.

This package defines all hardware extensions using typed dataclasses
with auto-discovery from subdirectories:

    sensors/    - Sensor definitions (IMU, ultrasonic, lidar, etc.)
    actuators/  - Actuator definitions (DC motor, servo, stepper)
    transports/ - Transport definitions (UART, WiFi, BLE, MQTT, CAN)

Adding new hardware (1 file):
    1. Create a new file in the appropriate subdirectory:
       - sensors/_mysensor.py   with SENSOR = SensorDef(...)
       - actuators/_myactuator.py with ACTUATOR = ActuatorDef(...)
       - transports/_mytransport.py with TRANSPORT = TransportDef(...)
    2. Run: mara generate all
    3. Implement firmware hardware logic (only the hardware-specific parts)

The registries provide:
    - Type-safe definitions using frozen dataclasses
    - Auto-discovery of new entries (just add a file)
    - Automatic validation (duplicate names, section IDs detected at import)
    - Automatic code generation for firmware stubs and Python APIs
    - GUI block diagram specifications
    - Legacy dict export for backward compatibility

See docs/ADDING_HARDWARE.md for full guide.
"""

from __future__ import annotations

from typing import Any

# Core types
from .core import (
    GuiBlockDef,
    FirmwareHints,
    PythonHints,
    SensorDef,
    ActuatorDef,
    TransportDef,
)

# Auto-discovered typed registries
from .sensors import SENSORS
from .actuators import ACTUATORS
from .transports import TRANSPORTS


# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

def _validate_hardware() -> None:
    """
    Validate hardware definitions for consistency.

    Checks:
    - No duplicate telemetry section IDs across sensors/actuators
    - No duplicate command names across all hardware
    """
    # Collect all telemetry section IDs
    section_ids: dict[int, str] = {}

    for name, sensor in SENSORS.items():
        sid = sensor.telemetry.section_id
        if sid in section_ids:
            raise ValueError(
                f"Duplicate telemetry section ID 0x{sid:02X}: "
                f"sensor '{name}' and '{section_ids[sid]}'"
            )
        section_ids[sid] = f"sensor:{name}"

    for name, actuator in ACTUATORS.items():
        if actuator.telemetry:
            sid = actuator.telemetry.section_id
            if sid in section_ids:
                raise ValueError(
                    f"Duplicate telemetry section ID 0x{sid:02X}: "
                    f"actuator '{name}' and '{section_ids[sid]}'"
                )
            section_ids[sid] = f"actuator:{name}"

    # Collect all command names
    command_names: dict[str, str] = {}

    for name, sensor in SENSORS.items():
        for cmd_name in sensor.commands:
            if cmd_name in command_names:
                raise ValueError(
                    f"Duplicate command name '{cmd_name}': "
                    f"sensor '{name}' and '{command_names[cmd_name]}'"
                )
            command_names[cmd_name] = f"sensor:{name}"

    for name, actuator in ACTUATORS.items():
        for cmd_name in actuator.commands:
            if cmd_name in command_names:
                raise ValueError(
                    f"Duplicate command name '{cmd_name}': "
                    f"actuator '{name}' and '{command_names[cmd_name]}'"
                )
            command_names[cmd_name] = f"actuator:{name}"

    for name, transport in TRANSPORTS.items():
        for cmd_name in transport.commands:
            if cmd_name in command_names:
                raise ValueError(
                    f"Duplicate command name '{cmd_name}': "
                    f"transport '{name}' and '{command_names[cmd_name]}'"
                )
            command_names[cmd_name] = f"transport:{name}"


# Run validation at import time
_validate_hardware()


# -----------------------------------------------------------------------------
# Legacy Compatibility
# -----------------------------------------------------------------------------

def _build_sensor_legacy() -> dict[str, dict[str, Any]]:
    """Build legacy SENSOR_HARDWARE dict from SENSORS."""
    return {name: sensor.to_legacy_dict() for name, sensor in SENSORS.items()}


def _build_actuator_legacy() -> dict[str, dict[str, Any]]:
    """Build legacy dict from ACTUATORS."""
    return {name: actuator.to_legacy_dict() for name, actuator in ACTUATORS.items()}


def _build_transport_legacy() -> dict[str, dict[str, Any]]:
    """Build legacy dict from TRANSPORTS."""
    return {name: transport.to_legacy_dict() for name, transport in TRANSPORTS.items()}


def _build_hardware_dict() -> dict[str, dict[str, Any]]:
    """Build combined legacy hardware dict."""
    result: dict[str, dict[str, Any]] = {}
    result.update(SENSOR_HARDWARE)
    result.update(ACTUATOR_HARDWARE)
    result.update(TRANSPORT_HARDWARE)
    return result


# Legacy registries
SENSOR_HARDWARE: dict[str, dict[str, Any]] = _build_sensor_legacy()
ACTUATOR_HARDWARE: dict[str, dict[str, Any]] = _build_actuator_legacy()
TRANSPORT_HARDWARE: dict[str, dict[str, Any]] = _build_transport_legacy()
HARDWARE: dict[str, dict[str, Any]] = _build_hardware_dict()


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def get_all_commands() -> dict[str, Any]:
    """
    Get all commands from all hardware definitions.

    Returns:
        Merged dict of all command definitions.
    """
    from ..commands.core import CommandDef, export_command_dicts

    all_commands: dict[str, CommandDef] = {}

    for sensor in SENSORS.values():
        all_commands.update(sensor.commands)

    for actuator in ACTUATORS.values():
        all_commands.update(actuator.commands)

    for transport in TRANSPORTS.values():
        all_commands.update(transport.commands)

    return export_command_dicts(all_commands)


def get_all_telemetry() -> dict[str, Any]:
    """
    Get all telemetry sections from hardware definitions.

    Returns:
        Dict mapping section names to TelemetrySectionDef objects.
    """
    from ..telemetry.core import TelemetrySectionDef

    sections: dict[str, TelemetrySectionDef] = {}

    for sensor in SENSORS.values():
        sections[sensor.telemetry.name] = sensor.telemetry

    for actuator in ACTUATORS.values():
        if actuator.telemetry:
            sections[actuator.telemetry.name] = actuator.telemetry

    return sections


__all__ = [
    # Types
    "GuiBlockDef",
    "FirmwareHints",
    "PythonHints",
    "SensorDef",
    "ActuatorDef",
    "TransportDef",
    # Typed registries
    "SENSORS",
    "ACTUATORS",
    "TRANSPORTS",
    # Legacy registries
    "SENSOR_HARDWARE",
    "ACTUATOR_HARDWARE",
    "TRANSPORT_HARDWARE",
    "HARDWARE",
    # Helpers
    "get_all_commands",
    "get_all_telemetry",
]
