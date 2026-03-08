# mara_host/gui/widgets/block_diagram/__init__.py
"""
Block Diagram System for MARA Host GUI.

A visual framework for creating and editing block diagrams supporting:
- Hardware Layout: Drag-and-drop components onto ESP32 with auto pin assignment
- Control Loop: Visualize PID controllers, observers, signal bus connections
- System Architecture: Show signal flow between services

Usage:
    from mara_host.gui.widgets.block_diagram import (
        DiagramCanvas,
        HardwareLayoutDiagram,
        ControlLoopDiagram,
        ESP32Block,
        PIDBlock,
    )

    # Create a hardware layout view
    hardware_view = HardwareLayoutDiagram()
    hardware_view.set_pin_service(pin_service)

    # Create a control loop view
    control_view = ControlLoopDiagram()
    control_view.set_controller(robot_controller)
    control_view.create_basic_pid_loop()
"""

# Core components
from .core import (
    # Models
    PortKind,
    PortType,
    PortConfig,
    BlockConfig,
    ConnectionConfig,
    DiagramState,
    PORT_TYPE_COLORS,
    can_connect,
    # Components
    Grid,
    Port,
    BlockBase,
    Connection,
    DiagramCanvas,
)

# Hardware blocks
from .blocks import (
    ESP32Block,
    MotorBlock,
    EncoderBlock,
    ServoBlock,
    SensorBlock,
    SENSOR_TYPES,
)

# Control blocks
from .blocks import (
    PIDBlock,
    ObserverBlock,
    SignalSourceBlock,
    SignalSinkBlock,
    SumBlock,
    GainBlock,
)

# Service blocks
from .blocks import (
    MotorServiceBlock,
    ServoServiceBlock,
    GPIOServiceBlock,
)

# Diagram views
from .diagrams import (
    ComponentPalette,
    HardwareLayoutDiagram,
    ControlLoopDiagram,
)

# Dialogs
from .dialogs import (
    BlockConfigDialog,
    PIDConfigDialog,
)

__all__ = [
    # Core
    "PortKind",
    "PortType",
    "PortConfig",
    "BlockConfig",
    "ConnectionConfig",
    "DiagramState",
    "PORT_TYPE_COLORS",
    "can_connect",
    "Grid",
    "Port",
    "BlockBase",
    "Connection",
    "DiagramCanvas",
    # Hardware blocks
    "ESP32Block",
    "MotorBlock",
    "EncoderBlock",
    "ServoBlock",
    "SensorBlock",
    "SENSOR_TYPES",
    # Control blocks
    "PIDBlock",
    "ObserverBlock",
    "SignalSourceBlock",
    "SignalSinkBlock",
    "SumBlock",
    "GainBlock",
    # Service blocks
    "MotorServiceBlock",
    "ServoServiceBlock",
    "GPIOServiceBlock",
    # Diagram views
    "ComponentPalette",
    "HardwareLayoutDiagram",
    "ControlLoopDiagram",
    # Dialogs
    "BlockConfigDialog",
    "PIDConfigDialog",
]
