# mara_host/gui/widgets/block_diagram/blocks/signal.py
"""Signal blocks for control loop diagrams."""

from typing import Optional

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
)

from ..core.block import BlockBase
from ..core.models import BlockConfig, PortConfig, PortKind, PortType


# --- Signal Source Block ---

def create_signal_source_config(
    block_id: str,
    label: str = "Ref",
    signal_id: int = 0,
) -> BlockConfig:
    """Create configuration for a signal source block."""
    return BlockConfig(
        block_type="signal_source",
        block_id=block_id,
        label=label,
        width=70,
        height=50,
        input_ports=[],
        output_ports=[
            PortConfig(
                port_id="out",
                label="out",
                kind=PortKind.OUTPUT,
                port_type=PortType.REF,
                position_ratio=0.5,
            ),
        ],
        properties={
            "signal_id": signal_id,
            "name": label,
            "kind": "reference",  # reference, setpoint, disturbance
            "initial_value": 0.0,
        },
    )


class SignalSourceBlock(BlockBase):
    """
    Signal source block.

    Represents a signal bus source (reference, setpoint, etc.).
    Outputs a single signal that can be connected to controller inputs.
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Ref",
        signal_id: int = 0,
    ):
        config = create_signal_source_config(block_id, label, signal_id)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        """Signal sources use blue accent."""
        return QColor("#3B82F6")

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint signal source content."""
        signal_id = self.config.properties.get("signal_id", 0)

        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QPen(QColor("#3B82F6")))

        id_rect = QRectF(rect.x() + 10, rect.bottom() - 18, rect.width() - 20, 14)
        painter.drawText(id_rect, Qt.AlignCenter, f"S{signal_id}")

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return SignalSourceConfigDialog(self.config.properties, parent)


class SignalSourceConfigDialog(QDialog):
    """Configuration dialog for signal source."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Signal Source Configuration")
        self.setMinimumWidth(280)

        layout = QVBoxLayout(self)

        group = QGroupBox("Signal Settings")
        form = QFormLayout(group)

        self.name_edit = QLineEdit(self._properties.get("name", "Ref"))
        form.addRow("Name:", self.name_edit)

        self.id_spin = QSpinBox()
        self.id_spin.setRange(0, 255)
        self.id_spin.setValue(self._properties.get("signal_id", 0))
        form.addRow("Signal ID:", self.id_spin)

        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["reference", "setpoint", "disturbance"])
        self.kind_combo.setCurrentText(self._properties.get("kind", "reference"))
        form.addRow("Kind:", self.kind_combo)

        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1000, 1000)
        self.value_spin.setDecimals(3)
        self.value_spin.setValue(self._properties.get("initial_value", 0.0))
        form.addRow("Initial Value:", self.value_spin)

        layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        return {
            "name": self.name_edit.text(),
            "signal_id": self.id_spin.value(),
            "kind": self.kind_combo.currentText(),
            "initial_value": self.value_spin.value(),
        }


# --- Signal Sink Block ---

def create_signal_sink_config(
    block_id: str,
    label: str = "Out",
    signal_id: int = 0,
) -> BlockConfig:
    """Create configuration for a signal sink block."""
    return BlockConfig(
        block_type="signal_sink",
        block_id=block_id,
        label=label,
        width=70,
        height=50,
        input_ports=[
            PortConfig(
                port_id="in",
                label="in",
                kind=PortKind.INPUT,
                port_type=PortType.OUT,
                position_ratio=0.5,
            ),
        ],
        output_ports=[],
        properties={
            "signal_id": signal_id,
            "name": label,
            "kind": "output",
        },
    )


class SignalSinkBlock(BlockBase):
    """
    Signal sink block.

    Represents a signal bus output (actuator command, etc.).
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Out",
        signal_id: int = 0,
    ):
        config = create_signal_sink_config(block_id, label, signal_id)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        """Signal sinks use orange accent."""
        return QColor("#F59E0B")

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        signal_id = self.config.properties.get("signal_id", 0)

        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QPen(QColor("#F59E0B")))

        id_rect = QRectF(rect.x() + 10, rect.bottom() - 18, rect.width() - 20, 14)
        painter.drawText(id_rect, Qt.AlignCenter, f"S{signal_id}")

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return SignalSourceConfigDialog(self.config.properties, parent)


# --- Sum Block ---

def create_sum_config(
    block_id: str,
    label: str = "Sum",
    n_inputs: int = 2,
    signs: Optional[list[str]] = None,
) -> BlockConfig:
    """Create configuration for a sum block."""
    if signs is None:
        signs = ["+"] * n_inputs

    input_ports = []
    for i in range(n_inputs):
        sign = signs[i] if i < len(signs) else "+"
        ratio = (i + 1) / (n_inputs + 1)
        input_ports.append(
            PortConfig(
                port_id=f"in{i}",
                label=sign,
                kind=PortKind.INPUT,
                port_type=PortType.SIGNAL,
                position_ratio=ratio,
            )
        )

    return BlockConfig(
        block_type="sum",
        block_id=block_id,
        label=label,
        width=50,
        height=50,
        input_ports=input_ports,
        output_ports=[
            PortConfig(
                port_id="out",
                label="out",
                kind=PortKind.OUTPUT,
                port_type=PortType.SIGNAL,
                position_ratio=0.5,
            ),
        ],
        properties={
            "n_inputs": n_inputs,
            "signs": signs,
        },
    )


class SumBlock(BlockBase):
    """
    Summing junction block.

    Adds (or subtracts) multiple input signals.
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Sum",
        n_inputs: int = 2,
        signs: Optional[list[str]] = None,
    ):
        config = create_sum_config(block_id, label, n_inputs, signs)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        return QColor("#71717A")

    def paint(self, painter: QPainter) -> None:
        """Paint sum block as a circle with + inside."""
        rect = self.rect

        # Draw circle
        center = QPointF(rect.x() + rect.width() / 2, rect.y() + rect.height() / 2)
        radius = min(rect.width(), rect.height()) / 2 - 2

        painter.setPen(QPen(self.get_border_color(), 2 if self._selected else 1))
        painter.setBrush(QBrush(self.get_background_color()))
        painter.drawEllipse(center, radius, radius)

        # Draw + symbol
        painter.setPen(QPen(QColor("#A1A1AA"), 2))
        cross_size = radius * 0.5
        painter.drawLine(
            int(center.x() - cross_size), int(center.y()),
            int(center.x() + cross_size), int(center.y()),
        )
        painter.drawLine(
            int(center.x()), int(center.y() - cross_size),
            int(center.x()), int(center.y() + cross_size),
        )

        # Draw ports
        for port in self.all_ports:
            port.paint(painter)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return None  # Simple block, no config


# --- Gain Block ---

def create_gain_config(
    block_id: str,
    label: str = "K",
    gain: float = 1.0,
) -> BlockConfig:
    """Create configuration for a gain block."""
    return BlockConfig(
        block_type="gain",
        block_id=block_id,
        label=label,
        width=60,
        height=50,
        input_ports=[
            PortConfig(
                port_id="in",
                label="in",
                kind=PortKind.INPUT,
                port_type=PortType.SIGNAL,
                position_ratio=0.5,
            ),
        ],
        output_ports=[
            PortConfig(
                port_id="out",
                label="out",
                kind=PortKind.OUTPUT,
                port_type=PortType.SIGNAL,
                position_ratio=0.5,
            ),
        ],
        properties={
            "gain": gain,
        },
    )


class GainBlock(BlockBase):
    """
    Scalar gain block.

    Multiplies input by a constant gain value.
    """

    def __init__(
        self,
        block_id: str,
        label: str = "K",
        gain: float = 1.0,
    ):
        config = create_gain_config(block_id, label, gain)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        return QColor("#8B5CF6")

    def paint(self, painter: QPainter) -> None:
        """Paint gain block as a triangle."""
        rect = self.rect

        # Draw triangle pointing right
        path = QPainterPath()
        margin = 5
        path.moveTo(rect.x() + margin, rect.y() + margin)
        path.lineTo(rect.right() - margin, rect.y() + rect.height() / 2)
        path.lineTo(rect.x() + margin, rect.bottom() - margin)
        path.closeSubpath()

        painter.setPen(QPen(self.get_border_color(), 2 if self._selected else 1))
        painter.setBrush(QBrush(self.get_background_color()))
        painter.drawPath(path)

        # Draw gain value
        gain = self.config.properties.get("gain", 1.0)
        painter.setFont(QFont("Consolas", 9))
        painter.setPen(QPen(QColor("#A1A1AA")))

        text_rect = QRectF(rect.x() + 8, rect.y(), rect.width() - 20, rect.height())
        painter.drawText(text_rect, Qt.AlignCenter, f"{gain:.2g}")

        # Draw ports
        for port in self.all_ports:
            port.paint(painter)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return GainConfigDialog(self.config.properties, parent)


class GainConfigDialog(QDialog):
    """Configuration dialog for gain block."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Gain Configuration")
        self.setMinimumWidth(200)

        layout = QVBoxLayout(self)

        group = QGroupBox("Gain")
        form = QFormLayout(group)

        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setRange(-10000, 10000)
        self.gain_spin.setDecimals(4)
        self.gain_spin.setValue(self._properties.get("gain", 1.0))
        form.addRow("K:", self.gain_spin)

        layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        return {"gain": self.gain_spin.value()}
