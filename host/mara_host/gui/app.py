# mara_host/gui/app.py
"""
MARA GUI application entry point.

Provides the main application class and run function.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import QApplication

from mara_host.gui.core import GuiSignals, RobotController, apply_theme, GuiSettings
from mara_host.gui.core.dev_mode import set_dev_mode
from mara_host.gui.main_window import MainWindow

# GUI log directory
GUI_LOG_DIR = Path.home() / ".mara" / "logs"


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
        # Always set up file logging for investigation
        self._setup_file_logging()

        # Configure console logging based on dev mode
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
        print("[MaraApp] Creating signals and controller...")
        self._signals = GuiSignals()
        self._controller = RobotController(self._signals, dev_mode=self._dev)

        # Start controller
        print("[MaraApp] Starting controller...")
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

    def _setup_file_logging(self) -> None:
        """
        Set up persistent file logging for investigation.

        Logs are written to ~/.mara/logs/gui_YYYYMMDD_HHMMSS.log
        """
        # Create log directory
        GUI_LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file = GUI_LOG_DIR / f"gui_{timestamp}.log"

        # Set up file handler
        file_handler = logging.FileHandler(self._log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.DEBUG)

        # Also capture print statements to log file
        self._setup_print_capture()

        # Create/update "latest" symlink for easy access
        latest_link = GUI_LOG_DIR / "gui_latest.log"
        try:
            if latest_link.is_symlink() or latest_link.exists():
                latest_link.unlink()
            latest_link.symlink_to(self._log_file.name)
        except OSError:
            pass  # Symlinks may not work on all platforms

        # Clean up old logs (keep last 10)
        self._cleanup_old_logs(keep=10)

        print(f"[GUI] Log file: {self._log_file}")
        print(f"[GUI] Latest log symlink: {latest_link}")

    def _cleanup_old_logs(self, keep: int = 10) -> None:
        """Remove old log files, keeping the most recent ones."""
        try:
            log_files = sorted(
                GUI_LOG_DIR.glob("gui_*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            # Skip symlinks and keep the most recent files
            regular_files = [f for f in log_files if not f.is_symlink()]
            for old_log in regular_files[keep:]:
                try:
                    old_log.unlink()
                except OSError:
                    pass
        except Exception:
            pass  # Don't fail startup for cleanup issues

    def _setup_print_capture(self) -> None:
        """Capture print statements to log file."""
        import io

        class TeeWriter(io.TextIOBase):
            """Write to both original stream and log file."""
            def __init__(self, original, log_file):
                self.original = original
                self.log_file = open(log_file, "a", encoding="utf-8")

            def write(self, s):
                self.original.write(s)
                self.log_file.write(s)
                self.log_file.flush()
                return len(s)

            def flush(self):
                self.original.flush()
                self.log_file.flush()

        sys.stdout = TeeWriter(sys.__stdout__, self._log_file)
        sys.stderr = TeeWriter(sys.__stderr__, self._log_file)

    def _setup_dev_logging(self) -> None:
        """Configure verbose logging for dev mode."""
        # Clear any existing handlers on root logger to prevent duplicates
        root_logger = logging.getLogger()
        # Only clear console handlers, keep file handler
        root_logger.handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]

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
