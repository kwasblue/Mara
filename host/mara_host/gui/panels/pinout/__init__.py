# mara_host/gui/panels/pinout/__init__.py
"""
Pinout configuration panel components.

Provides UI for GPIO pin management, conflict detection, and quick setup wizards.
Includes both table view and visual ESP32 board diagram for pin configuration.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "pinout",
    "label": "Pinout",
    "order": 100,
}

from mara_host.gui.panels.pinout.pin_table import PinTableWidget
from mara_host.gui.panels.pinout.pin_wizard import PinWizardWidget
from mara_host.gui.panels.pinout.pin_info import PinInfoWidget
from mara_host.gui.panels.pinout.board_diagram import BoardDiagramWidget, ESP32BoardWidget
from mara_host.gui.panels.pinout.panel import PinoutPanel

__all__ = [
    "PinoutPanel",
    "PinTableWidget",
    "PinWizardWidget",
    "PinInfoWidget",
    "BoardDiagramWidget",
    "ESP32BoardWidget",
]
