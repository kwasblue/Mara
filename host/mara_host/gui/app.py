# mara_host/gui/app.py
"""
MARA GUI application entry point.

Provides the main application class and run function.
"""

import sys
import logging
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController, apply_theme, GuiSettings
from mara_host.gui.core.dev_mode import set_dev_mode
from mara_host.gui.main_window import MainWindow


class MaraApplication:
    """
    MARA GUI Application.

    Manages the Qt application lifecycle, robot controller,
    and main window.

    Example:
        app = MaraApplication()
        app.run()

        # Or with pre-configured connection
        app = MaraApplication(port="/dev/cu.usbserial-0001")
        app.run()
    """

    def __init__(
        self,
        port: Optional[str] = None,
        host: Optional[str] = None,
        tcp_port: Optional[int] = None,
        dev: bool = False,
    ):
        """
        Initialize the MARA application.

        Args:
            port: Serial port to connect to on startup
            host: TCP host to connect to on startup
            tcp_port: TCP port to use (default 3333)
            dev: Enable dev mode with verbose logging
        """
        self._port = port
        self._host = host
        self._tcp_port = tcp_port or 3333
        self._dev = dev

        self._app: Optional[QApplication] = None
        self._signals: Optional[GuiSignals] = None
        self._controller: Optional[RobotController] = None
        self._window: Optional[MainWindow] = None

        # Set global dev mode flag
        set_dev_mode(dev)

    def run(self) -> int:
        """
        Run the application.

        Returns:
            Exit code
        """
        # Configure logging based on dev mode
        if self._dev:
            self._setup_dev_logging()

        # Create Qt application
        self._app = QApplication(sys.argv)
        self._app.setApplicationName("MARA Control")
        self._app.setOrganizationName("MARA")
        self._app.setStyle("Fusion")

        # Apply theme
        apply_theme(self._app)

        # Create core components
        self._signals = GuiSignals()
        self._controller = RobotController(self._signals, dev_mode=self._dev)

        # Start controller
        self._controller.start()

        # Create main window
        self._window = MainWindow(self._signals, self._controller, dev_mode=self._dev)
        self._window.show()

        if self._dev:
            self._signals.log_info("[DEV MODE] Verbose logging enabled")

        # Auto-connect if configured
        if self._port:
            settings = GuiSettings()
            baudrate = settings.get_baudrate()
            self._controller.connect_serial(self._port, baudrate)
        elif self._host:
            self._controller.connect_tcp(self._host, self._tcp_port)

        # Run event loop
        return self._app.exec()

    def _setup_dev_logging(self) -> None:
        """Configure verbose logging for dev mode."""
        # Clear any existing handlers on root logger to prevent duplicates
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # Set up single console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-5s] %(message)s",
            datefmt="%H:%M:%S",
        ))
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)

        # Enable debug logging for mara_host modules (without propagation to avoid dupes)
        for logger_name in ["mara_host", "mara", "MaraClient"]:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)

        print("[DEV MODE] Verbose console logging enabled")


def run_app(
    port: Optional[str] = None,
    host: Optional[str] = None,
    tcp_port: Optional[int] = None,
    dev: bool = False,
) -> int:
    """
    Run the MARA GUI application.

    Args:
        port: Serial port to connect to on startup
        host: TCP host to connect to on startup
        tcp_port: TCP port (default 3333)
        dev: Enable dev mode with verbose logging

    Returns:
        Exit code
    """
    app = MaraApplication(port=port, host=host, tcp_port=tcp_port, dev=dev)
    return app.run()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="MARA Control GUI")
    parser.add_argument(
        "--port",
        "-p",
        help="Serial port to connect to",
    )
    parser.add_argument(
        "--host",
        "-H",
        help="TCP host to connect to",
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=3333,
        help="TCP port (default: 3333)",
    )
    parser.add_argument(
        "--dev",
        "-d",
        action="store_true",
        help="Enable dev mode with verbose logging",
    )

    args = parser.parse_args()

    sys.exit(run_app(port=args.port, host=args.host, tcp_port=args.tcp_port, dev=args.dev))


if __name__ == "__main__":
    main()
