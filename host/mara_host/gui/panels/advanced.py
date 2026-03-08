# mara_host/gui/panels/advanced.py
"""
Advanced control panel for signal bus, controllers, and observers.

Provides UI for configuring and monitoring advanced control features:
- Signal Bus: Define, set, and monitor signals
- Controllers: Configure PID and state-space control slots
- Observers: Configure state observers (Luenberger, etc.)
"""

from typing import Optional
from dataclasses import dataclass

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
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QFrame,
    QDialog,
    QDialogButtonBox,
    QTextEdit,
    QCheckBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, QTimer

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings


class SignalBusTab(QWidget):
    """Signal bus management tab."""

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
        self._setup_connections()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Signals table
        table_group = QGroupBox("Signals")
        table_layout = QVBoxLayout(table_group)

        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(4)
        self.signals_table.setHorizontalHeaderLabels(["ID", "Name", "Kind", "Value"])

        header = self.signals_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.signals_table.setAlternatingRowColors(True)
        self.signals_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.signals_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self.signals_table)

        # Table buttons
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add Signal")
        self.add_btn.clicked.connect(self._add_signal)
        btn_row.addWidget(self.add_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("secondary")
        self.delete_btn.clicked.connect(self._delete_signal)
        btn_row.addWidget(self.delete_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setObjectName("secondary")
        self.clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(self.clear_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("secondary")
        self.refresh_btn.clicked.connect(self._refresh_signals)
        btn_row.addWidget(self.refresh_btn)

        btn_row.addStretch()
        table_layout.addLayout(btn_row)
        layout.addWidget(table_group, 1)

        # Set signal value
        set_group = QGroupBox("Set Signal Value")
        set_layout = QHBoxLayout(set_group)

        set_layout.addWidget(QLabel("ID:"))
        self.set_id_spin = QSpinBox()
        self.set_id_spin.setRange(0, 255)
        set_layout.addWidget(self.set_id_spin)

        set_layout.addWidget(QLabel("Value:"))
        self.set_value_spin = QDoubleSpinBox()
        self.set_value_spin.setRange(-1e9, 1e9)
        self.set_value_spin.setDecimals(6)
        set_layout.addWidget(self.set_value_spin)

        self.set_btn = QPushButton("Set")
        self.set_btn.clicked.connect(self._set_signal_value)
        set_layout.addWidget(self.set_btn)

        set_layout.addStretch()
        layout.addWidget(set_group)

    def _setup_connections(self) -> None:
        pass

    def _add_signal(self) -> None:
        """Show dialog to add a new signal."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Signal")
        dialog.setMinimumWidth(300)

        layout = QVBoxLayout(dialog)

        # ID
        id_row = QHBoxLayout()
        id_row.addWidget(QLabel("ID:"))
        id_spin = QSpinBox()
        id_spin.setRange(0, 255)
        id_row.addWidget(id_spin)
        layout.addLayout(id_row)

        # Name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        name_edit = QLineEdit()
        name_row.addWidget(name_edit)
        layout.addLayout(name_row)

        # Kind
        kind_row = QHBoxLayout()
        kind_row.addWidget(QLabel("Kind:"))
        kind_combo = QComboBox()
        kind_combo.addItems(["REF", "MEAS", "OUT", "STATE", "ERROR"])
        kind_row.addWidget(kind_combo)
        layout.addLayout(kind_row)

        # Initial value
        initial_row = QHBoxLayout()
        initial_row.addWidget(QLabel("Initial value:"))
        initial_spin = QDoubleSpinBox()
        initial_spin.setRange(-1e9, 1e9)
        initial_spin.setDecimals(6)
        initial_row.addWidget(initial_spin)
        layout.addLayout(initial_row)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            signal_id = id_spin.value()
            name = name_edit.text() or f"signal_{signal_id}"
            kind = kind_combo.currentText()
            initial = initial_spin.value()

            self.controller.signal_define(signal_id, name, kind, initial)
            self._add_signal_to_table(signal_id, name, kind, initial)

    def _add_signal_to_table(self, signal_id: int, name: str, kind: str, value: float) -> None:
        """Add a signal to the table."""
        row = self.signals_table.rowCount()
        self.signals_table.insertRow(row)
        self.signals_table.setItem(row, 0, QTableWidgetItem(str(signal_id)))
        self.signals_table.setItem(row, 1, QTableWidgetItem(name))
        self.signals_table.setItem(row, 2, QTableWidgetItem(kind))
        self.signals_table.setItem(row, 3, QTableWidgetItem(f"{value:.4f}"))

    def _delete_signal(self) -> None:
        """Delete selected signal."""
        row = self.signals_table.currentRow()
        if row >= 0:
            id_item = self.signals_table.item(row, 0)
            if id_item:
                signal_id = int(id_item.text())
                self.controller.signal_delete(signal_id)
                self.signals_table.removeRow(row)

    def _clear_all(self) -> None:
        """Clear all signals."""
        self.controller.signals_clear()
        self.signals_table.setRowCount(0)

    def _refresh_signals(self) -> None:
        """Refresh signals from device."""
        self.controller.signals_list()

    def _set_signal_value(self) -> None:
        """Set a signal value."""
        signal_id = self.set_id_spin.value()
        value = self.set_value_spin.value()
        self.controller.signal_set(signal_id, value)


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
        except ValueError as e:
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


class AdvancedPanel(QWidget):
    """
    Advanced control panel with tabs for signal bus, controllers, and observers.

    Layout:
        ┌─────────────────────────────────────────────────────┐
        │ [Signal Bus] [Controllers] [Observers]              │
        ├─────────────────────────────────────────────────────┤
        │                                                      │
        │  (tab content)                                       │
        │                                                      │
        └─────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        signals: GuiSignals,
        controller: RobotController,
        settings: GuiSettings,
    ):
        super().__init__()

        self.signals = signals
        self.controller = controller
        self.settings = settings

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """Set up the advanced panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget
        self.tabs = QTabWidget()

        # Signal Bus tab
        self.signal_bus_tab = SignalBusTab(self.signals, self.controller)
        self.tabs.addTab(self.signal_bus_tab, "Signal Bus")

        # Controllers tab
        self.controllers_tab = ControllersTab(self.signals, self.controller)
        self.tabs.addTab(self.controllers_tab, "Controllers")

        # Observers tab
        self.observers_tab = ObserversTab(self.signals, self.controller)
        self.tabs.addTab(self.observers_tab, "Observers")

        layout.addWidget(self.tabs)

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self.signals.connection_changed.connect(self._on_connection_changed)

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        """Handle connection state change."""
        # Could enable/disable widgets based on connection
        pass
