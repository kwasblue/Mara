# mara_host/gui/panels/advanced/observers_tab.py
"""Observers management tab for Advanced panel."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QLineEdit,
    QComboBox,
    QFrame,
    QDialog,
    QDialogButtonBox,
    QTextEdit,
    QCheckBox,
    QScrollArea,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController


class ObserverSlotWidget(QFrame):
    """Widget for a single observer slot."""

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

        # Info labels
        self.info_frame = QFrame()
        info_layout = QGridLayout(self.info_frame)
        info_layout.setSpacing(4)

        info_layout.addWidget(QLabel("States:"), 0, 0)
        self.states_label = QLabel("--")
        self.states_label.setStyleSheet("color: #71717A;")
        info_layout.addWidget(self.states_label, 0, 1)

        info_layout.addWidget(QLabel("Inputs:"), 0, 2)
        self.inputs_label = QLabel("--")
        self.inputs_label.setStyleSheet("color: #71717A;")
        info_layout.addWidget(self.inputs_label, 0, 3)

        info_layout.addWidget(QLabel("Outputs:"), 0, 4)
        self.outputs_label = QLabel("--")
        self.outputs_label.setStyleSheet("color: #71717A;")
        info_layout.addWidget(self.outputs_label, 0, 5)

        info_layout.addWidget(QLabel("Rate:"), 1, 0)
        self.rate_label = QLabel("-- Hz")
        self.rate_label.setStyleSheet("color: #71717A;")
        info_layout.addWidget(self.rate_label, 1, 1)

        self.info_frame.setVisible(False)
        layout.addWidget(self.info_frame)

        # Buttons
        btn_row = QHBoxLayout()
        self.configure_btn = QPushButton("Configure")
        self.configure_btn.setObjectName("secondary")
        self.configure_btn.clicked.connect(self._configure)
        btn_row.addWidget(self.configure_btn)

        self.matrices_btn = QPushButton("Set Matrices")
        self.matrices_btn.setObjectName("secondary")
        self.matrices_btn.clicked.connect(self._set_matrices)
        btn_row.addWidget(self.matrices_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("secondary")
        self.reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(self.reset_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_enable_changed(self, state: int) -> None:
        enable = state == Qt.CheckState.Checked.value
        self.robot_controller.observer_enable(self.slot, enable)

    def _configure(self) -> None:
        """Show configuration dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Configure Observer Slot {self.slot}")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Dimensions
        dim_group = QGroupBox("Dimensions")
        dim_layout = QGridLayout(dim_group)

        dim_layout.addWidget(QLabel("States:"), 0, 0)
        states_spin = QSpinBox()
        states_spin.setRange(1, 16)
        states_spin.setValue(2)
        dim_layout.addWidget(states_spin, 0, 1)

        dim_layout.addWidget(QLabel("Inputs:"), 0, 2)
        inputs_spin = QSpinBox()
        inputs_spin.setRange(1, 8)
        inputs_spin.setValue(1)
        dim_layout.addWidget(inputs_spin, 0, 3)

        dim_layout.addWidget(QLabel("Outputs:"), 1, 0)
        outputs_spin = QSpinBox()
        outputs_spin.setRange(1, 8)
        outputs_spin.setValue(1)
        dim_layout.addWidget(outputs_spin, 1, 1)

        layout.addWidget(dim_group)

        # Rate
        rate_row = QHBoxLayout()
        rate_row.addWidget(QLabel("Rate:"))
        rate_spin = QSpinBox()
        rate_spin.setRange(1, 1000)
        rate_spin.setValue(200)
        rate_spin.setSuffix(" Hz")
        rate_row.addWidget(rate_spin)
        rate_row.addStretch()
        layout.addLayout(rate_row)

        # Signal IDs
        signals_group = QGroupBox("Signal Routing")
        signals_layout = QVBoxLayout(signals_group)

        signals_layout.addWidget(QLabel("Input signal IDs (comma-separated):"))
        input_signals_edit = QLineEdit("0")
        signals_layout.addWidget(input_signals_edit)

        signals_layout.addWidget(QLabel("Output signal IDs (comma-separated):"))
        output_signals_edit = QLineEdit("1")
        signals_layout.addWidget(output_signals_edit)

        signals_layout.addWidget(QLabel("Estimate signal IDs (comma-separated):"))
        estimate_signals_edit = QLineEdit("2, 3")
        signals_layout.addWidget(estimate_signals_edit)

        layout.addWidget(signals_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = {
                "n_states": states_spin.value(),
                "n_inputs": inputs_spin.value(),
                "n_outputs": outputs_spin.value(),
                "rate_hz": rate_spin.value(),
                "input_signals": input_signals_edit.text(),
                "output_signals": output_signals_edit.text(),
                "estimate_signals": estimate_signals_edit.text(),
            }

            self.robot_controller.observer_config(self.slot, config)
            self._update_display(config)

    def _update_display(self, config: dict) -> None:
        """Update display with config."""
        self._configured = True
        self.title_label.setText(f"Slot {self.slot}: Luenberger Observer")
        self.states_label.setText(str(config.get("n_states", 2)))
        self.inputs_label.setText(str(config.get("n_inputs", 1)))
        self.outputs_label.setText(str(config.get("n_outputs", 1)))
        self.rate_label.setText(f"{config.get('rate_hz', 200)} Hz")
        self.info_frame.setVisible(True)

    def _set_matrices(self) -> None:
        """Show matrix editor dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Observer {self.slot} Matrices")
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(dialog)

        # Matrix selector
        matrix_row = QHBoxLayout()
        matrix_row.addWidget(QLabel("Matrix:"))
        matrix_combo = QComboBox()
        matrix_combo.addItems(["A (System)", "B (Input)", "C (Output)", "L (Gain)"])
        matrix_row.addWidget(matrix_combo)
        matrix_row.addStretch()
        layout.addLayout(matrix_row)

        # Matrix input (as text)
        layout.addWidget(QLabel("Enter matrix values (row by row, space-separated):"))
        matrix_edit = QTextEdit()
        matrix_edit.setPlaceholderText("1.0 0.0\n0.0 1.0")
        matrix_edit.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "background-color: #27272A; color: #FAFAFA;"
        )
        layout.addWidget(matrix_edit, 1)

        # Buttons
        btn_row = QHBoxLayout()
        apply_btn = QPushButton("Apply Matrix")
        apply_btn.clicked.connect(lambda: self._apply_matrix(
            matrix_combo.currentText()[0],  # First char: A, B, C, or L
            matrix_edit.toPlainText()
        ))
        btn_row.addWidget(apply_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        dialog.exec()

    def _apply_matrix(self, matrix_key: str, text: str) -> None:
        """Parse and apply matrix."""
        try:
            values = []
            for line in text.strip().split("\n"):
                row_values = [float(x) for x in line.split()]
                values.extend(row_values)

            self.robot_controller.observer_set_param_array(self.slot, matrix_key, values)
        except ValueError:
            pass  # Could show error

    def _reset(self) -> None:
        """Reset slot."""
        self.robot_controller.observer_reset(self.slot)
        self._configured = False
        self.title_label.setText(f"Slot {self.slot}: [Unconfigured]")
        self.info_frame.setVisible(False)
        self.enabled_check.setChecked(False)


class ObserversTab(QWidget):
    """Observers management tab."""

    NUM_SLOTS = 4

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
        info_label = QLabel(f"Observer Slots ({self.NUM_SLOTS} available)")
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
            slot_widget = ObserverSlotWidget(i, self.controller)
            self.slot_widgets.append(slot_widget)
            scroll_layout.addWidget(slot_widget)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
