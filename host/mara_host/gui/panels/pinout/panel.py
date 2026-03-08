# mara_host/gui/panels/pinout/panel.py
"""
Pinout configuration panel.

Thin composition layer that wires together the pin widgets.
Supports both table view and visual board diagram view.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QSplitter,
    QTextEdit,
    QTabWidget,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.gui.panels.pinout.pin_table import PinTableWidget
from mara_host.gui.panels.pinout.pin_info import PinInfoWidget
from mara_host.gui.panels.pinout.pin_wizard import PinWizardWidget
from mara_host.gui.panels.pinout.board_diagram import BoardDiagramWidget


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
        self._selected_gpio = None
        self._setup_ui()
        self._setup_connections()
        self._load_pin_service()

    def _setup_ui(self) -> None:
        """Set up the pinout panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left side - Tab widget with Table and Board views
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Tab widget for switching views
        self.view_tabs = QTabWidget()

        # Table view tab
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.pin_table = PinTableWidget()
        table_layout.addWidget(self.pin_table)
        self.view_tabs.addTab(table_tab, "Table View")

        # Board diagram view tab
        board_tab = QWidget()
        board_layout = QVBoxLayout(board_tab)
        board_layout.setContentsMargins(0, 0, 0, 0)
        self.board_diagram = BoardDiagramWidget()
        board_layout.addWidget(self.board_diagram)
        self.view_tabs.addTab(board_tab, "Board Diagram")

        left_layout.addWidget(self.view_tabs, 1)

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
        self.pin_info = PinInfoWidget()
        right_layout.addWidget(self.pin_info)

        # Conflicts
        right_layout.addWidget(self._create_conflicts_panel())

        # Wizards
        self.pin_wizard = PinWizardWidget()
        right_layout.addWidget(self.pin_wizard)

        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([600, 350])

        layout.addWidget(splitter)

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

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        # Table view connections
        self.pin_table.pin_selected.connect(self.pin_info.show_pin)
        self.pin_table.pin_selected.connect(self._on_pin_selected)

        # Board diagram connections
        self.board_diagram.pin_selected.connect(self.pin_info.show_pin)
        self.board_diagram.pin_selected.connect(self._on_pin_selected)

        # Wizard connections
        self.pin_wizard.pins_applied.connect(self._on_pins_applied)

        # Sync selection between views when tab changes
        self.view_tabs.currentChanged.connect(self._on_tab_changed)

    def _load_pin_service(self) -> None:
        """Load the pin service."""
        try:
            from mara_host.services.pins import PinService
            self._pin_service = PinService()

            # Set service on child widgets
            self.pin_table.set_pin_service(self._pin_service)
            self.pin_info.set_pin_service(self._pin_service)
            self.pin_wizard.set_pin_service(self._pin_service)
            self.board_diagram.set_pin_service(self._pin_service)

            self.pin_table.refresh()
            self.board_diagram.refresh()
            self._populate_gpio_combo()
            self._validate_pins()
        except Exception as e:
            self.signals.log_error(f"Failed to load pin service: {e}")

    def _populate_gpio_combo(self) -> None:
        """Populate GPIO dropdown with free pins."""
        self.gpio_input.clear()

        if not self._pin_service:
            return

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
            for gpio in range(40):
                self.gpio_input.addItem(str(gpio), gpio)

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
            self._refresh_all()
            self.name_input.clear()
        except Exception as e:
            self.signals.status_error.emit(f"Failed to assign: {e}")

    def _remove_pin(self) -> None:
        """Remove a pin assignment."""
        if not self._pin_service:
            return

        name = self.name_input.text().strip()
        if not name:
            name = self.pin_table.get_selected_name()

        if not name:
            self.signals.status_error.emit("Please enter or select a pin name")
            return

        try:
            self._pin_service.remove(name)
            self.signals.status_message.emit(f"Removed {name}")
            self._refresh_all()
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

    def _on_pins_applied(self, assignments: dict) -> None:
        """Handle pins applied from wizard."""
        self.signals.status_message.emit(
            f"Applied {len(assignments)} pin assignments"
        )
        self._refresh_all()

    def _on_pin_selected(self, gpio: int) -> None:
        """Handle pin selection from either view."""
        self._selected_gpio = gpio
        # Update GPIO combo to show selected pin
        for i in range(self.gpio_input.count()):
            if self.gpio_input.itemData(i) == gpio:
                self.gpio_input.setCurrentIndex(i)
                break
        # Sync selection to board diagram
        self.board_diagram.set_selected_pin(gpio)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change - refresh the new view."""
        if index == 1:  # Board diagram tab
            self.board_diagram.refresh()

    def _refresh_all(self) -> None:
        """Refresh all components."""
        self.pin_table.refresh()
        self.board_diagram.refresh()
        self._populate_gpio_combo()
        self._validate_pins()

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
