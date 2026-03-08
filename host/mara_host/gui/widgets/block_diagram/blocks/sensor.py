# mara_host/gui/widgets/block_diagram/blocks/sensor.py
"""Sensor blocks (IMU, ultrasonic, etc.)."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
)

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType


def _build_sensor_types() -> dict:
    """Build SENSOR_TYPES from hardware registry."""
    try:
        from mara_host.tools.schema.hardware import HARDWARE
    except ImportError:
        # Fallback if schema not available
        return {}

    sensor_types = {}
    for key, hw in HARDWARE.items():
        if hw.get("type") != "sensor":
            continue

        gui = hw.get("gui", {})
        interface = hw.get("interface", "gpio")

        # Convert outputs from hardware format to GUI format
        outputs = []
        for port_id, port_label in gui.get("outputs", []):
            port_type = PortType.SIGNAL
            if interface == "gpio":
                port_type = PortType.GPIO
            outputs.append((port_id, port_label, port_type))

        # Convert inputs
        inputs = []
        for port_id, port_label in gui.get("inputs", []):
            port_type = PortType.GPIO if interface == "gpio" else PortType.SIGNAL
            inputs.append((port_id, port_label, port_type))

        sensor_types[key] = {
            "label": gui.get("label", key.title()),
            "color": gui.get("color", "#71717A"),
            "interface": interface,
            "outputs": outputs,
            "inputs": inputs,
        }

    return sensor_types


# Sensor type configurations (auto-generated from hardware registry)
SENSOR_TYPES = _build_sensor_types()

# Fallback if hardware registry not available
if not SENSOR_TYPES:
    SENSOR_TYPES = {
        "imu": {
            "label": "IMU",
            "color": "#22C55E",
            "interface": "i2c",
            "outputs": [("accel", "Accel", PortType.SIGNAL), ("gyro", "Gyro", PortType.SIGNAL)],
        },
        "ultrasonic": {
            "label": "Ultrasonic",
            "color": "#3B82F6",
            "interface": "gpio",
            "inputs": [("trig", "TRIG", PortType.GPIO)],
            "outputs": [("echo", "ECHO", PortType.GPIO)],
        },
    }


def create_sensor_config(
    block_id: str,
    sensor_type: str = "imu",
    label: Optional[str] = None,
) -> BlockConfig:
    """Create configuration for a sensor block."""
    type_config = SENSOR_TYPES.get(sensor_type, SENSOR_TYPES["imu"])
    display_label = label or type_config["label"]

    input_ports = []
    output_ports = []

    # Add I2C ports if I2C interface
    if type_config["interface"] == "i2c":
        input_ports.append(
            PortConfig(
                port_id="SDA",
                label="SDA",
                kind=PortKind.INPUT,
                port_type=PortType.I2C,
                position_ratio=0.33,
            )
        )
        input_ports.append(
            PortConfig(
                port_id="SCL",
                label="SCL",
                kind=PortKind.INPUT,
                port_type=PortType.I2C,
                position_ratio=0.67,
            )
        )

    # Add custom inputs
    for i, (port_id, port_label, port_type) in enumerate(type_config.get("inputs", [])):
        ratio = (i + 1) / (len(type_config.get("inputs", [])) + 1)
        input_ports.append(
            PortConfig(
                port_id=port_id,
                label=port_label,
                kind=PortKind.INPUT,
                port_type=port_type,
                position_ratio=ratio,
            )
        )

    # Add outputs
    for i, (port_id, port_label, port_type) in enumerate(type_config.get("outputs", [])):
        ratio = (i + 1) / (len(type_config.get("outputs", [])) + 1)
        output_ports.append(
            PortConfig(
                port_id=port_id,
                label=port_label,
                kind=PortKind.OUTPUT,
                port_type=port_type,
                position_ratio=ratio,
            )
        )

    return BlockConfig(
        block_type="sensor",
        block_id=block_id,
        label=display_label,
        width=90,
        height=70,
        input_ports=input_ports,
        output_ports=output_ports,
        properties={
            "sensor_type": sensor_type,
            "name": display_label,
            "interface": type_config["interface"],
            "i2c_address": 0x68 if type_config["interface"] == "i2c" else None,
        },
    )


class SensorBlock(BlockBase):
    """
    Generic sensor block.

    Supports various sensor types: IMU, ultrasonic, IR, temperature, etc.
    """

    def __init__(
        self,
        block_id: str,
        sensor_type: str = "imu",
        label: Optional[str] = None,
    ):
        config = create_sensor_config(block_id, sensor_type, label)
        super().__init__(config)
        self._sensor_type = sensor_type

    def get_icon_color(self) -> QColor:
        """Get color for sensor type."""
        type_config = SENSOR_TYPES.get(self._sensor_type, SENSOR_TYPES["imu"])
        return QColor(type_config["color"])

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint sensor-specific content."""
        type_config = SENSOR_TYPES.get(self._sensor_type, {})
        color = QColor(type_config.get("color", "#22C55E"))

        # Draw sensor symbol
        center_x = rect.x() + rect.width() / 2
        center_y = rect.y() + rect.height() / 2 + 5

        # Sensor icon based on type
        if self._sensor_type == "imu":
            self._draw_imu_icon(painter, center_x, center_y, color)
        elif self._sensor_type == "ultrasonic":
            self._draw_ultrasonic_icon(painter, center_x, center_y, color)
        elif self._sensor_type == "ir":
            self._draw_ir_icon(painter, center_x, center_y, color)
        else:
            # Generic sensor icon
            self._draw_generic_icon(painter, center_x, center_y, color)

        # Interface label
        interface = type_config.get("interface", "")
        painter.setFont(QFont("Helvetica Neue", 7))
        painter.setPen(QPen(QColor("#71717A")))
        painter.drawText(
            QRectF(rect.x() + 12, rect.bottom() - 16, rect.width() - 24, 12),
            Qt.AlignCenter,
            interface.upper(),
        )

    def _draw_imu_icon(self, painter: QPainter, cx: float, cy: float, color: QColor) -> None:
        """Draw IMU icon (3-axis arrows)."""
        painter.setPen(QPen(color, 2))

        # X axis
        painter.drawLine(int(cx - 10), int(cy), int(cx + 10), int(cy))
        painter.drawLine(int(cx + 10), int(cy), int(cx + 6), int(cy - 3))

        # Y axis
        painter.drawLine(int(cx), int(cy - 10), int(cx), int(cy + 10))
        painter.drawLine(int(cx), int(cy - 10), int(cx - 3), int(cy - 6))

        # Z axis (diagonal)
        painter.drawLine(int(cx - 5), int(cy + 5), int(cx + 5), int(cy - 5))

    def _draw_ultrasonic_icon(self, painter: QPainter, cx: float, cy: float, color: QColor) -> None:
        """Draw ultrasonic icon (waves)."""
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.NoBrush)

        # Draw concentric arcs
        for i in range(3):
            r = 6 + i * 5
            painter.drawArc(int(cx - r), int(cy - r), int(r * 2), int(r * 2), 45 * 16, 90 * 16)

    def _draw_ir_icon(self, painter: QPainter, cx: float, cy: float, color: QColor) -> None:
        """Draw IR sensor icon."""
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color))

        # LED symbol
        painter.drawEllipse(int(cx - 5), int(cy - 5), 10, 10)

        # Rays
        painter.setPen(QPen(color, 1))
        import math
        for i in range(5):
            angle = math.radians(-60 + i * 30)
            x2 = cx + 15 * math.cos(angle)
            y2 = cy - 15 * math.sin(angle)
            painter.drawLine(int(cx + 6 * math.cos(angle)), int(cy - 6 * math.sin(angle)),
                           int(x2), int(y2))

    def _draw_generic_icon(self, painter: QPainter, cx: float, cy: float, color: QColor) -> None:
        """Draw generic sensor icon."""
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color.darker(150)))
        painter.drawRoundedRect(QRectF(cx - 12, cy - 8, 24, 16), 3, 3)

        painter.setPen(QPen(QColor("#FAFAFA")))
        painter.setFont(QFont("Helvetica Neue", 8))
        painter.drawText(QRectF(cx - 12, cy - 8, 24, 16), Qt.AlignCenter, "S")

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        """Get sensor configuration dialog."""
        return SensorConfigDialog(self.config.properties, parent)


class SensorConfigDialog(QDialog):
    """Configuration dialog for sensor."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Sensor Configuration")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        group = QGroupBox("Sensor Settings")
        form = QFormLayout(group)

        self.name_edit = QLineEdit(self._properties.get("name", "Sensor"))
        form.addRow("Name:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(list(SENSOR_TYPES.keys()))
        current_type = self._properties.get("sensor_type", "imu")
        self.type_combo.setCurrentText(current_type)
        form.addRow("Type:", self.type_combo)

        # I2C address (only for I2C sensors)
        self.address_edit = QLineEdit()
        addr = self._properties.get("i2c_address")
        if addr:
            self.address_edit.setText(f"0x{addr:02X}")
        else:
            self.address_edit.setText("0x68")
        form.addRow("I2C Address:", self.address_edit)

        layout.addWidget(group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        """Get configuration from dialog."""
        addr_text = self.address_edit.text()
        try:
            addr = int(addr_text, 16) if addr_text.startswith("0x") else int(addr_text)
        except ValueError:
            addr = 0x68

        return {
            "name": self.name_edit.text(),
            "sensor_type": self.type_combo.currentText(),
            "i2c_address": addr,
        }
