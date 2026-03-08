# mara_host/gui/widgets/block_diagram/blocks/esp32.py
"""ESP32 MCU block with GPIO ports."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath
from PySide6.QtWidgets import QDialog, QWidget

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType
from ..core.port import Port


# ESP32 DevKit GPIO layout (simplified for diagram)
ESP32_LEFT_GPIOS = [3, 1, 22, 21, 19, 18, 5, 17, 16, 4, 2, 15]
ESP32_RIGHT_GPIOS = [23, 36, 39, 34, 35, 32, 33, 25, 26, 27, 14, 12, 13]


def create_esp32_config(block_id: str, label: str = "ESP32") -> BlockConfig:
    """Create configuration for an ESP32 block."""
    input_ports = []
    output_ports = []

    # Left side GPIOs (can be inputs or outputs)
    for i, gpio in enumerate(ESP32_LEFT_GPIOS):
        ratio = (i + 1) / (len(ESP32_LEFT_GPIOS) + 1)
        input_ports.append(
            PortConfig(
                port_id=f"GPIO{gpio}",
                label=f"GPIO{gpio}",
                kind=PortKind.INPUT,
                port_type=PortType.GPIO,
                position_ratio=ratio,
            )
        )

    # Right side GPIOs
    for i, gpio in enumerate(ESP32_RIGHT_GPIOS):
        ratio = (i + 1) / (len(ESP32_RIGHT_GPIOS) + 1)
        output_ports.append(
            PortConfig(
                port_id=f"GPIO{gpio}",
                label=f"GPIO{gpio}",
                kind=PortKind.OUTPUT,
                port_type=PortType.GPIO,
                position_ratio=ratio,
            )
        )

    return BlockConfig(
        block_type="esp32",
        block_id=block_id,
        label=label,
        width=160,
        height=320,
        input_ports=input_ports,
        output_ports=output_ports,
        properties={
            "variant": "DevKitC",
            "left_gpios": ESP32_LEFT_GPIOS,
            "right_gpios": ESP32_RIGHT_GPIOS,
        },
    )


class ESP32Block(BlockBase):
    """
    ESP32 MCU block with clickable GPIO pins.

    Displays a representation of the ESP32 DevKit with GPIO
    ports along both sides that can be connected to peripherals.
    """

    def __init__(self, block_id: str, label: str = "ESP32"):
        config = create_esp32_config(block_id, label)
        super().__init__(config)

        # Track pin assignments
        self._pin_assignments: dict[int, str] = {}  # gpio -> assignment name

    def get_icon_color(self) -> QColor:
        """ESP32 uses cyan accent."""
        return QColor("#06B6D4")

    def set_pin_assignment(self, gpio: int, name: str) -> None:
        """Set assignment name for a GPIO pin."""
        self._pin_assignments[gpio] = name

    def clear_pin_assignment(self, gpio: int) -> None:
        """Clear assignment for a GPIO pin."""
        self._pin_assignments.pop(gpio, None)

    def get_gpio_port(self, gpio: int) -> Optional[Port]:
        """Get port for a specific GPIO number."""
        port_id = f"GPIO{gpio}"
        return self.get_port(port_id)

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint ESP32-specific content."""
        # Draw chip outline
        chip_margin = 20
        chip_rect = rect.adjusted(chip_margin, 40, -chip_margin, -20)

        # Chip background
        painter.setPen(QPen(QColor("#374151"), 1))
        painter.setBrush(QBrush(QColor("#1F2937")))
        path = QPainterPath()
        path.addRoundedRect(chip_rect, 4, 4)
        painter.drawPath(path)

        # Chip label
        font = QFont("Consolas", 9)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#6B7280")))
        painter.drawText(chip_rect, Qt.AlignCenter, "ESP32\nWROOM")

        # Draw GPIO labels next to ports
        label_font = QFont("Consolas", 8)
        painter.setFont(label_font)

        # Left side labels
        for port in self._input_ports:
            gpio_str = port.config.port_id.replace("GPIO", "")
            assigned = self._pin_assignments.get(int(gpio_str))

            if assigned:
                painter.setPen(QPen(QColor("#22C55E")))  # Green for assigned
                text = f"{gpio_str}:{assigned[:6]}"
            else:
                painter.setPen(QPen(QColor("#71717A")))
                text = gpio_str

            text_rect = QRectF(
                rect.x() + 12,
                port.position.y() - 6,
                chip_margin + 10,
                12,
            )
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

        # Right side labels
        for port in self._output_ports:
            gpio_str = port.config.port_id.replace("GPIO", "")
            assigned = self._pin_assignments.get(int(gpio_str))

            if assigned:
                painter.setPen(QPen(QColor("#22C55E")))
                text = f"{assigned[:6]}:{gpio_str}"
            else:
                painter.setPen(QPen(QColor("#71717A")))
                text = gpio_str

            text_rect = QRectF(
                rect.right() - chip_margin - 35,
                port.position.y() - 6,
                chip_margin + 10,
                12,
            )
            painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, text)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        """ESP32 has no additional config dialog for now."""
        return None
