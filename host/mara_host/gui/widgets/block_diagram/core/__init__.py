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
]
