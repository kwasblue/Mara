# mara_host/gui/panels/firmware.py
"""
Firmware panel for building and uploading ESP32 firmware.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "firmware",
    "label": "Firmware",
    "order": 110,
}

import subprocess
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QPlainTextEdit,
    QProgressBar,
    QCheckBox,
    QTabWidget,
)
from PySide6.QtCore import Qt, QThread, Signal

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.gui.widgets.serial_monitor import SerialMonitorWidget, SerialMonitorWindow


class BuildWorker(QThread):
    """Worker thread for running builds."""

    output = Signal(str)
    finished = Signal(bool, str)  # success, message

    def __init__(
        self,
        command: list[str],
        cwd: Path,
        parent=None,
    ):
        super().__init__(parent)
        self.command = command
        self.cwd = cwd
        self._process: Optional[subprocess.Popen] = None

    def run(self):
        """Run the build command."""
        try:
            self._process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for line in iter(self._process.stdout.readline, ''):
                if line:
                    self.output.emit(line.rstrip())

            self._process.wait()

            if self._process.returncode == 0:
                self.finished.emit(True, "Success")
            else:
                self.finished.emit(False, f"Failed with code {self._process.returncode}")

        except Exception as e:
            self.finished.emit(False, str(e))

    def stop(self):
        """Stop the build process."""
        if self._process:
            self._process.terminate()


class FirmwarePanel(QWidget):
    """
    Firmware panel for build and upload operations.

    Layout:
        +--------------------------------------------------+
        | Build                                            |
        | Environment: [esp32_full v] [ ] Generate first   |
        | [Build]  [Clean]                                 |
        +--------------------------------------------------+
        | Upload                                           |
        | Port: [/dev/cu.usb... v] [Refresh]              |
        | [Upload]  [ ] Erase first                        |
        +--------------------------------------------------+
        | Output                                           |
        | +----------------------------------------------+ |
        | | Build output log...                          | |
        | |                                              | |
        | +----------------------------------------------+ |
        | [============================] 45%               |
        +--------------------------------------------------+
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

        self._worker: Optional[BuildWorker] = None
        self._mcu_project = self._find_mcu_project()
        self._serial_window: Optional[SerialMonitorWindow] = None

        self._setup_ui()
        self._refresh_ports()
        self._setup_connections()

    def _find_mcu_project(self) -> Path:
        """Find the MCU project directory."""
        # Try relative to this file
        gui_dir = Path(__file__).parent.parent
        host_dir = gui_dir.parent.parent
        repo_root = host_dir.parent

        mcu_path = repo_root / "firmware" / "mcu"
        if mcu_path.exists():
            return mcu_path

        # Fallback - try from build_firmware module
        try:
            from mara_host.tools.build_firmware import MCU_PROJECT
            return MCU_PROJECT
        except ImportError:
            return Path.cwd()

    def _setup_ui(self) -> None:
        """Set up the firmware panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Build section
        layout.addWidget(self._create_build_section())

        # Upload section
        layout.addWidget(self._create_upload_section())

        # Tabbed output section
        self.output_tabs = QTabWidget()

        # Build output tab
        build_output_widget = self._create_output_section()
        self.output_tabs.addTab(build_output_widget, "Build Output")

        # Serial monitor tab
        self.serial_monitor = SerialMonitorWidget()
        self.serial_monitor.detach_requested.connect(self._detach_serial_monitor)
        self.output_tabs.addTab(self.serial_monitor, "Serial Monitor")

        layout.addWidget(self.output_tabs, 1)

    def _create_build_section(self) -> QGroupBox:
        """Create the build controls."""
        group = QGroupBox("Build Firmware")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Environment row
        env_layout = QHBoxLayout()
        env_layout.setSpacing(12)

        env_label = QLabel("Environment")
        env_label.setStyleSheet("color: #5C5C6E; font-size: 11px;")
        env_layout.addWidget(env_label)

        self.env_combo = QComboBox()
        self.env_combo.setMinimumWidth(180)
        self._populate_environments()
        env_layout.addWidget(self.env_combo)

        env_layout.addSpacing(16)

        self.generate_check = QCheckBox("Generate code first")
        self.generate_check.setToolTip("Run code generators before building")
        env_layout.addWidget(self.generate_check)

        env_layout.addStretch()

        layout.addLayout(env_layout)

        # Buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.build_btn = QPushButton("Build")
        self.build_btn.setMinimumWidth(100)
        self.build_btn.clicked.connect(self._on_build)
        btn_layout.addWidget(self.build_btn)

        self.clean_btn = QPushButton("Clean")
        self.clean_btn.setObjectName("secondary")
        self.clean_btn.setMinimumWidth(80)
        self.clean_btn.clicked.connect(self._on_clean)
        btn_layout.addWidget(self.clean_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.setMinimumWidth(80)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        btn_layout.addStretch()

        # Size info
        self.size_label = QLabel("")
        self.size_label.setStyleSheet(
            "color: #5C5C6E; "
            "font-size: 11px; "
            "font-family: 'Menlo', monospace;"
        )
        btn_layout.addWidget(self.size_label)

        layout.addLayout(btn_layout)

        return group

    def _create_upload_section(self) -> QGroupBox:
        """Create the upload controls."""
        group = QGroupBox("Upload to Device")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Port row
        port_layout = QHBoxLayout()
        port_layout.setSpacing(12)

        port_label = QLabel("Port")
        port_label.setStyleSheet("color: #5C5C6E; font-size: 11px;")
        port_layout.addWidget(port_label)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(220)
        port_layout.addWidget(self.port_combo)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.setMaximumWidth(80)
        refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addWidget(refresh_btn)

        port_layout.addSpacing(16)

        self.erase_check = QCheckBox("Erase flash first")
        self.erase_check.setToolTip("Erase all flash memory before uploading")
        port_layout.addWidget(self.erase_check)

        port_layout.addStretch()

        layout.addLayout(port_layout)

        # Buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.upload_btn = QPushButton("Upload")
        self.upload_btn.setMinimumWidth(100)
        self.upload_btn.clicked.connect(self._on_upload)
        btn_layout.addWidget(self.upload_btn)

        self.build_upload_btn = QPushButton("Build + Upload")
        self.build_upload_btn.setMinimumWidth(120)
        self.build_upload_btn.clicked.connect(self._on_build_upload)
        btn_layout.addWidget(self.build_upload_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        return group

    def _create_output_section(self) -> QGroupBox:
        """Create the output log section."""
        group = QGroupBox("Output")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Output log
        self.output_log = QPlainTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMaximumBlockCount(5000)  # Limit lines
        self.output_log.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "font-size: 11px; "
            "line-height: 1.4;"
        )
        layout.addWidget(self.output_log)

        # Progress bar
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(12)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #5C5C6E; font-size: 11px;")
        self.status_label.setMinimumWidth(100)
        progress_layout.addWidget(self.status_label)

        layout.addLayout(progress_layout)

        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.setObjectName("flat")
        clear_btn.clicked.connect(self.output_log.clear)
        layout.addWidget(clear_btn, 0, Qt.AlignRight)

        return group

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        # Auto-connect serial monitor when robot connects via serial
        self.signals.serial_port_selected.connect(self._on_serial_port_selected)

    def _on_serial_port_selected(self, port: str, baudrate: int) -> None:
        """Handle serial port selection from another panel."""
        # Connect the serial monitor to the same port
        if hasattr(self, 'serial_monitor') and self.serial_monitor:
            self.serial_monitor.connect_to_port(port, baudrate)

            # Switch to serial monitor tab
            idx = self.output_tabs.indexOf(self.serial_monitor)
            if idx >= 0:
                self.output_tabs.setCurrentIndex(idx)

        # Also connect detached window if open
        if self._serial_window:
            self._serial_window.monitor.connect_to_port(port, baudrate)

    def _populate_environments(self) -> None:
        """Populate environment dropdown."""
        try:
            from mara_host.services.build.firmware_service import FirmwareBuildService
            envs = FirmwareBuildService.get_available_environments()
        except ImportError:
            envs = {
                "esp32_minimal",
                "esp32_motors",
                "esp32_sensors",
                "esp32_control",
                "esp32_full",
                "esp32_usb",
                "esp32_ota",
            }

        # Sort with common ones first
        priority = ["esp32_usb", "esp32_full", "esp32_control", "esp32_motors"]
        sorted_envs = []

        for env in priority:
            if env in envs:
                sorted_envs.append(env)

        for env in sorted(envs):
            if env not in sorted_envs:
                sorted_envs.append(env)

        self.env_combo.clear()
        self.env_combo.addItems(sorted_envs)

        # Default to esp32_usb
        idx = self.env_combo.findText("esp32_usb")
        if idx >= 0:
            self.env_combo.setCurrentIndex(idx)

    def _refresh_ports(self) -> None:
        """Refresh available serial ports."""
        self.port_combo.clear()

        ports = self._find_esp32_ports()

        if not ports:
            self.port_combo.addItem("No devices found")
            self.port_combo.setEnabled(False)
            self.upload_btn.setEnabled(False)
            self.build_upload_btn.setEnabled(False)
        else:
            self.port_combo.setEnabled(True)
            self.upload_btn.setEnabled(True)
            self.build_upload_btn.setEnabled(True)

            for p in ports:
                display = f"{p['port']} ({p.get('chip', 'Unknown')})"
                self.port_combo.addItem(display, p['port'])

    def _find_esp32_ports(self) -> list[dict]:
        """Find ESP32 serial ports."""
        ports = []

        try:
            import serial.tools.list_ports
            for port in serial.tools.list_ports.comports():
                is_esp32 = False
                chip_type = "Unknown"

                desc = (port.description or "").lower()
                hwid = (port.hwid or "").lower()

                if "cp210" in desc or "cp210" in hwid:
                    is_esp32 = True
                    chip_type = "CP2102"
                elif "ch340" in desc or "ch340" in hwid:
                    is_esp32 = True
                    chip_type = "CH340"
                elif "ftdi" in desc or "ftdi" in hwid:
                    is_esp32 = True
                    chip_type = "FTDI"
                elif "usb" in desc and "serial" in desc:
                    is_esp32 = True
                    chip_type = "USB Serial"

                if is_esp32:
                    ports.append({
                        "port": port.device,
                        "description": port.description,
                        "chip": chip_type,
                    })

        except ImportError:
            # Fallback detection
            import glob
            if sys.platform == "darwin":
                for p in glob.glob("/dev/cu.usbserial-*") + glob.glob("/dev/cu.SLAB_USBtoUART*"):
                    ports.append({"port": p, "chip": "USB Serial"})
            elif sys.platform == "linux":
                for p in glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"):
                    ports.append({"port": p, "chip": "USB Serial"})

        return ports

    def _on_build(self) -> None:
        """Handle build button click."""
        if self._worker and self._worker.isRunning():
            return

        env = self.env_combo.currentText()
        generate = self.generate_check.isChecked()

        self._log(f"Building {env}...")
        self._set_building(True)
        self.progress_bar.setValue(0)

        # Build command (use Python -m for cross-platform compatibility)
        cmd = [sys.executable, "-m", "platformio", "run", "-e", env]

        if generate:
            # Run generators first
            self._log("Running code generators...")
            try:
                from mara_host.tools.generate_all import main as generate_main
                generate_main()
                self._log("Code generation complete")
            except Exception as e:
                self._log(f"Generator error: {e}")

        self._run_command(cmd, "Build")

    def _on_clean(self) -> None:
        """Handle clean button click."""
        if self._worker and self._worker.isRunning():
            return

        env = self.env_combo.currentText()
        self._log(f"Cleaning {env}...")
        self._set_building(True)

        cmd = [sys.executable, "-m", "platformio", "run", "-e", env, "-t", "clean"]
        self._run_command(cmd, "Clean")

    def _on_upload(self) -> None:
        """Handle upload button click."""
        if self._worker and self._worker.isRunning():
            return

        port = self.port_combo.currentData()
        if not port:
            self._log("No port selected")
            return

        env = self.env_combo.currentText()
        erase = self.erase_check.isChecked()

        if erase:
            self._log("Erasing flash...")
            # Would run esptool erase first

        self._log(f"Uploading to {port}...")
        self._set_building(True)

        cmd = [sys.executable, "-m", "platformio", "run", "-e", env, "-t", "upload", "--upload-port", port]
        self._run_command(cmd, "Upload")

    def _on_build_upload(self) -> None:
        """Handle build + upload button click."""
        if self._worker and self._worker.isRunning():
            return

        port = self.port_combo.currentData()
        if not port:
            self._log("No port selected")
            return

        env = self.env_combo.currentText()
        generate = self.generate_check.isChecked()

        self._log(f"Building and uploading {env} to {port}...")
        self._set_building(True)

        if generate:
            self._log("Running code generators...")
            try:
                from mara_host.tools.generate_all import main as generate_main
                generate_main()
                self._log("Code generation complete")
            except Exception as e:
                self._log(f"Generator error: {e}")

        # Build and upload in one command
        cmd = [sys.executable, "-m", "platformio", "run", "-e", env, "-t", "upload", "--upload-port", port]
        self._run_command(cmd, "Build + Upload")

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self._worker:
            self._log("Cancelling...")
            self._worker.stop()

    def _run_command(self, cmd: list[str], operation: str) -> None:
        """Run a PlatformIO command in a worker thread."""
        self._worker = BuildWorker(cmd, self._mcu_project)
        self._worker.output.connect(self._on_output)
        self._worker.finished.connect(
            lambda ok, msg: self._on_finished(ok, msg, operation)
        )
        self._worker.start()

    def _on_output(self, line: str) -> None:
        """Handle build output line."""
        self._log(line)

        # Parse progress from output
        if "Compiling" in line:
            self.progress_bar.setValue(30)
            self.status_label.setText("Compiling...")
        elif "Linking" in line:
            self.progress_bar.setValue(60)
            self.status_label.setText("Linking...")
        elif "Building" in line:
            self.progress_bar.setValue(80)
            self.status_label.setText("Building binary...")
        elif "Uploading" in line:
            self.progress_bar.setValue(90)
            self.status_label.setText("Uploading...")
        elif "SUCCESS" in line.upper():
            self.progress_bar.setValue(100)

    def _on_finished(self, success: bool, message: str, operation: str) -> None:
        """Handle build completion."""
        self._set_building(False)

        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Complete")
            self.status_label.setStyleSheet("color: #34A853; font-size: 11px;")
            self._log(f"{operation} completed successfully")
            self.signals.status_message.emit(f"{operation} successful")

            # Update size info
            self._update_size_info()
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText("Failed")
            self.status_label.setStyleSheet("color: #DC2626; font-size: 11px;")
            self._log(f"{operation} failed: {message}")
            self.signals.status_error.emit(f"{operation} failed")

    def _update_size_info(self) -> None:
        """Update firmware size display."""
        try:
            from mara_host.services.build.firmware_service import FirmwareBuildService
            service = FirmwareBuildService(self._mcu_project)
            size = service.get_size(self.env_combo.currentText())

            if size:
                self.size_label.setText(
                    f"Flash: {size.flash_used // 1024}KB ({size.flash_percent:.1f}%)  "
                    f"RAM: {size.ram_used // 1024}KB ({size.ram_percent:.1f}%)"
                )
        except Exception:
            pass

    def _set_building(self, building: bool) -> None:
        """Update UI state for building."""
        self.build_btn.setEnabled(not building)
        self.clean_btn.setEnabled(not building)
        self.upload_btn.setEnabled(not building)
        self.build_upload_btn.setEnabled(not building)
        self.cancel_btn.setVisible(building)

        if building:
            self.status_label.setText("Working...")
            self.status_label.setStyleSheet("color: #F59E0B; font-size: 11px;")

    def _log(self, message: str) -> None:
        """Add message to output log."""
        self.output_log.appendPlainText(message)
        # Auto-scroll to bottom
        scrollbar = self.output_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _detach_serial_monitor(self) -> None:
        """Detach the serial monitor to its own window."""
        if self._serial_window is not None:
            # Already detached, bring to front
            self._serial_window.raise_()
            self._serial_window.activateWindow()
            return

        # Create new window
        self._serial_window = SerialMonitorWindow()
        self._serial_window.setWindowTitle("Serial Monitor")

        # Handle window close - allow re-detaching
        self._serial_window.destroyed.connect(self._on_serial_window_closed)

        # Show the window
        self._serial_window.show()

        # Hide the embedded serial monitor tab
        idx = self.output_tabs.indexOf(self.serial_monitor)
        if idx >= 0:
            self.output_tabs.removeTab(idx)

    def _on_serial_window_closed(self) -> None:
        """Handle serial monitor window being closed."""
        self._serial_window = None

        # Re-add the embedded serial monitor tab
        self.serial_monitor = SerialMonitorWidget()
        self.serial_monitor.detach_requested.connect(self._detach_serial_monitor)
        self.output_tabs.addTab(self.serial_monitor, "Serial Monitor")

    def closeEvent(self, event) -> None:
        """Clean up on panel close."""
        # Close serial window if open
        if self._serial_window is not None:
            self._serial_window.close()
            self._serial_window = None

        # Stop any running worker
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)

        # Clean up embedded serial monitor
        if hasattr(self, 'serial_monitor'):
            self.serial_monitor.closeEvent(event)

        super().closeEvent(event)
