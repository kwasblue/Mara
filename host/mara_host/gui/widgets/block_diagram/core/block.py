# mara_host/gui/widgets/block_diagram/core/block.py
"""Base block class for diagram elements."""

from abc import ABC, abstractmethod
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, QSizeF
from PySide6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QPainterPath,
)
from PySide6.QtWidgets import QDialog, QWidget

from .models import BlockConfig
from .port import Port


class BlockBase(ABC):
    """
    Abstract base class for diagram blocks.

    Blocks are visual elements that can be placed on the canvas,
    connected via ports, and configured via dialogs.
    """

    # Default dimensions
    DEFAULT_WIDTH = 100
    DEFAULT_HEIGHT = 60
    CORNER_RADIUS = 8

    def __init__(self, config: BlockConfig):
        """
        Initialize block.

        Args:
            config: Block configuration
        """
        self.config = config
        self._position = QPointF(config.x, config.y)
        self._size = QSizeF(config.width, config.height)

        # State
        self._selected = False
        self._hovered = False
        self._dragging = False

        # Ports
        self._input_ports: list[Port] = []
        self._output_ports: list[Port] = []
        self._setup_ports()

    @property
    def block_id(self) -> str:
        """Get unique block identifier."""
        return self.config.block_id

    @property
    def block_type(self) -> str:
        """Get block type name."""
        return self.config.block_type

    @property
    def label(self) -> str:
        """Get block label."""
        return self.config.label

    @property
    def position(self) -> QPointF:
        """Get block position."""
        return self._position

    @position.setter
    def position(self, pos: QPointF) -> None:
        """Set block position and update config."""
        self._position = pos
        self.config.x = pos.x()
        self.config.y = pos.y()
        self._update_port_positions()

    @property
    def size(self) -> QSizeF:
        """Get block size."""
        return self._size

    @property
    def rect(self) -> QRectF:
        """Get block bounding rectangle."""
        return QRectF(self._position, self._size)

    @property
    def center(self) -> QPointF:
        """Get block center point."""
        return QPointF(
            self._position.x() + self._size.width() / 2,
            self._position.y() + self._size.height() / 2,
        )

    @property
    def input_ports(self) -> list[Port]:
        """Get input ports."""
        return self._input_ports

    @property
    def output_ports(self) -> list[Port]:
        """Get output ports."""
        return self._output_ports

    @property
    def all_ports(self) -> list[Port]:
        """Get all ports."""
        return self._input_ports + self._output_ports

    def _setup_ports(self) -> None:
        """Create ports from config."""
        for port_config in self.config.input_ports:
            port = Port(port_config, self.block_id)
            self._input_ports.append(port)

        for port_config in self.config.output_ports:
            port = Port(port_config, self.block_id)
            self._output_ports.append(port)

        self._update_port_positions()

    def _update_port_positions(self) -> None:
        """Update port positions based on block position and size."""
        # Input ports on left side
        for i, port in enumerate(self._input_ports):
            ratio = port.config.position_ratio
            if len(self._input_ports) > 1 and ratio == 0.5:
                # Auto-distribute if using default ratio
                ratio = (i + 1) / (len(self._input_ports) + 1)
            port.position = QPointF(
                self._position.x(),
                self._position.y() + self._size.height() * ratio,
            )

        # Output ports on right side
        for i, port in enumerate(self._output_ports):
            ratio = port.config.position_ratio
            if len(self._output_ports) > 1 and ratio == 0.5:
                ratio = (i + 1) / (len(self._output_ports) + 1)
            port.position = QPointF(
                self._position.x() + self._size.width(),
                self._position.y() + self._size.height() * ratio,
            )

    def get_port(self, port_id: str) -> Optional[Port]:
        """Get port by local ID."""
        for port in self.all_ports:
            if port.config.port_id == port_id:
                return port
        return None

    def set_selected(self, selected: bool) -> None:
        """Set selection state."""
        self._selected = selected

    def set_hovered(self, hovered: bool) -> None:
        """Set hover state."""
        self._hovered = hovered

    def set_dragging(self, dragging: bool) -> None:
        """Set dragging state."""
        self._dragging = dragging

    def contains(self, point: QPointF) -> bool:
        """Check if point is within block."""
        return self.rect.contains(point)

    def port_at(self, point: QPointF) -> Optional[Port]:
        """Get port at point, if any."""
        for port in self.all_ports:
            if port.contains(point):
                return port
        return None

    # --- Painting ---

    def get_background_color(self) -> QColor:
        """Get background color based on state."""
        if self._selected:
            return QColor("#2E2E33")
        if self._hovered:
            return QColor("#27272A")
        return QColor("#1F1F23")

    def get_border_color(self) -> QColor:
        """Get border color based on state."""
        if self._selected:
            return QColor("#3B82F6")  # Accent blue
        if self._hovered:
            return QColor("#52525B")
        return QColor("#27272A")

    @abstractmethod
    def get_icon_color(self) -> QColor:
        """Get icon/accent color for this block type."""
        pass

    def paint(self, painter: QPainter) -> None:
        """
        Paint the block.

        Args:
            painter: QPainter to draw with
        """
        rect = self.rect

        # Draw shadow for selected/hovered
        if self._selected or self._hovered:
            shadow_offset = 2
            shadow_rect = rect.adjusted(shadow_offset, shadow_offset, shadow_offset, shadow_offset)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
            path = QPainterPath()
            path.addRoundedRect(shadow_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)
            painter.drawPath(path)

        # Draw background
        painter.setPen(QPen(self.get_border_color(), 2 if self._selected else 1))
        painter.setBrush(QBrush(self.get_background_color()))
        path = QPainterPath()
        path.addRoundedRect(rect, self.CORNER_RADIUS, self.CORNER_RADIUS)
        painter.drawPath(path)

        # Draw icon bar on left
        icon_width = 8
        icon_rect = QRectF(
            rect.x(),
            rect.y(),
            icon_width,
            rect.height(),
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.get_icon_color()))
        icon_path = QPainterPath()
        icon_path.addRoundedRect(icon_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)
        # Clip to left half only
        clip_rect = QRectF(rect.x(), rect.y(), icon_width, rect.height())
        painter.setClipRect(clip_rect)
        painter.drawPath(icon_path)
        painter.setClipping(False)

        # Draw label
        painter.setPen(QPen(QColor("#FAFAFA")))
        font = QFont("Helvetica Neue", 11)
        font.setWeight(QFont.Medium)
        painter.setFont(font)

        text_rect = rect.adjusted(icon_width + 8, 8, -8, -8)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.label)

        # Draw custom content (subclass override)
        self.paint_content(painter, rect)

        # Draw ports
        for port in self.all_ports:
            port.paint(painter)

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """
        Paint custom block content. Override in subclasses.

        Args:
            painter: QPainter to draw with
            rect: Block rectangle
        """
        pass

    # --- Configuration ---

    @abstractmethod
    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        """
        Get configuration dialog for this block.

        Args:
            parent: Parent widget for dialog

        Returns:
            QDialog instance, or None if no configuration
        """
        pass

    def apply_config(self, config: dict) -> None:
        """
        Apply configuration from dialog.

        Args:
            config: Configuration dictionary
        """
        self.config.properties.update(config)

    def get_properties(self) -> dict:
        """Get current block properties."""
        return self.config.properties.copy()


# Import Qt.NoPen and Qt.AlignLeft etc
from PySide6.QtCore import Qt
