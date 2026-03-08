# mara_host/gui/widgets/block_diagram/blocks/encoder.py
"""Quadrature encoder block."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import QDialog, QWidget

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType
from ..dialogs.base import BaseBlockConfigDialog, FieldDef


def create_encoder_config(
    block_id: str,
    label: str = "Encoder",
    encoder_id: int = 0,
) -> BlockConfig:
    """Create configuration for an encoder block."""
    return BlockConfig(
        block_type="encoder",
        block_id=block_id,
        label=label,
        width=90,
        height=70,
        input_ports=[],  # Encoder has no inputs (it's a source)
        output_ports=[
            PortConfig(
                port_id="A",
                label="A",
                kind=PortKind.OUTPUT,
                port_type=PortType.ENCODER,
                position_ratio=0.33,
            ),
            PortConfig(
                port_id="B",
                label="B",
                kind=PortKind.OUTPUT,
                port_type=PortType.ENCODER,
                position_ratio=0.67,
            ),
        ],
        properties={
            "encoder_id": encoder_id,
            "name": label,
            "ppr": 11,  # Pulses per revolution
            "quadrature": True,
        },
    )


class EncoderBlock(BlockBase):
    """
    Quadrature encoder block.

    Outputs A and B channel signals for position/velocity measurement.
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Encoder",
        encoder_id: int = 0,
    ):
        config = create_encoder_config(block_id, label, encoder_id)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        """Encoders use purple accent."""
        return QColor("#8B5CF6")

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint encoder-specific content."""
        # Draw encoder wheel symbol
        center_x = rect.x() + rect.width() / 2
        center_y = rect.y() + rect.height() / 2 + 5
        radius = 15

        # Outer circle
        painter.setPen(QPen(QColor("#8B5CF6"), 2))
        painter.setBrush(QBrush(QColor("#1F1F2D")))
        painter.drawEllipse(int(center_x - radius), int(center_y - radius),
                           int(radius * 2), int(radius * 2))

        # Encoder slots (simplified)
        painter.setPen(QPen(QColor("#8B5CF6"), 1))
        slot_count = 8
        import math
        for i in range(slot_count):
            angle = (2 * math.pi * i) / slot_count
            inner_r = radius * 0.5
            outer_r = radius * 0.85
            x1 = center_x + inner_r * math.cos(angle)
            y1 = center_y + inner_r * math.sin(angle)
            x2 = center_x + outer_r * math.cos(angle)
            y2 = center_y + outer_r * math.sin(angle)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # PPR label
        ppr = self.config.properties.get("ppr", 11)
        painter.setFont(QFont("Helvetica Neue", 8))
        painter.setPen(QPen(QColor("#71717A")))
        painter.drawText(
            QRectF(rect.x() + 12, rect.bottom() - 16, rect.width() - 24, 12),
            Qt.AlignCenter,
            f"{ppr} PPR",
        )

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        """Get encoder configuration dialog."""
        return EncoderConfigDialog(self.config.properties, parent)


class EncoderConfigDialog(BaseBlockConfigDialog):
    """Configuration dialog for encoder."""

    dialog_title = "Encoder Configuration"
    show_live_tune = False
    min_width = 280
    fields = [
        FieldDef("name", "Name", field_type="str", default="Encoder"),
        FieldDef("encoder_id", "Encoder ID", field_type="int", default=0, min_val=0, max_val=7),
        FieldDef("ppr", "Pulses/Rev", field_type="int", default=11, min_val=1, max_val=10000),
    ]
