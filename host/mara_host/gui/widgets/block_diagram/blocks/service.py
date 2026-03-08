# mara_host/gui/widgets/block_diagram/blocks/service.py
"""Service blocks representing MARA host services."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import QDialog, QWidget

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType


# --- Motor Service Block ---

def create_motor_service_config(
    block_id: str,
    label: str = "MotorService",
) -> BlockConfig:
    """Create configuration for a motor service block."""
    return BlockConfig(
        block_type="motor_service",
        block_id=block_id,
        label=label,
        width=120,
        height=100,
        input_ports=[
            PortConfig(
                port_id="speed_0",
                label="M0",
                kind=PortKind.INPUT,
                port_type=PortType.OUT,
                position_ratio=0.2,
            ),
            PortConfig(
                port_id="speed_1",
                label="M1",
                kind=PortKind.INPUT,
                port_type=PortType.OUT,
                position_ratio=0.4,
            ),
            PortConfig(
                port_id="speed_2",
                label="M2",
                kind=PortKind.INPUT,
                port_type=PortType.OUT,
                position_ratio=0.6,
            ),
            PortConfig(
                port_id="speed_3",
                label="M3",
                kind=PortKind.INPUT,
                port_type=PortType.OUT,
                position_ratio=0.8,
            ),
        ],
        output_ports=[
            PortConfig(
                port_id="enc_0",
                label="E0",
                kind=PortKind.OUTPUT,
                port_type=PortType.MEAS,
                position_ratio=0.25,
            ),
            PortConfig(
                port_id="enc_1",
                label="E1",
                kind=PortKind.OUTPUT,
                port_type=PortType.MEAS,
                position_ratio=0.5,
            ),
            PortConfig(
                port_id="enc_2",
                label="E2",
                kind=PortKind.OUTPUT,
                port_type=PortType.MEAS,
                position_ratio=0.75,
            ),
        ],
        properties={
            "n_motors": 4,
            "n_encoders": 3,
        },
    )


class MotorServiceBlock(BlockBase):
    """
    Motor Service block.

    Represents the MotorService in the MARA system.
    Accepts speed commands and outputs encoder feedback.
    """

    def __init__(self, block_id: str, label: str = "MotorService"):
        config = create_motor_service_config(block_id, label)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        return QColor("#EF4444")

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint service-specific content."""
        # Draw service icon (gear)
        center_x = rect.x() + rect.width() / 2
        center_y = rect.y() + 50

        painter.setPen(QPen(QColor("#EF4444"), 2))
        painter.setBrush(Qt.NoBrush)

        # Simple gear representation
        import math
        radius = 15
        teeth = 8
        for i in range(teeth):
            angle = 2 * math.pi * i / teeth
            x1 = center_x + radius * 0.7 * math.cos(angle)
            y1 = center_y + radius * 0.7 * math.sin(angle)
            x2 = center_x + radius * math.cos(angle)
            y2 = center_y + radius * math.sin(angle)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.drawEllipse(int(center_x - radius * 0.7), int(center_y - radius * 0.7),
                           int(radius * 1.4), int(radius * 1.4))

        # Inner circle
        painter.setBrush(QBrush(QColor("#1F1F23")))
        painter.drawEllipse(int(center_x - 5), int(center_y - 5), 10, 10)

        # Port labels on sides
        painter.setFont(QFont("Consolas", 7))
        painter.setPen(QPen(QColor("#71717A")))

        # Left side labels
        for i, port in enumerate(self._input_ports):
            y = port.position.y()
            painter.drawText(int(rect.x() + 12), int(y + 3), port.config.label)

        # Right side labels
        for i, port in enumerate(self._output_ports):
            y = port.position.y()
            painter.drawText(int(rect.right() - 22), int(y + 3), port.config.label)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return None  # Service blocks have no config


# --- Servo Service Block ---

def create_servo_service_config(
    block_id: str,
    label: str = "ServoService",
) -> BlockConfig:
    """Create configuration for a servo service block."""
    return BlockConfig(
        block_type="servo_service",
        block_id=block_id,
        label=label,
        width=100,
        height=80,
        input_ports=[
            PortConfig(
                port_id="angle_0",
                label="S0",
                kind=PortKind.INPUT,
                port_type=PortType.OUT,
                position_ratio=0.25,
            ),
            PortConfig(
                port_id="angle_1",
                label="S1",
                kind=PortKind.INPUT,
                port_type=PortType.OUT,
                position_ratio=0.5,
            ),
            PortConfig(
                port_id="angle_2",
                label="S2",
                kind=PortKind.INPUT,
                port_type=PortType.OUT,
                position_ratio=0.75,
            ),
        ],
        output_ports=[],
        properties={
            "n_servos": 3,
        },
    )


class ServoServiceBlock(BlockBase):
    """
    Servo Service block.

    Represents the ServoService in the MARA system.
    Accepts angle commands for servo motors.
    """

    def __init__(self, block_id: str, label: str = "ServoService"):
        config = create_servo_service_config(block_id, label)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        return QColor("#F59E0B")

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint service content."""
        # Draw servo horn icon
        center_x = rect.x() + rect.width() / 2 + 10
        center_y = rect.y() + 45

        painter.setPen(QPen(QColor("#F59E0B"), 2))
        painter.setBrush(QBrush(QColor("#2D2510")))

        # Servo body
        painter.drawRoundedRect(QRectF(center_x - 20, center_y - 8, 30, 16), 2, 2)

        # Horn
        painter.setPen(QPen(QColor("#A1A1AA"), 1))
        painter.setBrush(QBrush(QColor("#52525B")))
        painter.drawEllipse(int(center_x + 5), int(center_y - 5), 10, 10)

        # Port labels
        painter.setFont(QFont("Consolas", 7))
        painter.setPen(QPen(QColor("#71717A")))
        for port in self._input_ports:
            y = port.position.y()
            painter.drawText(int(rect.x() + 12), int(y + 3), port.config.label)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return None


# --- GPIO Service Block ---

def create_gpio_service_config(
    block_id: str,
    label: str = "GPIOService",
) -> BlockConfig:
    """Create configuration for a GPIO service block."""
    return BlockConfig(
        block_type="gpio_service",
        block_id=block_id,
        label=label,
        width=100,
        height=90,
        input_ports=[
            PortConfig(
                port_id="write_0",
                label="W0",
                kind=PortKind.INPUT,
                port_type=PortType.SIGNAL,
                position_ratio=0.25,
            ),
            PortConfig(
                port_id="write_1",
                label="W1",
                kind=PortKind.INPUT,
                port_type=PortType.SIGNAL,
                position_ratio=0.5,
            ),
            PortConfig(
                port_id="write_2",
                label="W2",
                kind=PortKind.INPUT,
                port_type=PortType.SIGNAL,
                position_ratio=0.75,
            ),
        ],
        output_ports=[
            PortConfig(
                port_id="read_0",
                label="R0",
                kind=PortKind.OUTPUT,
                port_type=PortType.SIGNAL,
                position_ratio=0.33,
            ),
            PortConfig(
                port_id="read_1",
                label="R1",
                kind=PortKind.OUTPUT,
                port_type=PortType.SIGNAL,
                position_ratio=0.67,
            ),
        ],
        properties={
            "n_write": 3,
            "n_read": 2,
        },
    )


class GPIOServiceBlock(BlockBase):
    """
    GPIO Service block.

    Represents the GPIOService in the MARA system.
    """

    def __init__(self, block_id: str, label: str = "GPIOService"):
        config = create_gpio_service_config(block_id, label)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        return QColor("#06B6D4")

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint GPIO service content."""
        # Draw GPIO pin array icon
        center_x = rect.x() + rect.width() / 2
        center_y = rect.y() + 50

        painter.setPen(QPen(QColor("#06B6D4"), 1))
        painter.setBrush(QBrush(QColor("#1A2D33")))

        # Draw pin array
        pin_size = 6
        pin_spacing = 10
        rows = 2
        cols = 4

        for row in range(rows):
            for col in range(cols):
                x = center_x - (cols * pin_spacing) / 2 + col * pin_spacing
                y = center_y - (rows * pin_spacing) / 2 + row * pin_spacing
                painter.drawRect(int(x - pin_size/2), int(y - pin_size/2),
                               int(pin_size), int(pin_size))

        # Port labels
        painter.setFont(QFont("Consolas", 7))
        painter.setPen(QPen(QColor("#71717A")))

        for port in self._input_ports:
            y = port.position.y()
            painter.drawText(int(rect.x() + 12), int(y + 3), port.config.label)

        for port in self._output_ports:
            y = port.position.y()
            painter.drawText(int(rect.right() - 20), int(y + 3), port.config.label)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return None
