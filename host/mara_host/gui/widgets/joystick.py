# mara_host/gui/widgets/joystick.py
"""
Virtual joystick widget for velocity control.
"""

import math

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen, QBrush


class JoystickWidget(QWidget):
    """
    Virtual joystick for arcade-style velocity control.

    Emits normalized (-1, 1) x, y values as the handle is dragged.
    Auto-centers when released.

    Signals:
        velocity_changed(x, y): Emitted when position changes
            x: -1 (left) to 1 (right)
            y: -1 (back) to 1 (forward)
    """

    velocity_changed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(150, 150)
        self.setMaximumSize(300, 300)

        self._handle_pos = QPointF(0, 0)  # Normalized -1 to 1
        self._dragging = False

        # Colors - minimal palette
        self._bg_color = QColor("#1F1F23")
        self._ring_color = QColor("#27272A")
        self._handle_color = QColor("#FAFAFA")
        self._handle_highlight = QColor("#3B82F6")
        self._crosshair_color = QColor("#27272A")

    def _radius(self) -> float:
        """Get the joystick area radius."""
        return min(self.width(), self.height()) / 2 - 10

    def _center(self) -> QPointF:
        """Get the center point."""
        return QPointF(self.width() / 2, self.height() / 2)

    def _handle_radius(self) -> float:
        """Get the handle radius."""
        return self._radius() * 0.25

    def paintEvent(self, event) -> None:
        """Paint the joystick."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self._center()
        radius = self._radius()
        handle_radius = self._handle_radius()

        # Background circle
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(QPen(self._ring_color, 2))
        painter.drawEllipse(center, radius, radius)

        # Crosshairs
        painter.setPen(QPen(self._crosshair_color, 1))
        painter.drawLine(
            int(center.x() - radius), int(center.y()),
            int(center.x() + radius), int(center.y())
        )
        painter.drawLine(
            int(center.x()), int(center.y() - radius),
            int(center.x()), int(center.y() + radius)
        )

        # Inner guide circle
        painter.setPen(QPen(self._crosshair_color, 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, radius * 0.5, radius * 0.5)

        # Handle position in pixels
        handle_x = center.x() + self._handle_pos.x() * (radius - handle_radius)
        handle_y = center.y() - self._handle_pos.y() * (radius - handle_radius)

        # Handle gradient
        gradient = QRadialGradient(handle_x, handle_y, handle_radius)
        if self._dragging:
            gradient.setColorAt(0, self._handle_highlight)
            gradient.setColorAt(1, self._handle_color)
        else:
            gradient.setColorAt(0, self._handle_color.lighter(120))
            gradient.setColorAt(1, self._handle_color)

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(self._handle_color.darker(120), 2))
        painter.drawEllipse(QPointF(handle_x, handle_y), handle_radius, handle_radius)

    def mousePressEvent(self, event) -> None:
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._update_position(event.position())

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move."""
        if self._dragging:
            self._update_position(event.position())

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release - auto-center."""
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._handle_pos = QPointF(0, 0)
            self.update()
            self.velocity_changed.emit(0.0, 0.0)

    def _update_position(self, pos: QPointF) -> None:
        """Update handle position from mouse position."""
        center = self._center()
        radius = self._radius() - self._handle_radius()

        # Calculate offset from center
        dx = pos.x() - center.x()
        dy = center.y() - pos.y()  # Invert Y

        # Calculate distance
        distance = math.sqrt(dx * dx + dy * dy)

        # Clamp to circle
        if distance > radius:
            scale = radius / distance
            dx *= scale
            dy *= scale

        # Normalize to -1 to 1
        self._handle_pos = QPointF(dx / radius, dy / radius)

        self.update()
        self.velocity_changed.emit(
            self._handle_pos.x(),
            self._handle_pos.y()
        )

    def reset(self) -> None:
        """Reset joystick to center."""
        self._handle_pos = QPointF(0, 0)
        self._dragging = False
        self.update()
        self.velocity_changed.emit(0.0, 0.0)

    @property
    def x(self) -> float:
        """Get current X position (-1 to 1)."""
        return self._handle_pos.x()

    @property
    def y(self) -> float:
        """Get current Y position (-1 to 1)."""
        return self._handle_pos.y()
