# mara_host/gui/core/__init__.py
"""
GUI core components.

Provides the fundamental infrastructure for the GUI application:
- GuiSignals: Thread-safe Qt signal definitions
- RobotController: Async wrapper for robot operations
- AppState: Application state management
- Theme: Dark theme stylesheet
- Settings: QSettings wrapper for persistence
"""

from mara_host.gui.core.signals import GuiSignals
from mara_host.gui.core.controller import RobotController
from mara_host.gui.core.state import AppState, ConnectionState, DeviceCapabilities
from mara_host.gui.core.theme import DARK_THEME, apply_theme
from mara_host.gui.core.settings import GuiSettings

__all__ = [
    "GuiSignals",
    "RobotController",
    "AppState",
    "ConnectionState",
    "DeviceCapabilities",
    "DARK_THEME",
    "apply_theme",
    "GuiSettings",
]
