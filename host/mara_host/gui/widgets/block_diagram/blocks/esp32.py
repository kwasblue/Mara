# mara_host/gui/widgets/block_diagram/blocks/esp32.py
"""ESP32 MCU block with GPIO ports."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath
from PySide6.QtWidgets import QDialog, QWidget

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType
from ..core.port import Port
from ..core.esp32_pinout import get_pin_info, PIN_CATEGORY_COLORS


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
            try:
                gpio_num = int(gpio_str)
                assigned = self._pin_assignments.get(gpio_num)
            except ValueError:
                assigned = None
                gpio_num = None

            if assigned:
                painter.setPen(QPen(QColor("#22C55E")))  # Green for assigned
                text = f"{gpio_str}:{assigned[:6]}"
            else:
                # Use ESP32 pinout color based on pin category
                color = self._get_gpio_label_color(gpio_num)
                painter.setPen(QPen(color))
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
            try:
                gpio_num = int(gpio_str)
                assigned = self._pin_assignments.get(gpio_num)
            except ValueError:
                assigned = None
                gpio_num = None

            if assigned:
                painter.setPen(QPen(QColor("#22C55E")))
                text = f"{assigned[:6]}:{gpio_str}"
            else:
                # Use ESP32 pinout color based on pin category
                color = self._get_gpio_label_color(gpio_num)
                painter.setPen(QPen(color))
                text = gpio_str

            text_rect = QRectF(
                rect.right() - chip_margin - 35,
                port.position.y() - 6,
                chip_margin + 10,
                12,
            )
            painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, text)

    def _get_gpio_label_color(self, gpio: Optional[int]) -> QColor:
        """Get color for GPIO label based on pin category."""
        if gpio is None:
            return QColor("#71717A")

        pin_info = get_pin_info(gpio)
        if not pin_info:
            return QColor("#71717A")

        # Use category colors for visual feedback
        category = pin_info.color_category
        color_hex = PIN_CATEGORY_COLORS.get(category)
        if color_hex:
            return QColor(color_hex)

        return QColor("#71717A")

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        """ESP32 has no additional config dialog for now."""
        return None

    def handle_port_click(self, port: Port, global_pos: QPointF) -> bool:
        """
        Handle click on a GPIO port - show pin info popup.

        Args:
            port: The port that was clicked
            global_pos: Global position for popup placement

        Returns:
            True if handled, False otherwise
        """
        # Extract GPIO number from port ID (e.g., "GPIO23" -> 23)
        port_id = port.config.port_id
        if port_id.startswith("GPIO"):
            try:
                gpio = int(port_id[4:])
                self._show_pin_info(gpio, global_pos)
                return True
            except ValueError:
                pass
        return False

    def _show_pin_info(self, gpio: int, pos: QPointF) -> None:
        """Show pin info dialog for a GPIO."""
        from ..dialogs.pin_info import PinInfoDialog

        # Create and show dialog
        dialog = PinInfoDialog(gpio)
        dialog.move(int(pos.x()), int(pos.y()))
        dialog.exec()

    def get_port_color(self, port: Port) -> Optional[QColor]:
        """
        Get custom color for a port based on ESP32 pinout info.

        Returns:
            QColor if custom color should be used, None for default
        """
        port_id = port.config.port_id
        if not port_id.startswith("GPIO"):
            return None

        try:
            gpio = int(port_id[4:])
            pin_info = get_pin_info(gpio)
            if pin_info:
                category = pin_info.color_category
                color_hex = PIN_CATEGORY_COLORS.get(category)
                if color_hex:
                    return QColor(color_hex)
        except ValueError:
            pass

        return None
