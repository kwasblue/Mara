# mara_host/gui/panels/diagram.py
"""
Block Diagram panel for visual system design.

Provides Hardware Layout and Control Loop diagram views.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "diagram",
    "label": "Diagram",
    "order": 80,
}

import json

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QFrame,
)

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.gui.widgets.block_diagram import (
    HardwareLayoutDiagram,
    ControlLoopDiagram,
    DiagramState,
)


class DiagramPanel(QWidget):
    """
    Block Diagram panel with tabbed views for Hardware and Control diagrams.

    Features:
    - Hardware Layout: Design ESP32 peripheral connections
    - Control Loop: Configure PID controllers and observers
    - Save/Load diagram state to JSON
    - Sync control configuration to robot
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

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(
            "background-color: #18181B; "
            "border-bottom: 1px solid #27272A;"
        )
        toolbar.setFixedHeight(48)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 8, 16, 8)

        title = QLabel("Block Diagram")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #FAFAFA;")
        toolbar_layout.addWidget(title)

        toolbar_layout.addStretch()

        # Save/Load buttons
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("secondary")
        self.save_btn.clicked.connect(self._save_diagram)
        toolbar_layout.addWidget(self.save_btn)

        self.load_btn = QPushButton("Load")
        self.load_btn.setObjectName("secondary")
        self.load_btn.clicked.connect(self._load_diagram)
        toolbar_layout.addWidget(self.load_btn)

        layout.addWidget(toolbar)

        # Tab widget for diagram views
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Hardware Layout tab
        self.hardware_diagram = HardwareLayoutDiagram()
        self.tabs.addTab(self.hardware_diagram, "Hardware Layout")

        # Control Loop tab
        self.control_diagram = ControlLoopDiagram()
        self.control_diagram.set_controller(self.controller)
        self.tabs.addTab(self.control_diagram, "Control Loop")

        layout.addWidget(self.tabs)

    def _setup_connections(self) -> None:
        """Connect signals."""
        # Diagram changes
        self.hardware_diagram.diagram_changed.connect(self._on_diagram_changed)
        self.control_diagram.diagram_changed.connect(self._on_diagram_changed)

        # Block configuration
        self.hardware_diagram.block_configured.connect(self._on_block_configured)
        self.control_diagram.block_configured.connect(self._on_block_configured)

        # Controller sync
        self.control_diagram.controller_sync_requested.connect(
            self._on_controller_sync
        )

        # Connection state
        self.signals.connection_changed.connect(self._on_connection_changed)

    def set_pin_service(self, pin_service) -> None:
        """Set the pin service for hardware layout."""
        self._pin_service = pin_service
        self.hardware_diagram.set_pin_service(pin_service)

    def _on_diagram_changed(self) -> None:
        """Handle diagram state change."""
        self.signals.log_info("Diagram modified")

    def _on_block_configured(self, block_id: str, config: dict) -> None:
        """Handle block configuration change."""
        self.signals.log_info(f"Block {block_id} configured")

    def _on_controller_sync(self, block_id: str, config: dict) -> None:
        """Handle controller sync request."""
        self.signals.log_info(f"Controller {block_id} synced to robot")

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        """Handle connection state change."""
        # Update control diagram's controller reference
        if connected:
            self.control_diagram.set_controller(self.controller)

    def _save_diagram(self) -> None:
        """Save current diagram to JSON file."""
        # Get state from active tab
        current_idx = self.tabs.currentIndex()
        if current_idx == 0:
            state = self.hardware_diagram.get_state()
            default_name = "hardware_layout.json"
        else:
            state = self.control_diagram.get_state()
            default_name = "control_loop.json"

        # File dialog
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Diagram",
            default_name,
            "JSON Files (*.json);;All Files (*)",
        )

        if not filename:
            return

        try:
            with open(filename, "w") as f:
                json.dump(state.to_dict(), f, indent=2)
            self.signals.log_info(f"Diagram saved to {filename}")
            QMessageBox.information(self, "Saved", f"Diagram saved to {filename}")
        except Exception as e:
            self.signals.log_error(f"Failed to save diagram: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save: {e}")

    def _load_diagram(self) -> None:
        """Load diagram from JSON file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Diagram",
            "",
            "JSON Files (*.json);;All Files (*)",
        )

        if not filename:
            return

        try:
            with open(filename, "r") as f:
                data = json.load(f)

            state = DiagramState.from_dict(data)

            # Load into appropriate view
            if state.diagram_type == "hardware":
                self.hardware_diagram.load_state(state)
                self.tabs.setCurrentIndex(0)
            else:
                self.control_diagram.load_state(state)
                self.tabs.setCurrentIndex(1)

            self.signals.log_info(f"Diagram loaded from {filename}")
            QMessageBox.information(self, "Loaded", f"Diagram loaded from {filename}")

        except Exception as e:
            self.signals.log_error(f"Failed to load diagram: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load: {e}")

    def create_example_pid_loop(self) -> None:
        """Create an example PID control loop."""
        self.control_diagram.create_basic_pid_loop()
        self.tabs.setCurrentIndex(1)
