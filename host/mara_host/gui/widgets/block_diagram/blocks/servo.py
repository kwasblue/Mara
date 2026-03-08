# mara_host/gui/widgets/block_diagram/blocks/servo.py
"""Servo motor block."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QSpinBox,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
)

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType


def create_servo_config(
    block_id: str,
    label: str = "Servo",
    servo_id: int = 0,
) -> BlockConfig:
    """Create configuration for a servo block."""
    return BlockConfig(
        block_type="servo",
        block_id=block_id,
        label=label,
        width=90,
        height=60,
        input_ports=[
            PortConfig(
                port_id="PWM",
                label="PWM",
                kind=PortKind.INPUT,
                port_type=PortType.PWM,
                position_ratio=0.5,
            ),
        ],
        output_ports=[],
        properties={
            "servo_id": servo_id,
            "name": label,
            "min_us": 500,
            "max_us": 2500,
            "min_angle": 0,
            "max_angle": 180,
        },
    )


class ServoBlock(BlockBase):
    """
    Servo motor block.

    Accepts a PWM input for position control.
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Servo",
        servo_id: int = 0,
    ):
        config = create_servo_config(block_id, label, servo_id)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        """Servos use orange accent."""
        return QColor("#F59E0B")

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint servo-specific content."""
        # Draw servo body
        body_x = rect.x() + 25
        body_y = rect.y() + 25
        body_w = rect.width() - 35
        body_h = 25

        painter.setPen(QPen(QColor("#F59E0B"), 1))
        painter.setBrush(QBrush(QColor("#2D2510")))
        painter.drawRoundedRect(QRectF(body_x, body_y, body_w, body_h), 3, 3)

        # Draw servo horn (output shaft)
        horn_x = body_x + body_w - 8
        horn_y = body_y + body_h / 2

        painter.setPen(QPen(QColor("#A1A1AA"), 1))
        painter.setBrush(QBrush(QColor("#52525B")))

        # Horn base circle
        painter.drawEllipse(int(horn_x - 6), int(horn_y - 6), 12, 12)

        # Horn arm
        path = QPainterPath()
        path.moveTo(horn_x, horn_y - 4)
        path.lineTo(horn_x + 12, horn_y - 2)
        path.lineTo(horn_x + 12, horn_y + 2)
        path.lineTo(horn_x, horn_y + 4)
        path.closeSubpath()
        painter.drawPath(path)

        # Servo label
        painter.setFont(QFont("Helvetica Neue", 7))
        painter.setPen(QPen(QColor("#F59E0B")))
        painter.drawText(
            QRectF(body_x + 3, body_y + 3, body_w - 15, body_h - 6),
            Qt.AlignLeft | Qt.AlignVCenter,
            "SRV",
        )

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        """Get servo configuration dialog."""
        return ServoConfigDialog(self.config.properties, parent)


class ServoConfigDialog(QDialog):
    """Configuration dialog for servo."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Servo Configuration")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        # Basic settings
        basic_group = QGroupBox("Servo Settings")
        form = QFormLayout(basic_group)

        self.name_edit = QLineEdit(self._properties.get("name", "Servo"))
        form.addRow("Name:", self.name_edit)

        self.id_spin = QSpinBox()
        self.id_spin.setRange(0, 15)
        self.id_spin.setValue(self._properties.get("servo_id", 0))
        form.addRow("Servo ID:", self.id_spin)

        layout.addWidget(basic_group)

        # PWM timing
        timing_group = QGroupBox("PWM Timing")
        timing_form = QFormLayout(timing_group)

        self.min_us_spin = QSpinBox()
        self.min_us_spin.setRange(100, 2000)
        self.min_us_spin.setValue(self._properties.get("min_us", 500))
        self.min_us_spin.setSuffix(" us")
        timing_form.addRow("Min Pulse:", self.min_us_spin)

        self.max_us_spin = QSpinBox()
        self.max_us_spin.setRange(1000, 3000)
        self.max_us_spin.setValue(self._properties.get("max_us", 2500))
        self.max_us_spin.setSuffix(" us")
        timing_form.addRow("Max Pulse:", self.max_us_spin)

        layout.addWidget(timing_group)

        # Angle range
        angle_group = QGroupBox("Angle Range")
        angle_form = QFormLayout(angle_group)

        self.min_angle_spin = QSpinBox()
        self.min_angle_spin.setRange(-180, 180)
        self.min_angle_spin.setValue(self._properties.get("min_angle", 0))
        self.min_angle_spin.setSuffix(" deg")
        angle_form.addRow("Min Angle:", self.min_angle_spin)

        self.max_angle_spin = QSpinBox()
        self.max_angle_spin.setRange(-180, 360)
        self.max_angle_spin.setValue(self._properties.get("max_angle", 180))
        self.max_angle_spin.setSuffix(" deg")
        angle_form.addRow("Max Angle:", self.max_angle_spin)

        layout.addWidget(angle_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        """Get configuration from dialog."""
        return {
            "name": self.name_edit.text(),
            "servo_id": self.id_spin.value(),
            "min_us": self.min_us_spin.value(),
            "max_us": self.max_us_spin.value(),
            "min_angle": self.min_angle_spin.value(),
            "max_angle": self.max_angle_spin.value(),
        }
