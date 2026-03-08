# mara_host/gui/main_window.py
"""
Main window for the MARA Control GUI.

AUTO-DISCOVERY: Panels are automatically discovered from gui/panels/.
To add a new panel, create a file with PANEL_META and a Panel class.

Example:
    # gui/panels/mypanel.py
    PANEL_META = {
        "id": "mypanel",
        "label": "My Panel",
        "order": 50,  # Lower = higher in sidebar
    }

    class MyPanelPanel(QWidget):
        def __init__(self, signals, controller, settings):
            ...

The panel will be auto-discovered and added to the sidebar.
"""

import importlib
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QLabel,
    QStatusBar,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QCloseEvent, QShortcut, QKeySequence

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings, DeviceCapabilities


def _discover_panels() -> list[dict]:
    """
    Auto-discover panel modules from gui/panels/.

    Returns list of panel info dicts sorted by order.
    Each dict has: id, label, order, module_name, class_name
    """
    panels = []
    panels_dir = Path(__file__).parent / "panels"
    print(f"[MainWindow] Discovering panels from: {panels_dir}")

    for item in sorted(panels_dir.iterdir()):
        # Skip __pycache__ and private files
        if item.name.startswith("_"):
            continue

        # Determine module name
        if item.is_file() and item.suffix == ".py":
            module_name = item.stem
        elif item.is_dir() and (item / "__init__.py").exists():
            module_name = item.name
        else:
            continue

        try:
            # Import the module
            module = importlib.import_module(
                f"mara_host.gui.panels.{module_name}"
            )

            # Check for PANEL_META
            if not hasattr(module, "PANEL_META"):
                continue

            meta = module.PANEL_META
            if not isinstance(meta, dict) or "id" not in meta or "label" not in meta:
                continue

            # Find the panel class (convention: class name ends with "Panel")
            panel_class = None
            for attr_name in dir(module):
                if attr_name.endswith("Panel") and attr_name != "Panel":
                    cls = getattr(module, attr_name)
                    if isinstance(cls, type):
                        panel_class = cls
                        break

            if panel_class is None:
                continue

            panels.append({
                "id": meta["id"],
                "label": meta["label"],
                "order": meta.get("order", 100),
                "module_name": module_name,
                "class": panel_class,
            })

        except ImportError as e:
            import warnings
            warnings.warn(f"Failed to import panel '{module_name}': {e}")

    # Sort by order
    panels.sort(key=lambda p: p["order"])
    print(f"[MainWindow] Discovered {len(panels)} panels: {[p['id'] for p in panels]}")
    return panels


class MainWindow(QMainWindow):
    """
    Main application window with sidebar navigation.

    Layout:
        ┌─────────────┬────────────────────────────────────┐
        │  Sidebar    │  Panel Content                     │
        │             │                                    │
        │  Dashboard  │                                    │
        │  Control    │                                    │
        │  Camera     │                                    │
        │  Commands   │                                    │
        │  Config     │                                    │
        │  Logs       │                                    │
        │             │                                    │
        └─────────────┴────────────────────────────────────┘
        │ Status Bar                                       │
        └──────────────────────────────────────────────────┘
    """

    def __init__(self, signals: GuiSignals, controller: RobotController, dev_mode: bool = False):
        super().__init__()

        self.signals = signals
        self.controller = controller
        self.settings = GuiSettings()
        self._dev_mode = dev_mode

        # Discover panels
        self._panel_infos = _discover_panels()

        self.setWindowTitle("MARA Control" + (" [DEV]" if dev_mode else ""))
        self.setMinimumSize(1024, 768)

        # Create UI
        self._setup_ui()
        self._setup_connections()

        # Restore window state
        self._restore_window_state()

    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main horizontal layout
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # Content area
        self.content_stack = QStackedWidget()
        self._create_panels()
        main_layout.addWidget(self.content_stack, 1)

        # Status bar
        self._setup_status_bar()

    def _create_sidebar(self) -> QWidget:
        """Create the navigation sidebar."""
        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("background-color: #111113;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(2)

        # Logo/Title - minimal
        title = QLabel("MARA")
        title.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet(
            "color: #FAFAFA; "
            "padding: 12px 8px 8px 8px;"
        )
        layout.addWidget(title)

        # Dev mode indicator
        if self._dev_mode:
            dev_label = QLabel("DEV MODE")
            dev_label.setAlignment(Qt.AlignLeft)
            dev_label.setStyleSheet(
                "color: #F59E0B; "
                "background-color: rgba(245, 158, 11, 0.15); "
                "padding: 4px 8px; "
                "margin: 0 8px 16px 8px; "
                "border-radius: 4px; "
                "font-size: 10px; "
                "font-weight: 600;"
            )
            layout.addWidget(dev_label)
        else:
            # Add spacing to match layout
            layout.addSpacing(16)

        # Navigation list
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("Sidebar")
        self.nav_list.setSpacing(2)

        for panel_info in self._panel_infos:
            item = QListWidgetItem(panel_info["label"])
            item.setData(Qt.UserRole, panel_info["id"])
            item.setSizeHint(QSize(160, 36))
            self.nav_list.addItem(item)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        layout.addWidget(self.nav_list)

        # Spacer
        layout.addStretch()

        # Features indicator (shows when connected)
        self.features_label = QLabel("")
        self.features_label.setAlignment(Qt.AlignLeft)
        self.features_label.setWordWrap(True)
        self.features_label.setStyleSheet(
            "color: #52525B; "
            "padding: 4px 8px; "
            "font-size: 9px;"
        )
        self.features_label.setVisible(False)
        layout.addWidget(self.features_label)

        # Connection status - subtle
        self.connection_label = QLabel("Disconnected")
        self.connection_label.setAlignment(Qt.AlignLeft)
        self.connection_label.setWordWrap(True)
        self.connection_label.setStyleSheet(
            "color: #52525B; "
            "padding: 12px 8px; "
            "font-size: 11px;"
        )
        layout.addWidget(self.connection_label)

        return sidebar

    def _create_panels(self) -> None:
        """Create and add panel widgets (auto-discovered)."""
        self.panels = {}

        for panel_info in self._panel_infos:
            panel_id = panel_info["id"]
            panel_class = panel_info["class"]

            try:
                # Instantiate the panel
                panel = panel_class(self.signals, self.controller, self.settings)
                self.panels[panel_id] = panel
                self.content_stack.addWidget(panel)
                print(f"[MainWindow] Created panel: {panel_id}")
            except Exception as e:
                print(f"[MainWindow] ERROR creating panel '{panel_id}': {e}")
                import traceback
                traceback.print_exc()

        # Select initial panel
        last_panel = self.settings.get_last_panel()
        panel_ids = [p["id"] for p in self._panel_infos]
        if last_panel in panel_ids:
            idx = panel_ids.index(last_panel)
            self.nav_list.setCurrentRow(idx)
        else:
            self.nav_list.setCurrentRow(0)

    def _setup_status_bar(self) -> None:
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Robot state label
        self.state_label = QLabel("UNKNOWN")
        self.state_label.setStyleSheet(
            "background-color: #27272A; "
            "color: #71717A; "
            "padding: 4px 12px; "
            "border-radius: 4px; "
            "font-size: 11px; "
            "font-weight: 500;"
        )
        self.status_bar.addPermanentWidget(self.state_label)

        # Firmware version
        self.firmware_label = QLabel("")
        self.firmware_label.setStyleSheet(
            "color: #71717A; "
            "font-size: 11px; "
            "padding-left: 12px;"
        )
        self.status_bar.addPermanentWidget(self.firmware_label)

    def _setup_connections(self) -> None:
        """Connect signals to slots."""
        # Connection
        self.signals.connection_changed.connect(self._on_connection_changed)
        self.signals.connection_error.connect(self._on_connection_error)

        # Capabilities
        self.signals.capabilities_changed.connect(self._on_capabilities_changed)

        # State
        self.signals.state_changed.connect(self._on_state_changed)

        # Status messages
        self.signals.status_message.connect(self._on_status_message)
        self.signals.status_error.connect(self._on_status_error)

        # Log messages
        self.signals.log_message.connect(self._on_log_message)

        # Keyboard shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        """Set up global keyboard shortcuts."""
        # E-STOP: Space or Escape
        QShortcut(QKeySequence(Qt.Key_Space), self).activated.connect(
            self._shortcut_estop
        )
        QShortcut(QKeySequence(Qt.Key_Escape), self).activated.connect(
            self._shortcut_estop
        )

        # Arm: Ctrl+A
        QShortcut(QKeySequence("Ctrl+Shift+A"), self).activated.connect(
            self.controller.arm
        )

        # Disarm: Ctrl+D
        QShortcut(QKeySequence("Ctrl+Shift+D"), self).activated.connect(
            self.controller.disarm
        )

        # Activate: Ctrl+Shift+E
        QShortcut(QKeySequence("Ctrl+Shift+E"), self).activated.connect(
            self.controller.activate
        )

        # Panel switching: Ctrl+1 through Ctrl+9
        for i, panel_info in enumerate(self._panel_infos):
            if i < 9:
                shortcut = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
                shortcut.activated.connect(
                    lambda idx=i: self.nav_list.setCurrentRow(idx)
                )

    def _shortcut_estop(self) -> None:
        """Handle E-STOP shortcut."""
        if self.controller.is_connected:
            self.controller.estop()
            self.signals.status_error.emit("E-STOP activated!")

    def _on_nav_changed(self, index: int) -> None:
        """Handle navigation change."""
        if 0 <= index < len(self._panel_infos):
            panel_id = self._panel_infos[index]["id"]
            self.content_stack.setCurrentIndex(index)
            self.settings.set_last_panel(panel_id)

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        """Handle connection state change."""
        if connected:
            self.connection_label.setText(f"Connected\n{info}")
            self.connection_label.setStyleSheet(
                "color: #22C55E; "
                "padding: 12px 8px; "
                "font-size: 11px;"
            )
        else:
            self.connection_label.setText("Disconnected")
            self.connection_label.setStyleSheet(
                "color: #52525B; "
                "padding: 12px 8px; "
                "font-size: 11px;"
            )
            self.firmware_label.setText("")
            # Hide features when disconnected
            self.features_label.setVisible(False)
            self.features_label.setText("")

    def _on_capabilities_changed(self, caps: DeviceCapabilities) -> None:
        """Handle device capabilities change."""
        if caps.features:
            # Show abbreviated features list
            feature_icons = {
                "dc_motor": "M",
                "servo": "S",
                "stepper": "St",
                "imu": "I",
                "encoder": "E",
                "gpio": "G",
                "telemetry": "T",
                "motion_ctrl": "Mot",
                "wifi": "W",
                "uart": "U",
            }
            icons = []
            for f in caps.features:
                if f in feature_icons:
                    icons.append(feature_icons[f])
            if icons:
                self.features_label.setText(f"Features: {' '.join(icons)}")
                self.features_label.setVisible(True)

    def _on_connection_error(self, error: str) -> None:
        """Handle connection error."""
        self.connection_label.setText("Error")
        self.connection_label.setStyleSheet(
            "color: #EF4444; "
            "padding: 12px 8px; "
            "font-size: 11px;"
        )
        self.status_bar.showMessage(f"Error: {error}", 5000)

    def _on_state_changed(self, state: str) -> None:
        """Handle robot state change."""
        self.state_label.setText(state)

        # Update style based on state
        colors = {
            "IDLE": "#52525B",
            "ARMED": "#F59E0B",
            "ACTIVE": "#8B5CF6",
            "ESTOP": "#EF4444",
        }
        text_colors = {
            "ARMED": "#18181B",
        }
        color = colors.get(state, "#52525B")
        text_color = text_colors.get(state, "white")
        self.state_label.setStyleSheet(
            f"background-color: {color}; "
            f"color: {text_color}; "
            f"padding: 4px 12px; "
            f"border-radius: 4px; "
            f"font-weight: 500; "
            f"font-size: 11px;"
        )

    def _on_status_message(self, message: str) -> None:
        """Handle status message."""
        self.status_bar.showMessage(message, 3000)

    def _on_status_error(self, error: str) -> None:
        """Handle status error."""
        self.status_bar.showMessage(f"Error: {error}", 5000)

    def _on_log_message(self, timestamp: str, level: str, message: str) -> None:
        """Handle log message."""
        print(f"[LOG] {timestamp} [{level}] {message}")  # Debug
        if "logs" in self.panels:
            self.panels["logs"].add_message(timestamp, level, message)
        else:
            print(f"[WARNING] logs panel not found in panels: {list(self.panels.keys())}")

    def _restore_window_state(self) -> None:
        """Restore window geometry and state."""
        geometry = self.settings.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings.get_window_state()
        if state:
            self.restoreState(state)

    def _save_window_state(self) -> None:
        """Save window geometry and state."""
        self.settings.set_window_geometry(self.saveGeometry())
        self.settings.set_window_state(self.saveState())

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close."""
        self._save_window_state()
        self.controller.stop()
        event.accept()
