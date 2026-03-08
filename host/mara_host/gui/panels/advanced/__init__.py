# mara_host/gui/panels/advanced/__init__.py
"""
Advanced control panel components.

Provides UI for configuring and monitoring advanced control features:
- Signal Bus: Define, set, and monitor signals
- Controllers: Configure PID and state-space control slots
- Observers: Configure state observers (Luenberger, etc.)
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "advanced",
    "label": "Advanced",
    "order": 70,
}

from mara_host.gui.panels.advanced.slot_base import SlotWidgetBase, SlotTabPanel
from mara_host.gui.panels.advanced.signal_bus_tab import SignalBusTab
from mara_host.gui.panels.advanced.controllers_tab import ControllersTab, ControllerSlotWidget
from mara_host.gui.panels.advanced.observers_tab import ObserversTab, ObserverSlotWidget
from mara_host.gui.panels.advanced.panel import AdvancedPanel

__all__ = [
    # Base classes
    "SlotWidgetBase",
    "SlotTabPanel",
    # Tabs
    "AdvancedPanel",
    "SignalBusTab",
    "ControllersTab",
    "ControllerSlotWidget",
    "ObserversTab",
    "ObserverSlotWidget",
]
