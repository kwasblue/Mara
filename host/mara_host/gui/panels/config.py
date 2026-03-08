# mara_host/gui/panels/config.py
"""
Configuration panel for robot and transport settings.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QFormLayout,
    QTabWidget,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings


class ConfigPanel(QWidget):
    """
    Configuration panel for settings.

    Tabs:
        - Connection: Transport settings
        - Telemetry: Update rates, history
        - Control: Velocity limits
        - Camera: Stream settings
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
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the config panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Tab widget
        tabs = QTabWidget()

        tabs.addTab(self._create_connection_tab(), "Connection")
        tabs.addTab(self._create_telemetry_tab(), "Telemetry")
        tabs.addTab(self._create_control_tab(), "Control")
        tabs.addTab(self._create_camera_tab(), "Camera")

        layout.addWidget(tabs)

        # Save button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _create_connection_tab(self) -> QWidget:
        """Create connection settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # Serial settings
        serial_group = QGroupBox("Serial Connection")
        serial_layout = QFormLayout(serial_group)

        self.default_port = QLineEdit()
        self.default_port.setPlaceholderText("/dev/cu.usbserial-0001")
        serial_layout.addRow("Default Port:", self.default_port)

        self.baudrate = QComboBox()
        self.baudrate.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800"])
        self.baudrate.setCurrentText("115200")
        serial_layout.addRow("Baud Rate:", self.baudrate)

        layout.addWidget(serial_group)

        # TCP settings
        tcp_group = QGroupBox("TCP Connection")
        tcp_layout = QFormLayout(tcp_group)

        self.tcp_host = QLineEdit()
        self.tcp_host.setPlaceholderText("192.168.4.1")
        tcp_layout.addRow("Default Host:", self.tcp_host)

        self.tcp_port = QSpinBox()
        self.tcp_port.setRange(1, 65535)
        self.tcp_port.setValue(3333)
        tcp_layout.addRow("Port:", self.tcp_port)

        layout.addWidget(tcp_group)

        layout.addStretch()
        return widget

    def _create_telemetry_tab(self) -> QWidget:
        """Create telemetry settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        group = QGroupBox("Telemetry Settings")
        form = QFormLayout(group)

        self.telem_interval = QSpinBox()
        self.telem_interval.setRange(10, 1000)
        self.telem_interval.setValue(50)
        self.telem_interval.setSuffix(" ms")
        form.addRow("Update Interval:", self.telem_interval)

        self.plot_history = QSpinBox()
        self.plot_history.setRange(50, 1000)
        self.plot_history.setValue(200)
        self.plot_history.setSuffix(" samples")
        form.addRow("Plot History:", self.plot_history)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _create_control_tab(self) -> QWidget:
        """Create control settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        group = QGroupBox("Velocity Limits")
        form = QFormLayout(group)

        self.max_linear = QDoubleSpinBox()
        self.max_linear.setRange(0.1, 10.0)
        self.max_linear.setValue(1.0)
        self.max_linear.setSingleStep(0.1)
        self.max_linear.setSuffix(" m/s")
        form.addRow("Max Linear Velocity:", self.max_linear)

        self.max_angular = QDoubleSpinBox()
        self.max_angular.setRange(0.1, 20.0)
        self.max_angular.setValue(2.0)
        self.max_angular.setSingleStep(0.1)
        self.max_angular.setSuffix(" rad/s")
        form.addRow("Max Angular Velocity:", self.max_angular)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _create_camera_tab(self) -> QWidget:
        """Create camera settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        group = QGroupBox("Camera Settings")
        form = QFormLayout(group)

        self.camera_url = QLineEdit()
        self.camera_url.setPlaceholderText("http://10.0.0.60")
        form.addRow("Camera URL:", self.camera_url)

        self.camera_resolution = QComboBox()
        self.camera_resolution.addItems([
            "QVGA (320x240)",
            "VGA (640x480)",
            "SVGA (800x600)",
            "XGA (1024x768)",
        ])
        self.camera_resolution.setCurrentIndex(1)  # VGA
        form.addRow("Resolution:", self.camera_resolution)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _load_settings(self) -> None:
        """Load settings into UI."""
        # Connection
        self.default_port.setText(self.settings.get_last_port())
        self.baudrate.setCurrentText(str(self.settings.get_baudrate()))
        self.tcp_host.setText(self.settings.get_last_host())
        self.tcp_port.setValue(self.settings.get_last_tcp_port())

        # Telemetry
        self.telem_interval.setValue(self.settings.get_telemetry_interval())
        self.plot_history.setValue(self.settings.get_plot_history_size())

        # Control
        self.max_linear.setValue(self.settings.get_max_linear_velocity())
        self.max_angular.setValue(self.settings.get_max_angular_velocity())

        # Camera
        self.camera_url.setText(self.settings.get_camera_url())

    def _save_settings(self) -> None:
        """Save settings from UI."""
        # Connection
        if self.default_port.text():
            self.settings.set_last_port(self.default_port.text())
        self.settings.set_baudrate(int(self.baudrate.currentText()))
        if self.tcp_host.text():
            self.settings.set_last_host(self.tcp_host.text())
        self.settings.set_last_tcp_port(self.tcp_port.value())

        # Telemetry
        self.settings.set_telemetry_interval(self.telem_interval.value())
        self.settings.set_plot_history_size(self.plot_history.value())

        # Control
        self.settings.set_max_linear_velocity(self.max_linear.value())
        self.settings.set_max_angular_velocity(self.max_angular.value())

        # Camera
        if self.camera_url.text():
            self.settings.set_camera_url(self.camera_url.text())

        self.settings.sync()
        self.signals.status_message.emit("Settings saved")
