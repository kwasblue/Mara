# mara_host/gui/widgets/block_diagram/core/__init__.py
"""Core block diagram components."""

from .models import (
    PortKind,
    PortType,
    PortConfig,
    BlockConfig,
    ConnectionConfig,
    DiagramState,
    PORT_TYPE_COLORS,
    can_connect,
)
from .grid import Grid
from .port import Port
from .block import BlockBase
from .connection import Connection, paint_preview_connection
from .canvas import DiagramCanvas
from .esp32_pinout import (
    ESP32PinInfo,
    ESP32_PINOUT,
    PIN_CATEGORY_COLORS,
    get_pin_info,
    get_safe_gpios,
    get_adc1_gpios,
    get_adc2_gpios,
    get_touch_gpios,
    get_input_only_gpios,
    get_flash_gpios,
    get_strapping_gpios,
)
from .block_mapping import (
    BlockMapper,
    SignalConfig,
    ControllerSlotConfig,
    ObserverSlotConfig,
    map_diagram_to_firmware,
)

__all__ = [
    # Models
    "PortKind",
    "PortType",
    "PortConfig",
    "BlockConfig",
    "ConnectionConfig",
    "DiagramState",
    "PORT_TYPE_COLORS",
    "can_connect",
    # Components
    "Grid",
    "Port",
    "BlockBase",
    "Connection",
    "paint_preview_connection",
    "DiagramCanvas",
    # ESP32 Pinout
    "ESP32PinInfo",
    "ESP32_PINOUT",
    "PIN_CATEGORY_COLORS",
    "get_pin_info",
    "get_safe_gpios",
    "get_adc1_gpios",
    "get_adc2_gpios",
    "get_touch_gpios",
    "get_input_only_gpios",
    "get_flash_gpios",
    "get_strapping_gpios",
    # Block Mapping
    "BlockMapper",
    "SignalConfig",
    "ControllerSlotConfig",
    "ObserverSlotConfig",
    "map_diagram_to_firmware",
]
