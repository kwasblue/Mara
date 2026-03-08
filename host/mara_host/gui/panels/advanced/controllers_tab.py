# mara_host/gui/panels/advanced/controllers_tab.py
"""Controllers management tab for Advanced panel."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QFrame,
    QDialog,
    QDialogButtonBox,
    QCheckBox,
    QScrollArea,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController


class ControllerSlotWidget(QFrame):
    """Widget for a single controller slot."""

    def __init__(
        self,
        slot: int,
        controller: RobotController,
        parent=None,
    ):
        super().__init__(parent)
        self.slot = slot
        self.robot_controller = controller
        self._configured = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("QFrame { background-color: #1A1A1C; border-radius: 8px; padding: 12px; }")

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        self.title_label = QLabel(f"Slot {self.slot}: [Unconfigured]")
        self.title_label.setStyleSheet("font-weight: bold; color: #FAFAFA;")
        header.addWidget(self.title_label)

        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.stateChanged.connect(self._on_enable_changed)
        header.addWidget(self.enabled_check)
        header.addStretch()
        layout.addLayout(header)

        # Info labels (hidden when unconfigured)
        self.info_frame = QFrame()
        info_layout = QGridLayout(self.info_frame)
        info_layout.setSpacing(4)

        info_layout.addWidget(QLabel("Type:"), 0, 0)
        self.type_label = QLabel("--")
        self.type_label.setStyleSheet("color: #71717A;")
        info_layout.addWidget(self.type_label, 0, 1)

        info_layout.addWidget(QLabel("Rate:"), 0, 2)
        self.rate_label = QLabel("-- Hz")
        self.rate_label.setStyleSheet("color: #71717A;")
        info_layout.addWidget(self.rate_label, 0, 3)

        info_layout.addWidget(QLabel("Signals:"), 1, 0)
        self.signals_label = QLabel("ref=?, meas=?, out=?")
        self.signals_label.setStyleSheet("color: #71717A;")
        info_layout.addWidget(self.signals_label, 1, 1, 1, 3)

        info_layout.addWidget(QLabel("Gains:"), 2, 0)
        self.gains_label = QLabel("--")
        self.gains_label.setStyleSheet("color: #71717A;")
        info_layout.addWidget(self.gains_label, 2, 1, 1, 3)

        self.info_frame.setVisible(False)
        layout.addWidget(self.info_frame)

        # Buttons
        btn_row = QHBoxLayout()
        self.configure_btn = QPushButton("Configure")
        self.configure_btn.setObjectName("secondary")
        self.configure_btn.clicked.connect(self._configure)
        btn_row.addWidget(self.configure_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("secondary")
        self.reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(self.reset_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_enable_changed(self, state: int) -> None:
        enable = state == Qt.CheckState.Checked.value
        self.robot_controller.controller_enable(self.slot, enable)

    def _configure(self) -> None:
        """Show configuration dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Configure Controller Slot {self.slot}")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Controller type
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type:"))
        type_combo = QComboBox()
        type_combo.addItems(["PID", "State-Space"])
        type_row.addWidget(type_combo)
        type_row.addStretch()
        layout.addLayout(type_row)

        # Rate
        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("Rate:"))
        rate_spin = QSpinBox()
        rate_spin.setRange(1, 1000)
        rate_spin.setValue(100)
        rate_spin.setSuffix(" Hz")
        rate_row.addWidget(rate_spin)
        rate_row.addStretch()
        layout.addLayout(rate_row)

        # Signal IDs
        signals_group = QGroupBox("Signal Routing")
        signals_layout = QGridLayout(signals_group)

        signals_layout.addWidget(QLabel("Reference signal ID:"), 0, 0)
        ref_spin = QSpinBox()
        ref_spin.setRange(0, 255)
        signals_layout.addWidget(ref_spin, 0, 1)

        signals_layout.addWidget(QLabel("Measurement signal ID:"), 1, 0)
        meas_spin = QSpinBox()
        meas_spin.setRange(0, 255)
        meas_spin.setValue(1)
        signals_layout.addWidget(meas_spin, 1, 1)

        signals_layout.addWidget(QLabel("Output signal ID:"), 2, 0)
        out_spin = QSpinBox()
        out_spin.setRange(0, 255)
        out_spin.setValue(2)
        signals_layout.addWidget(out_spin, 2, 1)

        layout.addWidget(signals_group)

        # PID gains (shown for PID type)
        pid_group = QGroupBox("PID Gains")
        pid_layout = QGridLayout(pid_group)

        pid_layout.addWidget(QLabel("Kp:"), 0, 0)
        kp_spin = QDoubleSpinBox()
        kp_spin.setRange(0, 1000)
        kp_spin.setValue(1.0)
        kp_spin.setDecimals(4)
        pid_layout.addWidget(kp_spin, 0, 1)

        pid_layout.addWidget(QLabel("Ki:"), 0, 2)
        ki_spin = QDoubleSpinBox()
        ki_spin.setRange(0, 1000)
        ki_spin.setValue(0.0)
        ki_spin.setDecimals(4)
        pid_layout.addWidget(ki_spin, 0, 3)

        pid_layout.addWidget(QLabel("Kd:"), 1, 0)
        kd_spin = QDoubleSpinBox()
        kd_spin.setRange(0, 1000)
        kd_spin.setValue(0.0)
        kd_spin.setDecimals(4)
        pid_layout.addWidget(kd_spin, 1, 1)

        pid_layout.addWidget(QLabel("Output limit:"), 1, 2)
        limit_spin = QDoubleSpinBox()
        limit_spin.setRange(0, 1000)
        limit_spin.setValue(1.0)
        pid_layout.addWidget(limit_spin, 1, 3)

        layout.addWidget(pid_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            ctrl_type = type_combo.currentText()
            rate = rate_spin.value()

            config = {
                "type": ctrl_type.lower().replace("-", "_"),
                "rate_hz": rate,
                "ref_signal_id": ref_spin.value(),
                "meas_signal_id": meas_spin.value(),
                "out_signal_id": out_spin.value(),
                "kp": kp_spin.value(),
                "ki": ki_spin.value(),
                "kd": kd_spin.value(),
                "out_limit": limit_spin.value(),
            }

            self.robot_controller.controller_config(self.slot, config)
            self._update_display(config)

    def _update_display(self, config: dict) -> None:
        """Update display with config."""
        self._configured = True
        ctrl_type = config.get("type", "pid").upper().replace("_", "-")
        self.title_label.setText(f"Slot {self.slot}: {ctrl_type} Controller")
        self.type_label.setText(ctrl_type)
        self.rate_label.setText(f"{config.get('rate_hz', 100)} Hz")

        ref_id = config.get("ref_signal_id", 0)
        meas_id = config.get("meas_signal_id", 1)
        out_id = config.get("out_signal_id", 2)
        self.signals_label.setText(f"ref={ref_id}, meas={meas_id}, out={out_id}")

        kp = config.get("kp", 0)
        ki = config.get("ki", 0)
        kd = config.get("kd", 0)
        self.gains_label.setText(f"Kp={kp}, Ki={ki}, Kd={kd}")

        self.info_frame.setVisible(True)

    def _reset(self) -> None:
        """Reset slot."""
        self.robot_controller.controller_reset(self.slot)
        self._configured = False
        self.title_label.setText(f"Slot {self.slot}: [Unconfigured]")
        self.info_frame.setVisible(False)
        self.enabled_check.setChecked(False)


class ControllersTab(QWidget):
    """Controllers management tab."""

    NUM_SLOTS = 8

    def __init__(
        self,
        signals: GuiSignals,
        controller: RobotController,
        parent=None,
    ):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Info
        info_label = QLabel(f"Control Slots ({self.NUM_SLOTS} available)")
        info_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #FAFAFA;")
        layout.addWidget(info_label)

        # Scroll area for slots
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)

        self.slot_widgets = []
        for i in range(self.NUM_SLOTS):
            slot_widget = ControllerSlotWidget(i, self.controller)
            self.slot_widgets.append(slot_widget)
            scroll_layout.addWidget(slot_widget)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
