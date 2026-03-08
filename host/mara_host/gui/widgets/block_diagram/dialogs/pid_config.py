# mara_host/gui/widgets/block_diagram/dialogs/pid_config.py
"""PID controller configuration dialog."""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QDialogButtonBox,
    QGroupBox,
    QTabWidget,
    QWidget,
    QSlider,
    QFrame,
)

from .base import BaseBlockConfigDialog, FieldDef


class GainSlider(QFrame):
    """
    Combined slider and spinbox for gain adjustment.
    """

    value_changed = Signal(float)

    def __init__(
        self,
        min_val: float = -10.0,
        max_val: float = 10.0,
        initial: float = 0.0,
        decimals: int = 4,
        parent=None,
    ):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._decimals = decimals
        self._scale = 10 ** decimals

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(min_val * self._scale), int(max_val * self._scale))
        self.slider.setValue(int(initial * self._scale))
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider, 1)

        # Spinbox
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setDecimals(decimals)
        self.spinbox.setValue(initial)
        self.spinbox.setMinimumWidth(90)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)
        layout.addWidget(self.spinbox)

    def _on_slider_changed(self, value: int) -> None:
        float_val = value / self._scale
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(float_val)
        self.spinbox.blockSignals(False)
        self.value_changed.emit(float_val)

    def _on_spinbox_changed(self, value: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(int(value * self._scale))
        self.slider.blockSignals(False)
        self.value_changed.emit(value)

    def value(self) -> float:
        return self.spinbox.value()

    def setValue(self, value: float) -> None:
        self.spinbox.setValue(value)


class PIDConfigDialog(BaseBlockConfigDialog):
    """
    Configuration dialog for PID controller.

    Provides intuitive controls for PID gains with real-time
    slider feedback and advanced options.

    This dialog uses a custom layout with tabs and GainSliders
    rather than the declarative field definitions, but inherits
    common functionality from BaseBlockConfigDialog.

    Signals:
        live_update(int, dict): Emitted when Live Tune is enabled and a
                                parameter changes. Args: (slot, {param: value})
    """

    dialog_title = "PID Controller Configuration"
    show_live_tune = False  # We handle this manually with custom UI
    min_width = 400

    def __init__(
        self,
        properties: dict,
        parent: QWidget = None,
        controller: Any = None,
        slot: int = 0,
    ):
        """
        Initialize PID config dialog.

        Args:
            properties: Current block properties
            parent: Parent widget
            controller: RobotController for live tuning (optional)
            slot: Controller slot number
        """
        # Don't call super().__init__ since we override _setup_ui completely
        # but do basic QDialog init
        QWidget.__init__(self, parent)
        self._properties = properties.copy()
        self._controller = controller
        self._slot = slot
        self._live_tune = False
        self._widgets = {}
        self.setWindowTitle(self.dialog_title)
        self.setMinimumWidth(self.min_width)
        self._setup_ui_custom()

    def _setup_ui_custom(self) -> None:
        """Set up custom tabbed UI for PID dialog."""
        self.setMinimumHeight(450)

        layout = QVBoxLayout(self)

        # Tabs for basic/advanced
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Basic tab
        basic_widget = QWidget()
        basic_layout = QVBoxLayout(basic_widget)
        self._setup_basic_tab(basic_layout)
        tabs.addTab(basic_widget, "Gains")

        # Advanced tab
        advanced_widget = QWidget()
        advanced_layout = QVBoxLayout(advanced_widget)
        self._setup_advanced_tab(advanced_layout)
        tabs.addTab(advanced_widget, "Advanced")

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _setup_basic_tab(self, layout: QVBoxLayout) -> None:
        """Setup basic gains tab."""
        # Name and slot
        info_group = QGroupBox("Controller Info")
        info_form = QFormLayout(info_group)

        self.name_edit = QLineEdit(self._properties.get("name", "PID"))
        info_form.addRow("Name:", self.name_edit)

        self.slot_spin = QSpinBox()
        self.slot_spin.setRange(0, 7)
        self.slot_spin.setValue(self._properties.get("slot", 0))
        info_form.addRow("Slot:", self.slot_spin)

        layout.addWidget(info_group)

        # Live Tune toggle
        live_layout = QHBoxLayout()
        self.live_tune_check = QCheckBox("Live Tune")
        self.live_tune_check.setToolTip(
            "When enabled, gain changes are sent to the robot immediately.\n"
            "The robot must be connected and the controller slot configured."
        )
        self.live_tune_check.stateChanged.connect(self._on_live_tune_changed)
        live_layout.addWidget(self.live_tune_check)

        self.live_status = QLabel("")
        self.live_status.setStyleSheet("color: #71717A; font-size: 11px;")
        live_layout.addWidget(self.live_status)
        live_layout.addStretch()

        layout.addLayout(live_layout)

        # PID Gains
        gains_group = QGroupBox("PID Gains")
        gains_layout = QVBoxLayout(gains_group)

        # Kp
        kp_layout = QHBoxLayout()
        kp_label = QLabel("Kp (Proportional):")
        kp_label.setMinimumWidth(120)
        kp_layout.addWidget(kp_label)
        self.kp_slider = GainSlider(-100, 100, self._properties.get("kp", 1.0))
        self.kp_slider.value_changed.connect(lambda v: self._on_gain_changed("kp", v))
        kp_layout.addWidget(self.kp_slider)
        gains_layout.addLayout(kp_layout)

        # Ki
        ki_layout = QHBoxLayout()
        ki_label = QLabel("Ki (Integral):")
        ki_label.setMinimumWidth(120)
        ki_layout.addWidget(ki_label)
        self.ki_slider = GainSlider(-100, 100, self._properties.get("ki", 0.0))
        self.ki_slider.value_changed.connect(lambda v: self._on_gain_changed("ki", v))
        ki_layout.addWidget(self.ki_slider)
        gains_layout.addLayout(ki_layout)

        # Kd
        kd_layout = QHBoxLayout()
        kd_label = QLabel("Kd (Derivative):")
        kd_label.setMinimumWidth(120)
        kd_layout.addWidget(kd_label)
        self.kd_slider = GainSlider(-100, 100, self._properties.get("kd", 0.0))
        self.kd_slider.value_changed.connect(lambda v: self._on_gain_changed("kd", v))
        kd_layout.addWidget(self.kd_slider)
        gains_layout.addLayout(kd_layout)

        layout.addWidget(gains_group)

        # Formula hint
        hint = QLabel("u = Kp*e + Ki*∫e dt + Kd*(de/dt)")
        hint.setStyleSheet("color: #71717A; font-size: 11px; font-style: italic;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch()

    def _setup_advanced_tab(self, layout: QVBoxLayout) -> None:
        """Setup advanced options tab."""
        # Output limits
        limits_group = QGroupBox("Output Limits")
        limits_form = QFormLayout(limits_group)

        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-1000, 1000)
        self.min_spin.setDecimals(3)
        self.min_spin.setValue(self._properties.get("output_min", -1.0))
        limits_form.addRow("Min Output:", self.min_spin)

        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-1000, 1000)
        self.max_spin.setDecimals(3)
        self.max_spin.setValue(self._properties.get("output_max", 1.0))
        limits_form.addRow("Max Output:", self.max_spin)

        layout.addWidget(limits_group)

        # Anti-windup
        windup_group = QGroupBox("Integral Windup")
        windup_layout = QVBoxLayout(windup_group)

        self.anti_windup_check = QCheckBox("Enable anti-windup")
        self.anti_windup_check.setChecked(self._properties.get("anti_windup", True))
        windup_layout.addWidget(self.anti_windup_check)

        windup_hint = QLabel(
            "Anti-windup prevents integral term from accumulating\n"
            "when output is saturated at limits."
        )
        windup_hint.setStyleSheet("color: #71717A; font-size: 11px;")
        windup_layout.addWidget(windup_hint)

        layout.addWidget(windup_group)

        # Signal routing
        signal_group = QGroupBox("Signal Bus Routing")
        signal_form = QFormLayout(signal_group)

        self.ref_signal_spin = QSpinBox()
        self.ref_signal_spin.setRange(-1, 255)
        self.ref_signal_spin.setValue(self._properties.get("ref_signal_id", -1))
        self.ref_signal_spin.setSpecialValueText("None")
        signal_form.addRow("Reference Signal:", self.ref_signal_spin)

        self.meas_signal_spin = QSpinBox()
        self.meas_signal_spin.setRange(-1, 255)
        self.meas_signal_spin.setValue(self._properties.get("meas_signal_id", -1))
        self.meas_signal_spin.setSpecialValueText("None")
        signal_form.addRow("Measurement Signal:", self.meas_signal_spin)

        self.out_signal_spin = QSpinBox()
        self.out_signal_spin.setRange(-1, 255)
        self.out_signal_spin.setValue(self._properties.get("out_signal_id", -1))
        self.out_signal_spin.setSpecialValueText("None")
        signal_form.addRow("Output Signal:", self.out_signal_spin)

        layout.addWidget(signal_group)

        layout.addStretch()

    def _on_live_tune_changed(self, state: int) -> None:
        """Handle live tune checkbox change."""
        self._live_tune = state == Qt.Checked.value
        if self._live_tune:
            if self._controller and self._controller.is_connected:
                self.live_status.setText("Connected - changes sent immediately")
                self.live_status.setStyleSheet("color: #22C55E; font-size: 11px;")
            else:
                self.live_status.setText("Not connected - changes will be local only")
                self.live_status.setStyleSheet("color: #F59E0B; font-size: 11px;")
        else:
            self.live_status.setText("")

    def _on_gain_changed(self, param: str, value: float) -> None:
        """Handle gain slider change - send update if live tuning."""
        if not self._live_tune:
            return

        slot = self.slot_spin.value()

        # Emit signal for external handling
        self.live_update.emit(slot, {param: value})

        # Direct controller update if available
        if self._controller and getattr(self._controller, "is_connected", False):
            # Use single-param update for efficiency (hot-swap)
            self._controller.controller_set_param(slot, param, value)

    def set_controller(self, controller) -> None:
        """Set the robot controller for live tuning."""
        self._controller = controller
        # Update status if live tune is already enabled
        if self._live_tune:
            self._on_live_tune_changed(Qt.Checked.value)

    def get_config(self) -> dict:
        """Get configuration from dialog."""
        return {
            "name": self.name_edit.text(),
            "slot": self.slot_spin.value(),
            "kp": self.kp_slider.value(),
            "ki": self.ki_slider.value(),
            "kd": self.kd_slider.value(),
            "output_min": self.min_spin.value(),
            "output_max": self.max_spin.value(),
            "anti_windup": self.anti_windup_check.isChecked(),
            "ref_signal_id": self.ref_signal_spin.value() if self.ref_signal_spin.value() >= 0 else None,
            "meas_signal_id": self.meas_signal_spin.value() if self.meas_signal_spin.value() >= 0 else None,
            "out_signal_id": self.out_signal_spin.value() if self.out_signal_spin.value() >= 0 else None,
        }
