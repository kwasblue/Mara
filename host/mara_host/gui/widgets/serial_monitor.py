# mara_host/gui/widgets/serial_monitor.py
"""
Serial monitor widget for viewing and sending serial data.

Can be embedded in a panel or detached as a standalone window.
"""

import serial
import serial.tools.list_ports
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QLabel,
    QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QTextCursor, QKeyEvent


class SerialReaderThread(QThread):
    """Background thread for reading serial data."""

    data_received = Signal(bytes)
    error = Signal(str)
    connected = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._serial: Optional[serial.Serial] = None
        self._running = False
        self._port = ""
        self._baudrate = 115200

    def configure(self, port: str, baudrate: int = 115200) -> None:
        """Configure serial port settings."""
        self._port = port
        self._baudrate = baudrate

    def run(self) -> None:
        """Read serial data continuously."""
        try:
            self._serial = serial.Serial(
                self._port,
                self._baudrate,
                timeout=0.1,
            )
            self._running = True
            self.connected.emit(True)

            while self._running:
                if self._serial and self._serial.in_waiting:
                    data = self._serial.read(self._serial.in_waiting)
                    if data:
                        self.data_received.emit(data)
                else:
                    self.msleep(10)  # Prevent CPU spinning when no data

        except Exception as e:
            self.error.emit(str(e))

        finally:
            if self._serial:
                self._serial.close()
                self._serial = None
            self.connected.emit(False)

    def stop(self) -> None:
        """Stop reading."""
        self._running = False
        self.wait(2000)

    def write(self, data: bytes) -> bool:
        """Write data to serial port."""
        if self._serial and self._serial.is_open:
            try:
                self._serial.write(data)
                return True
            except Exception:
                pass
        return False


class SerialMonitorWidget(QWidget):
    """
    Serial monitor widget with output display and command input.

    Features:
    - Real-time serial output display
    - Command input with history
    - Auto-scroll toggle
    - Timestamps toggle
    - Clear button
    - Detach to window
    """

    # Signal emitted when detach is requested
    detach_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._reader: Optional[SerialReaderThread] = None
        self._connected = False
        self._auto_scroll = True
        self._show_timestamps = False
        self._command_history: list[str] = []
        self._history_index = -1

        self._setup_ui()
        self._refresh_ports()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        # Port selector
        port_label = QLabel("Port")
        port_label.setStyleSheet("color: #71717A; font-size: 11px;")
        toolbar.addWidget(port_label)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(180)
        toolbar.addWidget(self.port_combo)

        # Baud rate
        baud_label = QLabel("Baud")
        baud_label.setStyleSheet("color: #71717A; font-size: 11px;")
        toolbar.addWidget(baud_label)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self.baud_combo.setCurrentText("115200")
        self.baud_combo.setMaximumWidth(100)
        toolbar.addWidget(self.baud_combo)

        # Refresh ports
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.setMaximumWidth(80)
        refresh_btn.clicked.connect(self._refresh_ports)
        toolbar.addWidget(refresh_btn)

        toolbar.addSpacing(8)

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMaximumWidth(100)
        self.connect_btn.clicked.connect(self._toggle_connection)
        toolbar.addWidget(self.connect_btn)

        toolbar.addStretch()

        # Options
        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        self.autoscroll_check.toggled.connect(self._on_autoscroll_changed)
        toolbar.addWidget(self.autoscroll_check)

        self.timestamp_check = QCheckBox("Timestamps")
        self.timestamp_check.toggled.connect(self._on_timestamp_changed)
        toolbar.addWidget(self.timestamp_check)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondary")
        clear_btn.setMaximumWidth(70)
        clear_btn.clicked.connect(self._clear_output)
        toolbar.addWidget(clear_btn)

        # Detach button
        self.detach_btn = QPushButton("Detach")
        self.detach_btn.setObjectName("secondary")
        self.detach_btn.setMaximumWidth(80)
        self.detach_btn.clicked.connect(self._on_detach)
        toolbar.addWidget(self.detach_btn)

        layout.addLayout(toolbar)

        # Output display
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(10000)
        self.output.setFont(QFont("Menlo", 11))
        self.output.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #111113;"
            "  color: #FAFAFA;"
            "  border: none;"
            "  border-radius: 6px;"
            "  padding: 12px;"
            "}"
        )
        layout.addWidget(self.output, 1)

        # Input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter command...")
        self.input_field.returnPressed.connect(self._send_command)
        self.input_field.installEventFilter(self)
        input_layout.addWidget(self.input_field)

        # Line ending selector
        self.line_ending = QComboBox()
        self.line_ending.addItems(["No line ending", "Newline", "Carriage return", "Both NL & CR"])
        self.line_ending.setCurrentIndex(1)  # Default to newline
        self.line_ending.setMaximumWidth(130)
        input_layout.addWidget(self.line_ending)

        send_btn = QPushButton("Send")
        send_btn.setMaximumWidth(80)
        send_btn.clicked.connect(self._send_command)
        input_layout.addWidget(send_btn)

        layout.addLayout(input_layout)

    def _refresh_ports(self) -> None:
        """Refresh available serial ports."""
        self.port_combo.clear()

        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append((port.device, port.description))

        if not ports:
            self.port_combo.addItem("No ports found")
            self.port_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)
        else:
            self.port_combo.setEnabled(True)
            self.connect_btn.setEnabled(True)
            for device, desc in sorted(ports):
                display = f"{device}"
                if desc and desc != device:
                    display = f"{device} - {desc[:30]}"
                self.port_combo.addItem(display, device)

    def _toggle_connection(self) -> None:
        """Connect or disconnect from serial port."""
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self) -> None:
        """Connect to selected serial port."""
        port = self.port_combo.currentData()
        if not port:
            return

        baudrate = int(self.baud_combo.currentText())

        self._reader = SerialReaderThread(self)
        self._reader.configure(port, baudrate)
        self._reader.data_received.connect(self._on_data_received)
        self._reader.error.connect(self._on_error)
        self._reader.connected.connect(self._on_connected)
        self._reader.start()

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")

    def _disconnect(self) -> None:
        """Disconnect from serial port."""
        if self._reader:
            self._reader.stop()
            self._reader = None

    def _on_connected(self, connected: bool) -> None:
        """Handle connection state change."""
        self._connected = connected
        self.connect_btn.setEnabled(True)

        if connected:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setObjectName("danger")
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self._append_system(f"Connected to {self.port_combo.currentData()}")
        else:
            self.connect_btn.setText("Connect")
            self.connect_btn.setObjectName("")
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self._append_system("Disconnected")

        # Force style refresh
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)

    def _on_data_received(self, data: bytes) -> None:
        """Handle received serial data."""
        try:
            text = data.decode('utf-8', errors='replace')
        except Exception:
            text = data.hex()

        self._append_output(text)

    def _on_error(self, error: str) -> None:
        """Handle serial error."""
        self._append_system(f"Error: {error}")

    def _send_command(self) -> None:
        """Send command to serial port."""
        if not self._connected or not self._reader:
            return

        text = self.input_field.text()
        if not text:
            return

        # Add line ending
        line_ending_idx = self.line_ending.currentIndex()
        if line_ending_idx == 1:  # Newline
            text += "\n"
        elif line_ending_idx == 2:  # Carriage return
            text += "\r"
        elif line_ending_idx == 3:  # Both
            text += "\r\n"

        # Send
        if self._reader.write(text.encode('utf-8')):
            # Add to history
            cmd = self.input_field.text()
            if not self._command_history or self._command_history[-1] != cmd:
                self._command_history.append(cmd)
            self._history_index = len(self._command_history)

            self.input_field.clear()

    def _append_output(self, text: str) -> None:
        """Append text to output."""
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)

        if self._show_timestamps:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            # Insert timestamp at start of each line
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if line or i < len(lines) - 1:
                    if i > 0:
                        cursor.insertText('\n')
                    cursor.insertText(f"[{timestamp}] {line}")
        else:
            cursor.insertText(text)

        if self._auto_scroll:
            self.output.setTextCursor(cursor)
            self.output.ensureCursorVisible()

    def _append_system(self, text: str) -> None:
        """Append system message."""
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)

        timestamp = datetime.now().strftime("%H:%M:%S")
        cursor.insertText(f"\n--- {text} [{timestamp}] ---\n")

        if self._auto_scroll:
            self.output.setTextCursor(cursor)
            self.output.ensureCursorVisible()

    def _clear_output(self) -> None:
        """Clear output display."""
        self.output.clear()

    def _on_autoscroll_changed(self, checked: bool) -> None:
        """Handle auto-scroll toggle."""
        self._auto_scroll = checked

    def _on_timestamp_changed(self, checked: bool) -> None:
        """Handle timestamp toggle."""
        self._show_timestamps = checked

    def _on_detach(self) -> None:
        """Request detachment to window."""
        self.detach_requested.emit()

    def eventFilter(self, obj, event) -> bool:
        """Handle key events for command history."""
        if obj == self.input_field and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key_Up:
                self._history_up()
                return True
            elif event.key() == Qt.Key_Down:
                self._history_down()
                return True
        return super().eventFilter(obj, event)

    def _history_up(self) -> None:
        """Navigate command history up."""
        if self._command_history and self._history_index > 0:
            self._history_index -= 1
            self.input_field.setText(self._command_history[self._history_index])

    def _history_down(self) -> None:
        """Navigate command history down."""
        if self._history_index < len(self._command_history) - 1:
            self._history_index += 1
            self.input_field.setText(self._command_history[self._history_index])
        else:
            self._history_index = len(self._command_history)
            self.input_field.clear()

    def connect_to_port(self, port: str, baudrate: int = 115200) -> None:
        """Programmatically connect to a serial port."""
        if self._connected:
            self._disconnect()

        # Find and select the port in the combo
        for i in range(self.port_combo.count()):
            if self.port_combo.itemData(i) == port:
                self.port_combo.setCurrentIndex(i)
                break
        else:
            # Port not in list, refresh and try again
            self._refresh_ports()
            for i in range(self.port_combo.count()):
                if self.port_combo.itemData(i) == port:
                    self.port_combo.setCurrentIndex(i)
                    break

        # Set baud rate
        self.baud_combo.setCurrentText(str(baudrate))

        # Connect
        self._connect()

    def closeEvent(self, event) -> None:
        """Clean up on close."""
        self._disconnect()
        super().closeEvent(event)


class SerialMonitorWindow(QWidget):
    """Standalone serial monitor window."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)

        self.setWindowTitle("Serial Monitor")
        self.setMinimumSize(700, 500)

        # Apply dark theme
        self.setStyleSheet("""
            QWidget {
                background-color: #18181B;
                color: #FAFAFA;
                font-family: "Helvetica Neue", "Segoe UI", "Inter", sans-serif;
                font-size: 13px;
            }
            QComboBox {
                background-color: #27272A;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QComboBox:focus {
                border-color: #3B82F6;
            }
            QComboBox::drop-down {
                border: none;
                width: 28px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #71717A;
                margin-right: 10px;
            }
            QLineEdit {
                background-color: #27272A;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #3B82F6;
            }
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton#secondary {
                background-color: #27272A;
                color: #FAFAFA;
            }
            QPushButton#secondary:hover {
                background-color: #3F3F46;
            }
            QPushButton#danger {
                background-color: #EF4444;
            }
            QPushButton#danger:hover {
                background-color: #DC2626;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #52525B;
                border-radius: 4px;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #3B82F6;
                border-color: #3B82F6;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        self.monitor = SerialMonitorWidget()
        self.monitor.detach_btn.setVisible(False)  # Hide detach in window mode
        layout.addWidget(self.monitor)

    def closeEvent(self, event) -> None:
        """Clean up on close."""
        self.monitor.closeEvent(event)
        super().closeEvent(event)
