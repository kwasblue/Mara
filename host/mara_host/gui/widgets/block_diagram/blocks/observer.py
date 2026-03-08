# mara_host/gui/widgets/block_diagram/blocks/observer.py
"""Luenberger observer block."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QSpinBox,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
    QTextEdit,
    QLabel,
)

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType


def create_observer_config(
    block_id: str,
    label: str = "Observer",
    slot: int = 0,
    n_states: int = 2,
) -> BlockConfig:
    """Create configuration for an observer block."""
    return BlockConfig(
        block_type="observer",
        block_id=block_id,
        label=label,
        width=110,
        height=90,
        input_ports=[
            PortConfig(
                port_id="u",
                label="u",
                kind=PortKind.INPUT,
                port_type=PortType.OUT,
                position_ratio=0.33,
            ),
            PortConfig(
                port_id="y",
                label="y",
                kind=PortKind.INPUT,
                port_type=PortType.MEAS,
                position_ratio=0.67,
            ),
        ],
        output_ports=[
            PortConfig(
                port_id="x_hat",
                label="x_hat",
                kind=PortKind.OUTPUT,
                port_type=PortType.SIGNAL,
                position_ratio=0.5,
            ),
        ],
        properties={
            "slot": slot,
            "name": label,
            "n_states": n_states,
            "n_inputs": 1,
            "n_outputs": 1,
            # State-space matrices (flattened)
            "A": [0.0] * (n_states * n_states),
            "B": [0.0] * n_states,
            "C": [1.0] + [0.0] * (n_states - 1),
            "L": [0.5] * n_states,  # Observer gain
            "enabled": False,
        },
    )


class ObserverBlock(BlockBase):
    """
    Luenberger observer block.

    Estimates system state from inputs and outputs:
    - u: Control input
    - y: Measured output
    - x_hat: Estimated state vector

    Configured with state-space matrices A, B, C and observer gain L.
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Observer",
        slot: int = 0,
        n_states: int = 2,
    ):
        config = create_observer_config(block_id, label, slot, n_states)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        """Observers use green accent."""
        return QColor("#22C55E")

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint observer-specific content."""
        props = self.config.properties

        # Draw observer equation
        n_states = props.get("n_states", 2)

        painter.setFont(QFont("Consolas", 9))
        painter.setPen(QPen(QColor("#22C55E")))

        # x_hat dot equation symbol
        eq_rect = QRectF(rect.x() + 15, rect.y() + 35, rect.width() - 30, 20)
        painter.drawText(eq_rect, Qt.AlignCenter, "x = Ax + Bu + L(y-Cx)")

        # State dimension
        painter.setFont(QFont("Helvetica Neue", 8))
        painter.setPen(QPen(QColor("#71717A")))
        dim_rect = QRectF(rect.x() + 12, rect.y() + 52, rect.width() - 24, 14)
        painter.drawText(dim_rect, Qt.AlignCenter, f"n={n_states}")

        # Slot and status
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
        """Get observer configuration dialog."""
        return ObserverConfigDialog(self.config.properties, parent)


class ObserverConfigDialog(QDialog):
    """Configuration dialog for observer."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Observer Configuration")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)

        # Basic settings
        basic_group = QGroupBox("Observer Settings")
        form = QFormLayout(basic_group)

        self.name_edit = QLineEdit(self._properties.get("name", "Observer"))
        form.addRow("Name:", self.name_edit)

        self.slot_spin = QSpinBox()
        self.slot_spin.setRange(0, 7)
        self.slot_spin.setValue(self._properties.get("slot", 0))
        form.addRow("Slot:", self.slot_spin)

        self.n_states_spin = QSpinBox()
        self.n_states_spin.setRange(1, 10)
        self.n_states_spin.setValue(self._properties.get("n_states", 2))
        form.addRow("States:", self.n_states_spin)

        layout.addWidget(basic_group)

        # Matrix input (simplified - just L gain for now)
        gain_group = QGroupBox("Observer Gain L")
        gain_layout = QVBoxLayout(gain_group)

        gain_layout.addWidget(QLabel("Enter L values (comma-separated):"))

        self.l_edit = QLineEdit()
        l_values = self._properties.get("L", [0.5, 0.5])
        self.l_edit.setText(", ".join(f"{v:.4f}" for v in l_values))
        gain_layout.addWidget(self.l_edit)

        layout.addWidget(gain_group)

        # State-space matrices (advanced)
        matrices_group = QGroupBox("State-Space Matrices (Advanced)")
        matrices_layout = QVBoxLayout(matrices_group)

        matrices_layout.addWidget(QLabel("A matrix (row-major, comma-separated):"))
        self.a_edit = QTextEdit()
        a_values = self._properties.get("A", [])
        self.a_edit.setPlainText(", ".join(f"{v:.4f}" for v in a_values))
        self.a_edit.setMaximumHeight(60)
        matrices_layout.addWidget(self.a_edit)

        matrices_layout.addWidget(QLabel("B matrix (comma-separated):"))
        self.b_edit = QLineEdit()
        b_values = self._properties.get("B", [])
        self.b_edit.setText(", ".join(f"{v:.4f}" for v in b_values))
        matrices_layout.addWidget(self.b_edit)

        matrices_layout.addWidget(QLabel("C matrix (comma-separated):"))
        self.c_edit = QLineEdit()
        c_values = self._properties.get("C", [])
        self.c_edit.setText(", ".join(f"{v:.4f}" for v in c_values))
        matrices_layout.addWidget(self.c_edit)

        layout.addWidget(matrices_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _parse_values(self, text: str) -> list[float]:
        """Parse comma-separated values."""
        try:
            return [float(v.strip()) for v in text.split(",") if v.strip()]
        except ValueError:
            return []

    def get_config(self) -> dict:
        """Get configuration from dialog."""
        return {
            "name": self.name_edit.text(),
            "slot": self.slot_spin.value(),
            "n_states": self.n_states_spin.value(),
            "L": self._parse_values(self.l_edit.text()),
            "A": self._parse_values(self.a_edit.toPlainText()),
            "B": self._parse_values(self.b_edit.text()),
            "C": self._parse_values(self.c_edit.text()),
        }
