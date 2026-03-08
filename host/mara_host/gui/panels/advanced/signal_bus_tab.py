# mara_host/gui/panels/advanced/signal_bus_tab.py
"""Signal bus management tab for Advanced panel."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
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
    QDialog,
    QDialogButtonBox,
)

from mara_host.gui.core import GuiSignals, RobotController


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
