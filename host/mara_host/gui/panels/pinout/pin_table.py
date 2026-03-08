# mara_host/gui/panels/pinout/pin_table.py
"""Pin status table widget."""

from typing import Optional

from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


# Pin status colors
PIN_COLORS = {
    "assigned": "#22C55E",    # Green
    "free_safe": "#3B82F6",   # Blue
    "free_boot": "#EAB308",   # Yellow
    "free_input": "#A855F7",  # Purple
    "flash": "#EF4444",       # Red (unusable)
    "conflict": "#F97316",    # Orange
}


class PinTableWidget(QGroupBox):
    """
    Widget for displaying and filtering GPIO pins.

    Signals:
        pin_selected(int): Emitted when a pin is selected (GPIO number)
    """

    pin_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__("GPIO Pins", parent)
        self._pin_service = None
        self._setup_ui()

    def set_pin_service(self, pin_service) -> None:
        """Set the pin service instance."""
        self._pin_service = pin_service

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Filter bar
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Show:"))

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Pins",
            "Assigned Only",
            "Free (Safe)",
            "Free (All)",
            "Conflicts",
        ])
        self.filter_combo.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.filter_combo)

        filter_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.setMinimumWidth(80)
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)

        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "GPIO", "Name", "Status", "Capabilities", "Notes"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

    def refresh(self) -> None:
        """Refresh the pin table."""
        if not self._pin_service:
            return

        self.table.setRowCount(0)

        try:
            all_pins = self._pin_service.get_all_pins()
            assignments = self._pin_service.get_assignments()
            conflicts = self._pin_service.detect_conflicts()
            conflict_gpios = {c.gpio for c in conflicts}

            filter_mode = self.filter_combo.currentText()

            for gpio, pin_info in sorted(all_pins.items()):
                # Check assignment
                assigned_name = None
                for name, g in assignments.items():
                    if g == gpio:
                        assigned_name = name
                        break

                is_assigned = assigned_name is not None
                is_safe = self._pin_service.is_safe_pin(gpio)
                is_flash = self._pin_service.is_flash_pin(gpio)
                is_boot = self._pin_service.is_boot_pin(gpio)
                has_conflict = gpio in conflict_gpios

                # Apply filter
                if filter_mode == "Assigned Only" and not is_assigned:
                    continue
                if filter_mode == "Free (Safe)" and (is_assigned or not is_safe):
                    continue
                if filter_mode == "Free (All)" and is_assigned:
                    continue
                if filter_mode == "Conflicts" and not has_conflict:
                    continue

                self._add_row(
                    gpio, assigned_name, is_assigned, is_safe,
                    is_flash, is_boot, has_conflict, pin_info
                )

        except Exception:
            pass

    def _add_row(
        self,
        gpio: int,
        name: Optional[str],
        is_assigned: bool,
        is_safe: bool,
        is_flash: bool,
        is_boot: bool,
        has_conflict: bool,
        pin_info,
    ) -> None:
        """Add a row to the table."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # GPIO number
        gpio_item = QTableWidgetItem(str(gpio))
        gpio_item.setData(Qt.UserRole, gpio)
        gpio_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 0, gpio_item)

        # Name
        name_item = QTableWidgetItem(name or "")
        if name:
            name_item.setForeground(QColor(PIN_COLORS["assigned"]))
        self.table.setItem(row, 1, name_item)

        # Status
        if is_flash:
            status = "FLASH"
            color = PIN_COLORS["flash"]
        elif has_conflict:
            status = "CONFLICT"
            color = PIN_COLORS["conflict"]
        elif is_assigned:
            status = "Assigned"
            color = PIN_COLORS["assigned"]
        elif is_safe:
            status = "Free (Safe)"
            color = PIN_COLORS["free_safe"]
        elif is_boot:
            status = "Free (Boot)"
            color = PIN_COLORS["free_boot"]
        elif self._pin_service.is_input_only(gpio):
            status = "Free (Input)"
            color = PIN_COLORS["free_input"]
        else:
            status = "Free"
            color = "#707090"

        status_item = QTableWidgetItem(status)
        status_item.setForeground(QColor(color))
        self.table.setItem(row, 2, status_item)

        # Capabilities
        caps = self._pin_service.capability_string(gpio)
        caps_item = QTableWidgetItem(caps)
        caps_item.setForeground(QColor("#B0B0C0"))
        self.table.setItem(row, 3, caps_item)

        # Notes
        notes = getattr(pin_info, "notes", "") or getattr(pin_info, "warning", "")
        notes_item = QTableWidgetItem(notes)
        notes_item.setForeground(QColor("#707090"))
        self.table.setItem(row, 4, notes_item)

    def _on_selection_changed(self) -> None:
        """Handle selection change."""
        selected = self.table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        gpio_item = self.table.item(row, 0)
        if gpio_item:
            gpio = gpio_item.data(Qt.UserRole)
            self.pin_selected.emit(gpio)

    def get_selected_name(self) -> Optional[str]:
        """Get the name of the currently selected pin."""
        selected = self.table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        name_item = self.table.item(row, 1)
        return name_item.text() if name_item else None
