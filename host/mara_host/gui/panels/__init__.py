# mara_host/gui/panels/__init__.py
"""
GUI panels for the MARA Control application.

Panels are the main content views accessible via sidebar navigation.
"""

from mara_host.gui.panels.dashboard import DashboardPanel
from mara_host.gui.panels.control import ControlPanel
from mara_host.gui.panels.camera import CameraPanel
from mara_host.gui.panels.commands import CommandsPanel
from mara_host.gui.panels.pinout import PinoutPanel
from mara_host.gui.panels.firmware import FirmwarePanel
from mara_host.gui.panels.config import ConfigPanel
from mara_host.gui.panels.logs import LogsPanel
from mara_host.gui.panels.calibration import CalibrationPanel
from mara_host.gui.panels.testing import TestingPanel
from mara_host.gui.panels.advanced import AdvancedPanel
from mara_host.gui.panels.session import SessionPanel

__all__ = [
    "DashboardPanel",
    "ControlPanel",
    "CameraPanel",
    "CommandsPanel",
    "PinoutPanel",
    "FirmwarePanel",
    "ConfigPanel",
    "LogsPanel",
    "CalibrationPanel",
    "TestingPanel",
    "AdvancedPanel",
    "SessionPanel",
]
