# mara_host/gui/widgets/block_diagram/blocks/servo.py
"""Servo motor block."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath
from PySide6.QtWidgets import QDialog, QWidget

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType
from ..dialogs.base import BaseBlockConfigDialog, FieldDef


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


class ServoConfigDialog(BaseBlockConfigDialog):
    """Configuration dialog for servo."""

    dialog_title = "Servo Configuration"
    show_live_tune = False
    fields = [
        # Basic settings
        FieldDef("name", "Name", field_type="str", default="Servo"),
        FieldDef("servo_id", "Servo ID", field_type="int", default=0, min_val=0, max_val=15),
        # PWM timing
        FieldDef("min_us", "Min Pulse", field_type="int", default=500, min_val=100, max_val=2000,
                 suffix="us", group="PWM Timing"),
        FieldDef("max_us", "Max Pulse", field_type="int", default=2500, min_val=1000, max_val=3000,
                 suffix="us", group="PWM Timing"),
        # Angle range
        FieldDef("min_angle", "Min Angle", field_type="int", default=0, min_val=-180, max_val=180,
                 suffix="deg", group="Angle Range"),
        FieldDef("max_angle", "Max Angle", field_type="int", default=180, min_val=-180, max_val=360,
                 suffix="deg", group="Angle Range"),
    ]
