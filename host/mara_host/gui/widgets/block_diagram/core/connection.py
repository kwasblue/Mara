# mara_host/gui/widgets/block_diagram/core/connection.py
"""Connection class for wires between ports."""

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QFont

from .models import ConnectionConfig, PORT_TYPE_COLORS, PortType
from .port import Port


class Connection:
    """
    A connection (wire) between two ports.

    Renders as a bezier curve with optional signal label.
    """

    def __init__(
        self,
        config: ConnectionConfig,
        from_port: Port,
        to_port: Port,
    ):
        """
        Initialize connection.

        Args:
            config: Connection configuration
            from_port: Source port (output)
            to_port: Destination port (input)
        """
        self.config = config
        self.from_port = from_port
        self.to_port = to_port

        # State
        self._selected = False
        self._hovered = False

    @property
    def connection_id(self) -> str:
        """Get unique connection identifier."""
        return self.config.connection_id

    @property
    def signal_id(self) -> Optional[int]:
        """Get signal bus ID if assigned."""
        return self.config.signal_id

    @property
    def label(self) -> Optional[str]:
        """Get connection label."""
        return self.config.label

    def set_selected(self, selected: bool) -> None:
        """Set selection state."""
        self._selected = selected

    def set_hovered(self, hovered: bool) -> None:
        """Set hover state."""
        self._hovered = hovered

    def get_color(self) -> QColor:
        """Get connection color based on port type and state."""
        # Use output port type for color
        base_color = QColor(PORT_TYPE_COLORS.get(self.from_port.port_type, "#9CA3AF"))

        if self._selected:
            return QColor("#3B82F6")  # Accent blue
        if self._hovered:
            return base_color.lighter(130)
        return base_color

    def get_path(self) -> QPainterPath:
        """Get the bezier curve path for the connection."""
        start = self.from_port.position
        end = self.to_port.position

        path = QPainterPath()
        path.moveTo(start)

        # Calculate control points for smooth bezier
        dx = abs(end.x() - start.x())
        dy = abs(end.y() - start.y())

        # Control point offset based on distance
        offset = max(40, min(dx * 0.5, 100))

        ctrl1 = QPointF(start.x() + offset, start.y())
        ctrl2 = QPointF(end.x() - offset, end.y())

        path.cubicTo(ctrl1, ctrl2, end)

        return path

    def get_preview_path(self, start: QPointF, end: QPointF) -> QPainterPath:
        """Get path for connection preview (during drag)."""
        path = QPainterPath()
        path.moveTo(start)

        dx = abs(end.x() - start.x())
        offset = max(40, min(dx * 0.5, 100))

        ctrl1 = QPointF(start.x() + offset, start.y())
        ctrl2 = QPointF(end.x() - offset, end.y())

        path.cubicTo(ctrl1, ctrl2, end)

        return path

    def contains(self, point: QPointF, tolerance: float = 5.0) -> bool:
        """
        Check if a point is near the connection line.

        Args:
            point: Point to test
            tolerance: Distance tolerance in pixels

        Returns:
            True if point is within tolerance of the line
        """
        path = self.get_path()

        # Create a stroked version of the path for hit testing
        stroker = QPainterPathStroker()
        stroker.setWidth(tolerance * 2)
        stroked = stroker.createStroke(path)

        return stroked.contains(point)

    def get_midpoint(self) -> QPointF:
        """Get the midpoint of the connection for label placement."""
        start = self.from_port.position
        end = self.to_port.position
        return QPointF(
            (start.x() + end.x()) / 2,
            (start.y() + end.y()) / 2,
        )

    def paint(self, painter: QPainter) -> None:
        """
        Paint the connection.

        Args:
            painter: QPainter to draw with
        """
        color = self.get_color()
        path = self.get_path()

        # Draw line
        width = 3 if self._selected else 2
        painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        # Draw arrow at end
        self._draw_arrow(painter, color)

        # Draw label if present
        if self.label or self.signal_id is not None:
            self._draw_label(painter)

    def _draw_arrow(self, painter: QPainter, color: QColor) -> None:
        """Draw arrow head at the end of the connection."""
        end = self.to_port.position
        path = self.get_path()

        # Get direction at end point
        t = 0.95  # Near the end
        point_before = path.pointAtPercent(t)
        dx = end.x() - point_before.x()
        dy = end.y() - point_before.y()

        # Normalize
        length = (dx * dx + dy * dy) ** 0.5
        if length > 0:
            dx /= length
            dy /= length

        # Arrow dimensions
        arrow_size = 8
        angle = 0.5  # ~30 degrees

        # Arrow points
        p1 = QPointF(
            end.x() - arrow_size * (dx + angle * dy),
            end.y() - arrow_size * (dy - angle * dx),
        )
        p2 = QPointF(
            end.x() - arrow_size * (dx - angle * dy),
            end.y() - arrow_size * (dy + angle * dx),
        )

        arrow_path = QPainterPath()
        arrow_path.moveTo(end)
        arrow_path.lineTo(p1)
        arrow_path.lineTo(p2)
        arrow_path.closeSubpath()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPath(arrow_path)

    def _draw_label(self, painter: QPainter) -> None:
        """Draw connection label at midpoint."""
        midpoint = self.get_midpoint()

        # Determine label text
        text = self.label or f"S{self.signal_id}"

        # Draw background pill
        font = QFont("Helvetica Neue", 9)
        painter.setFont(font)
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        text_height = fm.height()

        padding = 4
        rect = QRectF(
            midpoint.x() - text_width / 2 - padding,
            midpoint.y() - text_height / 2 - padding,
            text_width + padding * 2,
            text_height + padding * 2,
        )

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#27272A")))
        painter.drawRoundedRect(rect, 4, 4)

        # Draw text
        painter.setPen(QPen(QColor("#A1A1AA")))
        painter.drawText(rect, Qt.AlignCenter, text)


# Import stroker
from PySide6.QtGui import QPainterPathStroker


def paint_preview_connection(
    painter: QPainter,
    start: QPointF,
    end: QPointF,
    port_type: PortType,
) -> None:
    """
    Paint a preview connection during drag.

    Args:
        painter: QPainter to draw with
        start: Start point
        end: Current mouse position
        port_type: Type of the source port
    """
    color = QColor(PORT_TYPE_COLORS.get(port_type, "#9CA3AF"))
    color.setAlpha(180)

    path = QPainterPath()
    path.moveTo(start)

    dx = abs(end.x() - start.x())
    offset = max(40, min(dx * 0.5, 100))

    ctrl1 = QPointF(start.x() + offset, start.y())
    ctrl2 = QPointF(end.x() - offset, end.y())

    path.cubicTo(ctrl1, ctrl2, end)

    painter.setPen(QPen(color, 2, Qt.DashLine, Qt.RoundCap))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)

    # Draw circle at end
    painter.setPen(QPen(color, 2))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(end, 4, 4)
