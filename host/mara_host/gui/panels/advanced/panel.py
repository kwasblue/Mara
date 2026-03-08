# mara_host/gui/panels/advanced/panel.py
"""
Advanced control panel with tabs for signal bus, controllers, and observers.

This is a thin composition layer that wires together the tab widgets.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.gui.panels.advanced.signal_bus_tab import SignalBusTab
from mara_host.gui.panels.advanced.controllers_tab import ControllersTab
from mara_host.gui.panels.advanced.observers_tab import ObserversTab


class AdvancedPanel(QWidget):
    """
    Advanced control panel with tabs for signal bus, controllers, and observers.

    Layout:
        +-------------------------------------------------+
        | [Signal Bus] [Controllers] [Observers]          |
        +-------------------------------------------------+
        |                                                 |
        |  (tab content)                                  |
        |                                                 |
        +-------------------------------------------------+
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
