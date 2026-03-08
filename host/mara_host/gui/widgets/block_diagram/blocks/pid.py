# mara_host/gui/widgets/block_diagram/blocks/pid.py
"""PID controller block."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QDoubleSpinBox,
    QSpinBox,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
    QCheckBox,
)

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType


def create_pid_config(
    block_id: str,
    label: str = "PID",
    slot: int = 0,
    kp: float = 1.0,
    ki: float = 0.0,
    kd: float = 0.0,
) -> BlockConfig:
    """Create configuration for a PID controller block."""
    return BlockConfig(
        block_type="pid",
        block_id=block_id,
        label=label,
        width=100,
        height=80,
        input_ports=[
            PortConfig(
                port_id="ref",
                label="ref",
                kind=PortKind.INPUT,
                port_type=PortType.REF,
                position_ratio=0.33,
            ),
            PortConfig(
                port_id="meas",
                label="meas",
                kind=PortKind.INPUT,
                port_type=PortType.MEAS,
                position_ratio=0.67,
            ),
        ],
        output_ports=[
            PortConfig(
                port_id="out",
                label="out",
                kind=PortKind.OUTPUT,
                port_type=PortType.OUT,
                position_ratio=0.5,
            ),
        ],
        properties={
            "slot": slot,
            "name": label,
            "kp": kp,
            "ki": ki,
            "kd": kd,
            "output_min": -1.0,
            "output_max": 1.0,
            "anti_windup": True,
            "enabled": False,
        },
    )


class PIDBlock(BlockBase):
    """
    PID Controller block.

    Implements standard PID control with configurable gains:
    - ref: Reference/setpoint input
    - meas: Measurement/feedback input
    - out: Control output

    Properties include Kp, Ki, Kd gains, output limits, and anti-windup.
    """

    def __init__(
        self,
        block_id: str,
        label: str = "PID",
        slot: int = 0,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
    ):
        config = create_pid_config(block_id, label, slot, kp, ki, kd)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        """PID controllers use blue accent."""
        return QColor("#3B82F6")

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint PID-specific content."""
        props = self.config.properties

        # Draw PID equation representation
        kp = props.get("kp", 1.0)
        ki = props.get("ki", 0.0)
        kd = props.get("kd", 0.0)

        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QPen(QColor("#A1A1AA")))

        # Format gains
        gains_text = f"P:{kp:.2f}"
        if ki != 0:
            gains_text += f" I:{ki:.2f}"
        if kd != 0:
            gains_text += f" D:{kd:.2f}"

        text_rect = QRectF(rect.x() + 12, rect.y() + 35, rect.width() - 24, 14)
        painter.drawText(text_rect, Qt.AlignCenter, gains_text)

        # Draw slot indicator
        slot = props.get("slot", 0)
        enabled = props.get("enabled", False)

        status_y = rect.bottom() - 18
        status_rect = QRectF(rect.x() + 12, status_y, rect.width() - 24, 14)

        if enabled:
            painter.setPen(QPen(QColor("#22C55E")))
            status_text = f"Slot {slot} [ON]"
        else:
            painter.setPen(QPen(QColor("#71717A")))
            status_text = f"Slot {slot}"

        painter.drawText(status_rect, Qt.AlignCenter, status_text)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        """Get PID configuration dialog."""
        from ..dialogs.pid_config import PIDConfigDialog
        return PIDConfigDialog(self.config.properties, parent)


# Inline dialog for simpler cases (the full dialog is in dialogs/pid_config.py)
class PIDSimpleConfigDialog(QDialog):
    """Simple configuration dialog for PID."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("PID Configuration")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        # Basic settings
        basic_group = QGroupBox("Controller Settings")
        form = QFormLayout(basic_group)

        self.name_edit = QLineEdit(self._properties.get("name", "PID"))
        form.addRow("Name:", self.name_edit)

        self.slot_spin = QSpinBox()
        self.slot_spin.setRange(0, 7)
        self.slot_spin.setValue(self._properties.get("slot", 0))
        form.addRow("Slot:", self.slot_spin)

        layout.addWidget(basic_group)

        # Gains
        gains_group = QGroupBox("PID Gains")
        gains_form = QFormLayout(gains_group)

        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(-1000, 1000)
        self.kp_spin.setDecimals(4)
        self.kp_spin.setValue(self._properties.get("kp", 1.0))
        gains_form.addRow("Kp:", self.kp_spin)

        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(-1000, 1000)
        self.ki_spin.setDecimals(4)
        self.ki_spin.setValue(self._properties.get("ki", 0.0))
        gains_form.addRow("Ki:", self.ki_spin)

        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(-1000, 1000)
        self.kd_spin.setDecimals(4)
        self.kd_spin.setValue(self._properties.get("kd", 0.0))
        gains_form.addRow("Kd:", self.kd_spin)

        layout.addWidget(gains_group)

        # Output limits
        limits_group = QGroupBox("Output Limits")
        limits_form = QFormLayout(limits_group)

        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-1000, 1000)
        self.min_spin.setDecimals(2)
        self.min_spin.setValue(self._properties.get("output_min", -1.0))
        limits_form.addRow("Min:", self.min_spin)

        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-1000, 1000)
        self.max_spin.setDecimals(2)
        self.max_spin.setValue(self._properties.get("output_max", 1.0))
        limits_form.addRow("Max:", self.max_spin)

        self.anti_windup_check = QCheckBox("Anti-windup")
        self.anti_windup_check.setChecked(self._properties.get("anti_windup", True))
        limits_form.addRow("", self.anti_windup_check)

        layout.addWidget(limits_group)

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
            "slot": self.slot_spin.value(),
            "kp": self.kp_spin.value(),
            "ki": self.ki_spin.value(),
            "kd": self.kd_spin.value(),
            "output_min": self.min_spin.value(),
            "output_max": self.max_spin.value(),
            "anti_windup": self.anti_windup_check.isChecked(),
        }
