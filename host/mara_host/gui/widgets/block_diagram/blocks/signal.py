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


# --- Integrator Block ---

def create_integrator_config(
    block_id: str,
    label: str = "Int",
    gain: float = 1.0,
) -> BlockConfig:
    """Create configuration for an integrator block."""
    return BlockConfig(
        block_type="integrator",
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
            "initial_value": 0.0,
            "anti_windup": True,
            "limit_min": -1000.0,
            "limit_max": 1000.0,
        },
    )


class IntegratorBlock(BlockBase):
    """
    Integrator block (1/s).

    Integrates input signal over time: y = integral(K * u) dt
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Int",
        gain: float = 1.0,
    ):
        config = create_integrator_config(block_id, label, gain)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        return QColor("#14B8A6")  # Teal

    def paint(self, painter: QPainter) -> None:
        """Paint integrator block."""
        rect = self.rect

        painter.setPen(QPen(self.get_border_color(), 2 if self._selected else 1))
        painter.setBrush(QBrush(self.get_background_color()))
        painter.drawRoundedRect(rect, 4, 4)

        # Draw integrator symbol: 1/s
        painter.setFont(QFont("Times New Roman", 12))
        painter.setPen(QPen(QColor("#14B8A6")))
        painter.drawText(rect, Qt.AlignCenter, "1/s")

        # Draw ports
        for port in self.all_ports:
            port.paint(painter)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return IntegratorConfigDialog(self.config.properties, parent)


class IntegratorConfigDialog(QDialog):
    """Configuration dialog for integrator."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Integrator Configuration")
        self.setMinimumWidth(250)

        layout = QVBoxLayout(self)

        group = QGroupBox("Integrator Settings")
        form = QFormLayout(group)

        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setRange(-10000, 10000)
        self.gain_spin.setDecimals(4)
        self.gain_spin.setValue(self._properties.get("gain", 1.0))
        form.addRow("Gain:", self.gain_spin)

        self.initial_spin = QDoubleSpinBox()
        self.initial_spin.setRange(-10000, 10000)
        self.initial_spin.setDecimals(4)
        self.initial_spin.setValue(self._properties.get("initial_value", 0.0))
        form.addRow("Initial:", self.initial_spin)

        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-100000, 100000)
        self.min_spin.setValue(self._properties.get("limit_min", -1000.0))
        form.addRow("Min Limit:", self.min_spin)

        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-100000, 100000)
        self.max_spin.setValue(self._properties.get("limit_max", 1000.0))
        form.addRow("Max Limit:", self.max_spin)

        layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        return {
            "gain": self.gain_spin.value(),
            "initial_value": self.initial_spin.value(),
            "limit_min": self.min_spin.value(),
            "limit_max": self.max_spin.value(),
        }


# --- Derivative Block ---

def create_derivative_config(
    block_id: str,
    label: str = "Der",
    gain: float = 1.0,
    filter_coeff: float = 100.0,
) -> BlockConfig:
    """Create configuration for a derivative block."""
    return BlockConfig(
        block_type="derivative",
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
            "filter_coeff": filter_coeff,  # N in s*K/(1+s/N)
        },
    )


class DerivativeBlock(BlockBase):
    """
    Derivative block (s).

    Differentiates input with filtering: y = K*s/(1 + s/N) * u
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Der",
        gain: float = 1.0,
        filter_coeff: float = 100.0,
    ):
        config = create_derivative_config(block_id, label, gain, filter_coeff)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        return QColor("#EC4899")  # Pink

    def paint(self, painter: QPainter) -> None:
        """Paint derivative block."""
        rect = self.rect

        painter.setPen(QPen(self.get_border_color(), 2 if self._selected else 1))
        painter.setBrush(QBrush(self.get_background_color()))
        painter.drawRoundedRect(rect, 4, 4)

        # Draw derivative symbol: s
        painter.setFont(QFont("Times New Roman", 14, QFont.Bold))
        painter.setPen(QPen(QColor("#EC4899")))
        painter.drawText(rect, Qt.AlignCenter, "s")

        # Draw ports
        for port in self.all_ports:
            port.paint(painter)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return DerivativeConfigDialog(self.config.properties, parent)


class DerivativeConfigDialog(QDialog):
    """Configuration dialog for derivative."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Derivative Configuration")
        self.setMinimumWidth(250)

        layout = QVBoxLayout(self)

        group = QGroupBox("Derivative Settings")
        form = QFormLayout(group)

        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setRange(-10000, 10000)
        self.gain_spin.setDecimals(4)
        self.gain_spin.setValue(self._properties.get("gain", 1.0))
        form.addRow("Gain (K):", self.gain_spin)

        self.filter_spin = QDoubleSpinBox()
        self.filter_spin.setRange(1, 10000)
        self.filter_spin.setDecimals(1)
        self.filter_spin.setValue(self._properties.get("filter_coeff", 100.0))
        form.addRow("Filter (N):", self.filter_spin)

        layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        return {
            "gain": self.gain_spin.value(),
            "filter_coeff": self.filter_spin.value(),
        }


# --- Saturation Block ---

def create_saturation_config(
    block_id: str,
    label: str = "Sat",
    lower: float = -1.0,
    upper: float = 1.0,
) -> BlockConfig:
    """Create configuration for a saturation block."""
    return BlockConfig(
        block_type="saturation",
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
            "lower": lower,
            "upper": upper,
        },
    )


class SaturationBlock(BlockBase):
    """
    Saturation/Limiter block.

    Limits output to [lower, upper] range.
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Sat",
        lower: float = -1.0,
        upper: float = 1.0,
    ):
        config = create_saturation_config(block_id, label, lower, upper)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        return QColor("#EF4444")  # Red

    def paint(self, painter: QPainter) -> None:
        """Paint saturation block with characteristic."""
        rect = self.rect

        painter.setPen(QPen(self.get_border_color(), 2 if self._selected else 1))
        painter.setBrush(QBrush(self.get_background_color()))
        painter.drawRoundedRect(rect, 4, 4)

        # Draw saturation characteristic (S-curve with flat ends)
        painter.setPen(QPen(QColor("#EF4444"), 2))

        cx = rect.x() + rect.width() / 2
        cy = rect.y() + rect.height() / 2
        w = 20
        h = 12

        # Lower flat, slope, upper flat
        painter.drawLine(int(cx - w), int(cy + h), int(cx - w/2), int(cy + h))  # Lower flat
        painter.drawLine(int(cx - w/2), int(cy + h), int(cx + w/2), int(cy - h))  # Slope
        painter.drawLine(int(cx + w/2), int(cy - h), int(cx + w), int(cy - h))  # Upper flat

        # Draw ports
        for port in self.all_ports:
            port.paint(painter)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return SaturationConfigDialog(self.config.properties, parent)


class SaturationConfigDialog(QDialog):
    """Configuration dialog for saturation."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Saturation Configuration")
        self.setMinimumWidth(220)

        layout = QVBoxLayout(self)

        group = QGroupBox("Limits")
        form = QFormLayout(group)

        self.lower_spin = QDoubleSpinBox()
        self.lower_spin.setRange(-100000, 100000)
        self.lower_spin.setDecimals(3)
        self.lower_spin.setValue(self._properties.get("lower", -1.0))
        form.addRow("Lower:", self.lower_spin)

        self.upper_spin = QDoubleSpinBox()
        self.upper_spin.setRange(-100000, 100000)
        self.upper_spin.setDecimals(3)
        self.upper_spin.setValue(self._properties.get("upper", 1.0))
        form.addRow("Upper:", self.upper_spin)

        layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        return {
            "lower": self.lower_spin.value(),
            "upper": self.upper_spin.value(),
        }


# --- Low-Pass Filter Block ---

def create_filter_config(
    block_id: str,
    label: str = "LPF",
    cutoff_freq: float = 10.0,
) -> BlockConfig:
    """Create configuration for a low-pass filter block."""
    return BlockConfig(
        block_type="filter",
        block_id=block_id,
        label=label,
        width=70,
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
            "cutoff_freq": cutoff_freq,
            "filter_type": "lowpass",  # lowpass, highpass, bandpass
            "order": 1,
        },
    )


class FilterBlock(BlockBase):
    """
    Low-pass filter block.

    First-order low-pass: H(s) = wc / (s + wc)
    """

    def __init__(
        self,
        block_id: str,
        label: str = "LPF",
        cutoff_freq: float = 10.0,
    ):
        config = create_filter_config(block_id, label, cutoff_freq)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        return QColor("#A855F7")  # Purple

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint filter-specific content."""
        cutoff = self.config.properties.get("cutoff_freq", 10.0)

        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QPen(QColor("#A855F7")))

        text_rect = QRectF(rect.x() + 8, rect.bottom() - 18, rect.width() - 16, 14)
        painter.drawText(text_rect, Qt.AlignCenter, f"fc={cutoff:.1f}Hz")

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return FilterConfigDialog(self.config.properties, parent)


class FilterConfigDialog(QDialog):
    """Configuration dialog for filter."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Filter Configuration")
        self.setMinimumWidth(250)

        layout = QVBoxLayout(self)

        group = QGroupBox("Filter Settings")
        form = QFormLayout(group)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["lowpass", "highpass"])
        self.type_combo.setCurrentText(self._properties.get("filter_type", "lowpass"))
        form.addRow("Type:", self.type_combo)

        self.cutoff_spin = QDoubleSpinBox()
        self.cutoff_spin.setRange(0.001, 10000)
        self.cutoff_spin.setDecimals(3)
        self.cutoff_spin.setValue(self._properties.get("cutoff_freq", 10.0))
        self.cutoff_spin.setSuffix(" Hz")
        form.addRow("Cutoff:", self.cutoff_spin)

        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 4)
        self.order_spin.setValue(self._properties.get("order", 1))
        form.addRow("Order:", self.order_spin)

        layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        return {
            "filter_type": self.type_combo.currentText(),
            "cutoff_freq": self.cutoff_spin.value(),
            "order": self.order_spin.value(),
        }


# --- Delay Block ---

def create_delay_config(
    block_id: str,
    label: str = "Delay",
    delay_time: float = 0.1,
) -> BlockConfig:
    """Create configuration for a delay block."""
    return BlockConfig(
        block_type="delay",
        block_id=block_id,
        label=label,
        width=70,
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
            "delay_time": delay_time,
        },
    )


class DelayBlock(BlockBase):
    """
    Time delay block.

    Delays input by specified time: y(t) = u(t - T)
    """

    def __init__(
        self,
        block_id: str,
        label: str = "Delay",
        delay_time: float = 0.1,
    ):
        config = create_delay_config(block_id, label, delay_time)
        super().__init__(config)

    def get_icon_color(self) -> QColor:
        return QColor("#F97316")  # Orange

    def paint_content(self, painter: QPainter, rect: QRectF) -> None:
        """Paint delay-specific content."""
        delay = self.config.properties.get("delay_time", 0.1)

        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QPen(QColor("#F97316")))

        text_rect = QRectF(rect.x() + 8, rect.bottom() - 18, rect.width() - 16, 14)
        if delay < 0.001:
            text = f"T={delay*1000000:.0f}us"
        elif delay < 1:
            text = f"T={delay*1000:.1f}ms"
        else:
            text = f"T={delay:.3f}s"
        painter.drawText(text_rect, Qt.AlignCenter, text)

    def get_config_dialog(self, parent: QWidget) -> Optional[QDialog]:
        return DelayConfigDialog(self.config.properties, parent)


class DelayConfigDialog(QDialog):
    """Configuration dialog for delay."""

    def __init__(self, properties: dict, parent=None):
        super().__init__(parent)
        self._properties = properties.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Delay Configuration")
        self.setMinimumWidth(220)

        layout = QVBoxLayout(self)

        group = QGroupBox("Delay Settings")
        form = QFormLayout(group)

        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0001, 100)
        self.delay_spin.setDecimals(4)
        self.delay_spin.setValue(self._properties.get("delay_time", 0.1))
        self.delay_spin.setSuffix(" s")
        form.addRow("Delay:", self.delay_spin)

        layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        return {
            "delay_time": self.delay_spin.value(),
        }
