# mara_host/gui/panels/pinout.py
"""
Pinout configuration panel for GPIO pin management.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QLineEdit,
    QHeaderView,
    QAbstractItemView,
    QSplitter,
    QTextEdit,
    QMessageBox,
    QFormLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings


class PinoutPanel(QWidget):
    """
    Pinout configuration panel.

    Features:
        - Visual pin status table
        - Add/remove pin assignments
        - Conflict detection and warnings
        - Pin recommendations by use case
        - Quick setup wizards
    """

    # Pin status colors
    COLORS = {
        "assigned": "#22C55E",    # Green
        "free_safe": "#3B82F6",   # Blue
        "free_boot": "#EAB308",   # Yellow
        "free_input": "#A855F7",  # Purple
        "flash": "#EF4444",       # Red (unusable)
        "conflict": "#F97316",    # Orange
    }

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

        self._pin_service = None
        self._setup_ui()
        self._load_pin_service()

    def _setup_ui(self) -> None:
        """Set up the pinout panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left side - Pin table and assignments
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Pin table
        left_layout.addWidget(self._create_pin_table(), 1)

        # Assignment controls
        left_layout.addWidget(self._create_assignment_controls())

        splitter.addWidget(left_widget)

        # Right side - Info and wizards
        right_widget = QWidget()
        right_widget.setMaximumWidth(350)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Pin info
        right_layout.addWidget(self._create_pin_info())

        # Conflicts
        right_layout.addWidget(self._create_conflicts_panel())

        # Wizards
        right_layout.addWidget(self._create_wizard_panel())

        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([600, 350])

        layout.addWidget(splitter)

    def _create_pin_table(self) -> QGroupBox:
        """Create the pin status table."""
        group = QGroupBox("GPIO Pins")
        layout = QVBoxLayout(group)

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
        self.filter_combo.currentIndexChanged.connect(self._refresh_table)
        filter_layout.addWidget(self.filter_combo)

        filter_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.setMinimumWidth(80)
        refresh_btn.clicked.connect(self._refresh_table)
        filter_layout.addWidget(refresh_btn)

        layout.addLayout(filter_layout)

        # Table
        self.pin_table = QTableWidget()
        self.pin_table.setColumnCount(5)
        self.pin_table.setHorizontalHeaderLabels([
            "GPIO", "Name", "Status", "Capabilities", "Notes"
        ])
        self.pin_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pin_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.pin_table.setColumnWidth(0, 50)
        self.pin_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pin_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.pin_table.itemSelectionChanged.connect(self._on_pin_selected)
        self.pin_table.setAlternatingRowColors(True)

        layout.addWidget(self.pin_table)

        return group

    def _create_assignment_controls(self) -> QGroupBox:
        """Create pin assignment controls."""
        group = QGroupBox("Pin Assignment")
        layout = QHBoxLayout(group)

        # Name input
        layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., MOTOR0_PWM")
        self.name_input.setMaximumWidth(200)
        layout.addWidget(self.name_input)

        # GPIO input
        layout.addWidget(QLabel("GPIO:"))
        self.gpio_input = QComboBox()
        self.gpio_input.setMaximumWidth(80)
        layout.addWidget(self.gpio_input)

        # Buttons
        assign_btn = QPushButton("Assign")
        assign_btn.setMinimumWidth(80)
        assign_btn.clicked.connect(self._assign_pin)
        layout.addWidget(assign_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("secondary")
        remove_btn.setMinimumWidth(85)
        remove_btn.clicked.connect(self._remove_pin)
        layout.addWidget(remove_btn)

        layout.addStretch()

        # Save button
        save_btn = QPushButton("Save to Config")
        save_btn.setMinimumWidth(120)
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn)

        return group

    def _create_pin_info(self) -> QGroupBox:
        """Create pin info panel."""
        group = QGroupBox("Pin Details")
        layout = QFormLayout(group)

        self.info_gpio = QLabel("--")
        self.info_gpio.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addRow("GPIO:", self.info_gpio)

        self.info_name = QLabel("--")
        layout.addRow("Name:", self.info_name)

        self.info_caps = QLabel("--")
        self.info_caps.setWordWrap(True)
        layout.addRow("Capabilities:", self.info_caps)

        self.info_adc = QLabel("--")
        layout.addRow("ADC:", self.info_adc)

        self.info_touch = QLabel("--")
        layout.addRow("Touch:", self.info_touch)

        self.info_notes = QLabel("--")
        self.info_notes.setWordWrap(True)
        self.info_notes.setStyleSheet("color: #EAB308;")
        layout.addRow("Notes:", self.info_notes)

        return group

    def _create_conflicts_panel(self) -> QGroupBox:
        """Create conflicts display."""
        group = QGroupBox("Conflicts & Warnings")
        layout = QVBoxLayout(group)

        self.conflicts_text = QTextEdit()
        self.conflicts_text.setReadOnly(True)
        self.conflicts_text.setMaximumHeight(120)
        self.conflicts_text.setStyleSheet(
            "font-family: monospace; background-color: #1E1E2E;"
        )
        layout.addWidget(self.conflicts_text)

        validate_btn = QPushButton("Validate All")
        validate_btn.setObjectName("secondary")
        validate_btn.clicked.connect(self._validate_pins)
        layout.addWidget(validate_btn)

        return group

    def _create_wizard_panel(self) -> QGroupBox:
        """Create quick setup wizards."""
        group = QGroupBox("Quick Setup")
        layout = QVBoxLayout(group)

        # Wizard selector
        wizard_layout = QHBoxLayout()

        self.wizard_combo = QComboBox()
        self.wizard_combo.addItems([
            "DC Motor",
            "Encoder",
            "Stepper",
            "Servo",
            "I2C",
            "SPI",
            "UART",
        ])
        wizard_layout.addWidget(self.wizard_combo, 1)

        # Instance number
        wizard_layout.addWidget(QLabel("#"))
        self.instance_input = QLineEdit("0")
        self.instance_input.setMaximumWidth(40)
        wizard_layout.addWidget(self.instance_input)

        layout.addLayout(wizard_layout)

        # Suggest button
        suggest_btn = QPushButton("Suggest Pins")
        suggest_btn.clicked.connect(self._suggest_pins)
        layout.addWidget(suggest_btn)

        # Apply button
        apply_btn = QPushButton("Apply Suggestion")
        apply_btn.setObjectName("success")
        apply_btn.clicked.connect(self._apply_suggestion)
        layout.addWidget(apply_btn)

        # Suggestion display
        self.suggestion_text = QTextEdit()
        self.suggestion_text.setReadOnly(True)
        self.suggestion_text.setMaximumHeight(100)
        self.suggestion_text.setStyleSheet(
            "font-family: monospace; background-color: #1E1E2E;"
        )
        layout.addWidget(self.suggestion_text)

        return group

    def _load_pin_service(self) -> None:
        """Load the pin service."""
        try:
            from mara_host.services.pins import PinService
            self._pin_service = PinService()
            self._refresh_table()
            self._populate_gpio_combo()
            self._validate_pins()
        except Exception as e:
            self.signals.log_error(f"Failed to load pin service: {e}")

    def _populate_gpio_combo(self) -> None:
        """Populate GPIO dropdown with free pins."""
        self.gpio_input.clear()

        if not self._pin_service:
            return

        # Get free pins, prioritizing safe ones
        try:
            free_pins = self._pin_service.get_free_pins()
            safe_pins = self._pin_service.get_safe_pins()

            # Add safe pins first
            for gpio in sorted(safe_pins):
                if gpio in free_pins:
                    self.gpio_input.addItem(f"{gpio} (safe)", gpio)

            # Add other free pins
            for gpio in sorted(free_pins):
                if gpio not in safe_pins:
                    self.gpio_input.addItem(str(gpio), gpio)
        except Exception:
            # Fallback to all GPIOs
            for gpio in range(40):
                self.gpio_input.addItem(str(gpio), gpio)

    def _refresh_table(self) -> None:
        """Refresh the pin table."""
        if not self._pin_service:
            return

        self.pin_table.setRowCount(0)

        try:
            all_pins = self._pin_service.get_all_pins()
            assignments = self._pin_service.get_assignments()
            conflicts = self._pin_service.detect_conflicts()
            conflict_gpios = {c.gpio for c in conflicts}

            filter_mode = self.filter_combo.currentText()

            for gpio, pin_info in sorted(all_pins.items()):
                # Apply filter
                is_assigned = gpio in [assignments.get(name) for name in assignments]
                assigned_name = None
                for name, g in assignments.items():
                    if g == gpio:
                        assigned_name = name
                        break

                is_safe = self._pin_service.is_safe_pin(gpio)
                is_flash = self._pin_service.is_flash_pin(gpio)
                is_boot = self._pin_service.is_boot_pin(gpio)
                has_conflict = gpio in conflict_gpios

                # Filter logic
                if filter_mode == "Assigned Only" and not is_assigned:
                    continue
                if filter_mode == "Free (Safe)" and (is_assigned or not is_safe):
                    continue
                if filter_mode == "Free (All)" and is_assigned:
                    continue
                if filter_mode == "Conflicts" and not has_conflict:
                    continue

                # Add row
                row = self.pin_table.rowCount()
                self.pin_table.insertRow(row)

                # GPIO number
                gpio_item = QTableWidgetItem(str(gpio))
                gpio_item.setData(Qt.UserRole, gpio)
                gpio_item.setTextAlignment(Qt.AlignCenter)
                self.pin_table.setItem(row, 0, gpio_item)

                # Name
                name_item = QTableWidgetItem(assigned_name or "")
                if assigned_name:
                    name_item.setForeground(QColor(self.COLORS["assigned"]))
                self.pin_table.setItem(row, 1, name_item)

                # Status
                if is_flash:
                    status = "FLASH"
                    color = self.COLORS["flash"]
                elif has_conflict:
                    status = "CONFLICT"
                    color = self.COLORS["conflict"]
                elif is_assigned:
                    status = "Assigned"
                    color = self.COLORS["assigned"]
                elif is_safe:
                    status = "Free (Safe)"
                    color = self.COLORS["free_safe"]
                elif is_boot:
                    status = "Free (Boot)"
                    color = self.COLORS["free_boot"]
                elif self._pin_service.is_input_only(gpio):
                    status = "Free (Input)"
                    color = self.COLORS["free_input"]
                else:
                    status = "Free"
                    color = "#707090"

                status_item = QTableWidgetItem(status)
                status_item.setForeground(QColor(color))
                self.pin_table.setItem(row, 2, status_item)

                # Capabilities
                caps = self._pin_service.capability_string(gpio)
                caps_item = QTableWidgetItem(caps)
                caps_item.setForeground(QColor("#B0B0C0"))
                self.pin_table.setItem(row, 3, caps_item)

                # Notes (PinInfo is a dataclass, use attribute access)
                notes = getattr(pin_info, "notes", "") or getattr(pin_info, "warning", "")
                notes_item = QTableWidgetItem(notes)
                notes_item.setForeground(QColor("#707090"))
                self.pin_table.setItem(row, 4, notes_item)

        except Exception as e:
            self.signals.log_error(f"Failed to refresh pin table: {e}")

    def _on_pin_selected(self) -> None:
        """Handle pin selection."""
        selected = self.pin_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        gpio_item = self.pin_table.item(row, 0)
        if not gpio_item:
            return

        gpio = gpio_item.data(Qt.UserRole)
        self._show_pin_info(gpio)

    def _show_pin_info(self, gpio: int) -> None:
        """Show detailed info for a pin."""
        if not self._pin_service:
            return

        try:
            info = self._pin_service.get_pin_info(gpio)
            if not info:
                return

            self.info_gpio.setText(f"GPIO {gpio}")

            # Get assignment name
            assignments = self._pin_service.get_assignments()
            name = None
            for n, g in assignments.items():
                if g == gpio:
                    name = n
                    break
            self.info_name.setText(name or "(unassigned)")

            # Capabilities
            caps = self._pin_service.capability_string(gpio)
            self.info_caps.setText(caps)

            # ADC (PinInfo has adc_channel as string like "ADC1_CH0")
            adc_channel = getattr(info, "adc_channel", None)
            if adc_channel:
                self.info_adc.setText(adc_channel)
            else:
                self.info_adc.setText("None")

            # Touch
            touch = getattr(info, "touch_channel", None)
            self.info_touch.setText(f"Touch {touch}" if touch is not None else "None")

            # Notes/warnings
            notes = getattr(info, "notes", "") or ""
            warning = getattr(info, "warning", "") or ""
            if self._pin_service.is_flash_pin(gpio):
                notes = "DO NOT USE - Flash connected"
            elif self._pin_service.is_boot_pin(gpio):
                notes = f"Boot pin - {warning}" if warning else "Boot strapping pin"
            elif warning:
                notes = warning
            self.info_notes.setText(notes or "None")

        except Exception as e:
            self.signals.log_error(f"Failed to get pin info: {e}")

    def _assign_pin(self) -> None:
        """Assign a pin."""
        if not self._pin_service:
            return

        name = self.name_input.text().strip()
        if not name:
            self.signals.status_error.emit("Please enter a pin name")
            return

        gpio = self.gpio_input.currentData()
        if gpio is None:
            self.signals.status_error.emit("Please select a GPIO")
            return

        try:
            self._pin_service.assign(name, gpio)
            self.signals.status_message.emit(f"Assigned {name} to GPIO {gpio}")
            self._refresh_table()
            self._populate_gpio_combo()
            self._validate_pins()
            self.name_input.clear()
        except Exception as e:
            self.signals.status_error.emit(f"Failed to assign: {e}")

    def _remove_pin(self) -> None:
        """Remove a pin assignment."""
        if not self._pin_service:
            return

        name = self.name_input.text().strip()
        if not name:
            # Try to get from selection
            selected = self.pin_table.selectedItems()
            if selected:
                row = selected[0].row()
                name_item = self.pin_table.item(row, 1)
                if name_item:
                    name = name_item.text()

        if not name:
            self.signals.status_error.emit("Please enter or select a pin name")
            return

        try:
            self._pin_service.remove(name)
            self.signals.status_message.emit(f"Removed {name}")
            self._refresh_table()
            self._populate_gpio_combo()
            self._validate_pins()
        except Exception as e:
            self.signals.status_error.emit(f"Failed to remove: {e}")

    def _validate_pins(self) -> None:
        """Validate current pin assignments."""
        if not self._pin_service:
            return

        try:
            conflicts = self._pin_service.detect_conflicts()

            if not conflicts:
                self.conflicts_text.setHtml(
                    '<span style="color: #22C55E;">No conflicts detected</span>'
                )
            else:
                html = ""
                for c in conflicts:
                    color = "#EF4444" if c.severity == "error" else "#EAB308"
                    html += f'<span style="color: {color};">'
                    html += f"GPIO {c.gpio}: {c.message}"
                    html += "</span><br>"
                self.conflicts_text.setHtml(html)

        except Exception as e:
            self.conflicts_text.setPlainText(f"Error: {e}")

    def _suggest_pins(self) -> None:
        """Suggest pins for a use case."""
        if not self._pin_service:
            return

        wizard_map = {
            "DC Motor": "motor",
            "Encoder": "encoder",
            "Stepper": "stepper",
            "Servo": "servo",
            "I2C": "i2c",
            "SPI": "spi",
            "UART": "uart",
        }

        wizard = self.wizard_combo.currentText()
        use_case = wizard_map.get(wizard, "motor")
        instance = self.instance_input.text() or "0"

        try:
            # Get recommendation method
            method_name = f"recommend_{use_case}_pins"
            if hasattr(self._pin_service, method_name):
                # Methods that require an ID parameter
                needs_id = {"motor", "encoder", "stepper", "servo"}
                if use_case in needs_id:
                    recommendations = getattr(self._pin_service, method_name)(instance)
                elif use_case == "uart":
                    recommendations = getattr(self._pin_service, method_name)(instance)
                else:
                    # i2c, spi don't need an ID
                    recommendations = getattr(self._pin_service, method_name)()
            else:
                recommendations = self._pin_service.suggest_pins(use_case)

            if not recommendations:
                self.suggestion_text.setPlainText("No suitable pins found")
                return

            # Format suggestions
            text = f"{wizard} #{instance}:\n"
            self._current_suggestion = {}

            # Handle GroupRecommendation (dataclass with suggested_assignments)
            if hasattr(recommendations, 'suggested_assignments'):
                for name, gpio in recommendations.suggested_assignments.items():
                    # Name is already complete (e.g., MOTOR_0_PWM)
                    text += f"  {name}: GPIO {gpio}\n"
                    self._current_suggestion[name] = gpio
                # Show any warnings
                if recommendations.warnings:
                    text += "\nWarnings:\n"
                    for warning in recommendations.warnings:
                        text += f"  ⚠️ {warning}\n"
            elif isinstance(recommendations, dict):
                # Plain dict recommendation - names are already complete
                for name, gpio in recommendations.items():
                    text += f"  {name}: GPIO {gpio}\n"
                    self._current_suggestion[name] = gpio
            elif isinstance(recommendations, list):
                # List of PinRecommendation objects - need to generate names
                for i, rec in enumerate(recommendations[:4]):
                    name = f"{use_case.upper()}_{instance}_{i}"
                    text += f"  {name}: GPIO {rec.gpio} (score: {rec.score})\n"
                    self._current_suggestion[name] = rec.gpio
            else:
                self.suggestion_text.setPlainText(f"Unexpected recommendation type: {type(recommendations)}")
                return

            self.suggestion_text.setPlainText(text)

        except Exception as e:
            self.suggestion_text.setPlainText(f"Error: {e}")

    def _apply_suggestion(self) -> None:
        """Apply the current suggestion."""
        if not self._pin_service or not hasattr(self, '_current_suggestion'):
            self.signals.status_error.emit("No suggestion to apply")
            return

        try:
            for name, gpio in self._current_suggestion.items():
                self._pin_service.assign(name, gpio)

            self.signals.status_message.emit(
                f"Applied {len(self._current_suggestion)} pin assignments"
            )
            self._refresh_table()
            self._populate_gpio_combo()
            self._validate_pins()
            self._current_suggestion = {}
            self.suggestion_text.clear()

        except Exception as e:
            self.signals.status_error.emit(f"Failed to apply: {e}")

    def _save_config(self) -> None:
        """Save pin configuration."""
        if not self._pin_service:
            return

        try:
            from mara_host.tools.schema.pins import save_pins

            assignments = self._pin_service.get_assignments()
            save_pins(assignments)
            self.signals.status_message.emit("Pin configuration saved")

        except Exception as e:
            self.signals.status_error.emit(f"Failed to save: {e}")
