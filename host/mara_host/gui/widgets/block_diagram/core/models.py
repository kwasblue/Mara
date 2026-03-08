# mara_host/gui/widgets/block_diagram/core/models.py
"""Data models for the block diagram system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PortKind(Enum):
    """Direction of a port."""
    INPUT = "input"
    OUTPUT = "output"


class PortType(Enum):
    """Type of signal a port carries."""
    SIGNAL = "signal"    # Generic signal (white)
    REF = "ref"          # Reference input (blue)
    MEAS = "meas"        # Measurement input (green)
    OUT = "out"          # Control output (orange)
    GPIO = "gpio"        # GPIO pin (cyan)
    PWM = "pwm"          # PWM output (red)
    ENCODER = "encoder"  # Encoder signal (purple)
    I2C = "i2c"          # I2C bus (yellow)
    SPI = "spi"          # SPI bus (magenta)


# Port type compatibility matrix - which types can connect
PORT_TYPE_COMPAT = {
    PortType.SIGNAL: {PortType.SIGNAL, PortType.REF, PortType.MEAS, PortType.OUT},
    PortType.REF: {PortType.SIGNAL, PortType.REF, PortType.OUT},
    PortType.MEAS: {PortType.SIGNAL, PortType.MEAS, PortType.ENCODER},
    PortType.OUT: {PortType.SIGNAL, PortType.REF, PortType.OUT, PortType.PWM},
    PortType.GPIO: {PortType.GPIO},
    PortType.PWM: {PortType.PWM, PortType.OUT},
    PortType.ENCODER: {PortType.ENCODER, PortType.MEAS, PortType.SIGNAL},
    PortType.I2C: {PortType.I2C},
    PortType.SPI: {PortType.SPI},
}


# Colors for port types (hex colors)
PORT_TYPE_COLORS = {
    PortType.SIGNAL: "#9CA3AF",   # Gray
    PortType.REF: "#3B82F6",      # Blue
    PortType.MEAS: "#22C55E",     # Green
    PortType.OUT: "#F59E0B",      # Orange
    PortType.GPIO: "#06B6D4",     # Cyan
    PortType.PWM: "#EF4444",      # Red
    PortType.ENCODER: "#8B5CF6",  # Purple
    PortType.I2C: "#EAB308",      # Yellow
    PortType.SPI: "#EC4899",      # Magenta
}


@dataclass
class PortConfig:
    """Configuration for a port on a block."""
    port_id: str
    label: str
    kind: PortKind
    port_type: PortType = PortType.SIGNAL
    position_ratio: float = 0.5  # 0.0 = top/left, 1.0 = bottom/right


@dataclass
class BlockConfig:
    """Configuration for a block in the diagram."""
    block_type: str
    block_id: str
    label: str
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 60.0
    properties: dict[str, Any] = field(default_factory=dict)
    input_ports: list[PortConfig] = field(default_factory=list)
    output_ports: list[PortConfig] = field(default_factory=list)


@dataclass
class ConnectionConfig:
    """Configuration for a connection between ports."""
    connection_id: str
    from_block: str
    from_port: str
    to_block: str
    to_port: str
    signal_id: Optional[int] = None  # For signal bus routing
    label: Optional[str] = None


@dataclass
class DiagramState:
    """Complete state of a diagram (for save/load)."""
    diagram_type: str  # "hardware" or "control"
    name: str = "Untitled"
    blocks: list[BlockConfig] = field(default_factory=list)
    connections: list[ConnectionConfig] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "diagram_type": self.diagram_type,
            "name": self.name,
            "blocks": [
                {
                    "block_type": b.block_type,
                    "block_id": b.block_id,
                    "label": b.label,
                    "x": b.x,
                    "y": b.y,
                    "width": b.width,
                    "height": b.height,
                    "properties": b.properties,
                }
                for b in self.blocks
            ],
            "connections": [
                {
                    "connection_id": c.connection_id,
                    "from_block": c.from_block,
                    "from_port": c.from_port,
                    "to_block": c.to_block,
                    "to_port": c.to_port,
                    "signal_id": c.signal_id,
                    "label": c.label,
                }
                for c in self.connections
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagramState":
        """Create from JSON dict."""
        # This would need block type registry to recreate port configs
        # For now, basic structure
        return cls(
            diagram_type=data.get("diagram_type", "hardware"),
            name=data.get("name", "Untitled"),
            blocks=[
                BlockConfig(
                    block_type=b["block_type"],
                    block_id=b["block_id"],
                    label=b["label"],
                    x=b.get("x", 0),
                    y=b.get("y", 0),
                    width=b.get("width", 100),
                    height=b.get("height", 60),
                    properties=b.get("properties", {}),
                )
                for b in data.get("blocks", [])
            ],
            connections=[
                ConnectionConfig(
                    connection_id=c["connection_id"],
                    from_block=c["from_block"],
                    from_port=c["from_port"],
                    to_block=c["to_block"],
                    to_port=c["to_port"],
                    signal_id=c.get("signal_id"),
                    label=c.get("label"),
                )
                for c in data.get("connections", [])
            ],
            metadata=data.get("metadata", {}),
        )


def can_connect(from_type: PortType, to_type: PortType) -> bool:
    """Check if two port types can be connected."""
    return to_type in PORT_TYPE_COMPAT.get(from_type, set())
