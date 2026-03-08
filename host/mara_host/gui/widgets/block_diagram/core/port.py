# mara_host/gui/widgets/block_diagram/core/port.py
"""Port class for block connection points."""

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor

from .models import PortConfig, PortKind, PortType, PORT_TYPE_COLORS


class Port:
    """
    A connection point on a block.

    Ports can be inputs or outputs, and have a type that
    determines what connections are valid.
    """

    RADIUS = 6  # Port circle radius

    def __init__(self, config: PortConfig, parent_block_id: str):
        """
        Initialize port.

        Args:
            config: Port configuration
            parent_block_id: ID of the block this port belongs to
        """
        self.config = config
        self.parent_block_id = parent_block_id

        # State
        self._position = QPointF(0, 0)
        self._hovered = False
        self._connected = False

    @property
    def port_id(self) -> str:
        """Get unique port identifier."""
        return f"{self.parent_block_id}.{self.config.port_id}"

    @property
    def kind(self) -> PortKind:
        """Get port direction (input/output)."""
        return self.config.kind

    @property
    def port_type(self) -> PortType:
        """Get port signal type."""
        return self.config.port_type

    @property
    def label(self) -> str:
        """Get port label."""
        return self.config.label

    @property
    def position(self) -> QPointF:
        """Get port position (set by parent block)."""
        return self._position

    @position.setter
    def position(self, pos: QPointF) -> None:
        """Set port position."""
        self._position = pos

    @property
    def is_input(self) -> bool:
        """Check if this is an input port."""
        return self.config.kind == PortKind.INPUT

    @property
    def is_output(self) -> bool:
        """Check if this is an output port."""
        return self.config.kind == PortKind.OUTPUT

    def get_rect(self) -> QRectF:
        """Get port bounding rectangle for hit testing."""
        return QRectF(
            self._position.x() - self.RADIUS,
            self._position.y() - self.RADIUS,
            self.RADIUS * 2,
            self.RADIUS * 2,
        )

    def get_color(self) -> QColor:
        """Get port color based on type and state."""
        color = QColor(PORT_TYPE_COLORS.get(self.port_type, "#9CA3AF"))
        if self._hovered:
            return color.lighter(130)
        return color

    def set_hovered(self, hovered: bool) -> None:
        """Set hover state."""
        self._hovered = hovered

    def set_connected(self, connected: bool) -> None:
        """Set connected state."""
        self._connected = connected

    def paint(self, painter: QPainter) -> None:
        """
        Paint the port.

        Args:
            painter: QPainter to draw with
        """
        color = self.get_color()

        # Draw filled circle for output, ring for input
        if self.is_output:
            painter.setPen(QPen(color.darker(120), 1))
            painter.setBrush(QBrush(color))
        else:
            painter.setPen(QPen(color, 2))
            painter.setBrush(QBrush(QColor("#18181B")))  # Dark center

        painter.drawEllipse(self._position, self.RADIUS, self.RADIUS)

        # Draw connection indicator
        if self._connected:
            painter.setPen(QPen(QColor("#FAFAFA"), 1))
            painter.setBrush(QBrush(QColor("#FAFAFA")))
            painter.drawEllipse(self._position, 2, 2)

    def contains(self, point: QPointF) -> bool:
        """Check if a point is within the port."""
        dx = point.x() - self._position.x()
        dy = point.y() - self._position.y()
        return (dx * dx + dy * dy) <= (self.RADIUS * self.RADIUS)
