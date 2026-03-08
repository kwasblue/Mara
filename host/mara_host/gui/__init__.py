# mara_host/gui/__init__.py
"""
MARA Control GUI - PySide6 Desktop Application.

Provides an operator dashboard, development/debug tool, and configuration UI.

Architecture:
    - gui/core/      Core components (signals, controller, state, theme)
    - gui/panels/    Main panel views (dashboard, control, camera, etc.)
    - gui/widgets/   Reusable widget components

Example:
    from mara_host.gui import run_app

    # Launch the GUI
    run_app()

    # Or with pre-configured transport
    run_app(port="/dev/cu.usbserial-0001")

Dependencies:
    - PySide6>=6.5.0
    - pyqtgraph>=0.13.0 (for telemetry plots)
"""

from mara_host.gui.app import run_app, MaraApplication

__all__ = [
    "run_app",
    "MaraApplication",
]
