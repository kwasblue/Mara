# mara_host/gui/widgets/block_diagram/blocks/motor.py
"""DC Motor block with driver pins."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import QDialog, QWidget

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType
from ..dialogs.base import BaseBlockConfigDialog, FieldDef


def create_motor_config(
    block_id: str,
    label: str = "Motor",
    motor_id: int = 0,
) -> BlockConfig:
    """Create configuration for a DC motor block."""
    return BlockConfig(
        block_type="motor",
        block_id=block_id,
        label=label,
        width=100,
        height=80,
        input_ports=[
            PortConfig(
                port_id="PWM",
                label="PWM",
                kind=PortKind.INPUT,
                port_type=PortType.PWM,
                position_ratio=0.25,
            ),
            PortConfig(
                port_id="IN1",
                label="IN1",
                kind=PortKind.INPUT,
                port_type=PortType.GPIO,
                position_ratio=0.5,
            ),
            PortConfig(
                port_id="IN2",
                label="IN2",
                kind=PortKind.INPUT,
                port_type=PortType.GPIO,
                position_ratio=0.75,
            ),
        ],
        output_ports=[
            PortConfig(
                port_id="ENC",
                label="ENC",
                kind=PortKind.OUTPUT,
                port_type=PortType.ENCODER,
                position_ratio=0.5,
            ),
        ],
        properties={
            "motor_id": motor_id,
            "name": label,
            "max_rpm": 200,
            "gear_ratio": 1.0,
        },
    )


class MotorBlock(BlockBase):
    """
    DC Motor block with PWM and direction control inputs.

    Represents a DC motor with H-bridge driver, accepting:
    - PWM: Speed control signal
    - IN1/IN2: Direction control signals

    Optionally outputs encoder feedback.
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Motor",
        motor_id: int = 0,
    ):
        config = create_motor_config(block_id, label, motor_id)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        """Motors use red accent."""
        return QColor("#EF4444")

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint motor-specific content."""
        # Draw motor symbol (circle with M)
        center_x = rect.x() + rect.width() / 2
        center_y = rect.y() + rect.height() / 2 + 5
        radius = 18

        painter.setPen(QPen(QColor("#EF4444"), 2))
        painter.setBrush(QBrush(QColor("#2D1F1F")))
        painter.drawEllipse(int(center_x - radius), int(center_y - radius),
                           int(radius * 2), int(radius * 2))

        # M label
        font = QFont("Helvetica Neue", 12)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#EF4444")))
        painter.drawText(
            QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2),
            Qt.AlignCenter,
            "M",
        )

        # Motor ID
        if self.config.properties.get("motor_id") is not None:
            painter.setFont(QFont("Helvetica Neue", 8))
            painter.setPen(QPen(QColor("#71717A")))
            id_text = f"ID: {self.config.properties['motor_id']}"
            painter.drawText(
                QRectF(rect.x() + 12, rect.bottom() - 18, rect.width() - 24, 14),
                Qt.AlignCenter,
                id_text,
            )

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        """Get motor configuration dialog."""
        return MotorConfigDialog(self.config.properties, parent)


class MotorConfigDialog(BaseBlockConfigDialog):
    """Configuration dialog for DC motor."""

    dialog_title = "Motor Configuration"
    show_live_tune = False
    fields = [
        FieldDef("name", "Name", field_type="str", default="Motor"),
        FieldDef("motor_id", "Motor ID", field_type="int", default=0, min_val=0, max_val=7),
        FieldDef("max_rpm", "Max RPM", field_type="int", default=200, min_val=1, max_val=10000),
    ]
