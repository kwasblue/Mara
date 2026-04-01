# schema/hardware/core.py
"""
Core typed dataclass definitions for hardware extensions.

These dataclasses define the single source of truth for sensors, actuators,
and transports. Code generators read from these typed definitions instead
of parsing untyped dicts.

Patterns:
- Follow CommandDef (schema/commands/core.py) structure
- Follow TelemetrySectionDef (schema/telemetry/core.py) structure
- Immutable (frozen=True) for safety
- to_legacy_dict() for backward compatibility
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..commands.core import CommandDef
from ..telemetry.core import TelemetrySectionDef


# -----------------------------------------------------------------------------
# GUI Block Definition
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class GuiBlockDef:
    """
    GUI block diagram appearance for hardware.

    Attributes:
        label: Display label in block diagram (e.g., "IMU", "Ultrasonic")
        color: Hex color code for the block (e.g., "#22C55E")
        inputs: Tuple of (pin_name, label) for input pins
        outputs: Tuple of (pin_name, label) for output pins
    """
    label: str
    color: str
    inputs: tuple[tuple[str, str], ...] = ()
    outputs: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format."""
        result: dict[str, Any] = {
            "label": self.label,
            "color": self.color,
        }
        if self.inputs:
            result["inputs"] = [list(p) for p in self.inputs]
        if self.outputs:
            result["outputs"] = [list(p) for p in self.outputs]
        return result


# -----------------------------------------------------------------------------
# Firmware Hints
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class FirmwareHints:
    """
    Hints for firmware code generation.

    Attributes:
        class_name: C++ class name (e.g., "UltrasonicSensor")
        feature_flag: Preprocessor flag (e.g., "HAS_ULTRASONIC")
        capability: Capability constant name (e.g., "CAP_ULTRASONIC")
        max_instances: Maximum hardware instances (default 1)
        sample_interval_ms: Default sampling interval in milliseconds
        handler: Handler class name (e.g., "SensorHandler")
        manager: Manager class name (e.g., "UltrasonicManager")
    """
    class_name: str
    feature_flag: str
    capability: str = ""
    max_instances: int = 1
    sample_interval_ms: int = 50
    handler: str = ""
    manager: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format."""
        result: dict[str, Any] = {
            "feature_flag": self.feature_flag,
        }
        if self.manager:
            result["manager"] = self.manager
        if self.handler:
            result["handler"] = self.handler
        if self.class_name:
            result["class_name"] = self.class_name
        if self.capability:
            result["capability"] = self.capability
        if self.max_instances != 1:
            result["max_instances"] = self.max_instances
        if self.sample_interval_ms != 50:
            result["sample_interval_ms"] = self.sample_interval_ms
        return result


# -----------------------------------------------------------------------------
# Python Hints
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class PythonHints:
    """
    Hints for Python code generation.

    Attributes:
        api_class: Python API class name (e.g., "Ultrasonic")
        reading_class: Reading dataclass name (e.g., "UltrasonicReading")
        telemetry_topic: Event bus topic (e.g., "telemetry.ultrasonic")
    """
    api_class: str
    reading_class: str
    telemetry_topic: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format."""
        return {
            "api_class": self.api_class,
            "reading_class": self.reading_class,
            "telemetry_topic": self.telemetry_topic,
        }


# -----------------------------------------------------------------------------
# Sensor Definition
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class SensorDef:
    """
    Complete definition for a sensor hardware type.

    Attributes:
        name: Unique sensor identifier (e.g., "ultrasonic", "imu")
        interface: Hardware interface type (i2c | gpio | uart | spi | adc)
        description: Human-readable description
        gui: Block diagram appearance
        commands: Commands for this sensor (CommandDef instances)
        telemetry: Telemetry section definition
        firmware: Firmware generation hints
        python: Python generation hints
    """
    name: str
    interface: str  # i2c | gpio | uart | spi | adc
    description: str
    gui: GuiBlockDef
    commands: Mapping[str, CommandDef]
    telemetry: TelemetrySectionDef
    firmware: FirmwareHints
    python: PythonHints

    def to_legacy_dict(self) -> dict[str, Any]:
        """Convert to legacy SENSOR_HARDWARE dict format."""
        from ..commands.core import export_command_dicts

        return {
            "type": "sensor",
            "interface": self.interface,
            "description": self.description,
            "gui": self.gui.to_dict(),
            "commands": export_command_dicts(self.commands),
            "telemetry": self.telemetry.to_legacy_dict(),
            "firmware": self.firmware.to_dict(),
            "python": self.python.to_dict(),
        }


# -----------------------------------------------------------------------------
# Actuator Definition
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ActuatorDef:
    """
    Complete definition for an actuator hardware type.

    Attributes:
        name: Unique actuator identifier (e.g., "dc_motor", "servo", "stepper")
        interface: Hardware interface type (pwm | gpio | uart)
        description: Human-readable description
        gui: Block diagram appearance (optional)
        commands: Commands for this actuator (CommandDef instances)
        telemetry: Telemetry section definition (optional for some actuators)
        firmware: Firmware generation hints
        python: Python generation hints
    """
    name: str
    interface: str  # pwm | gpio | uart
    description: str
    gui: GuiBlockDef | None
    commands: Mapping[str, CommandDef]
    telemetry: TelemetrySectionDef | None
    firmware: FirmwareHints
    python: PythonHints

    def to_legacy_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format."""
        from ..commands.core import export_command_dicts

        result: dict[str, Any] = {
            "type": "actuator",
            "interface": self.interface,
            "description": self.description,
            "commands": export_command_dicts(self.commands),
            "firmware": self.firmware.to_dict(),
            "python": self.python.to_dict(),
        }
        if self.gui:
            result["gui"] = self.gui.to_dict()
        if self.telemetry:
            result["telemetry"] = self.telemetry.to_legacy_dict()
        return result


# -----------------------------------------------------------------------------
# Transport Definition
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class TransportDef:
    """
    Complete definition for a transport/communication layer.

    Attributes:
        name: Unique transport identifier (e.g., "uart", "wifi", "ble")
        layer: Transport layer (physical | protocol)
        description: Human-readable description
        commands: Commands for this transport (CommandDef instances)
        firmware: Firmware generation hints
        python: Python generation hints
    """
    name: str
    layer: str  # physical | protocol
    description: str
    commands: Mapping[str, CommandDef]
    firmware: FirmwareHints
    python: PythonHints

    def to_legacy_dict(self) -> dict[str, Any]:
        """Convert to legacy dict format."""
        from ..commands.core import export_command_dicts

        return {
            "type": "transport",
            "layer": self.layer,
            "description": self.description,
            "commands": export_command_dicts(self.commands),
            "firmware": self.firmware.to_dict(),
            "python": self.python.to_dict(),
        }


__all__ = [
    "GuiBlockDef",
    "FirmwareHints",
    "PythonHints",
    "SensorDef",
    "ActuatorDef",
    "TransportDef",
]
