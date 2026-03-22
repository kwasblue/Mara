# mara_host/gui/panels/dashboard.py
"""
Dashboard panel for telemetry overview and quick actions.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "dashboard",
    "label": "Dashboard",
    "order": 10,
}

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QFrame,
    QSplitter,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.gui.core.state import DeviceCapabilities
from mara_host.gui.widgets.telemetry_plot import ImuPlotWidget, GyroPlotWidget


class DashboardPanel(QWidget):
    """
    Dashboard panel showing connection, state, and telemetry overview.

    Layout:
        ┌─────────────────────────────────────────────────────┐
        │ [Transport ▼] [Port/Host____] [Connect]            │
        ├─────────────────────────────────────────────────────┤
        │ State: [IDLE] → [ARM] → [ARMED] → [ACTIVE]        │
        ├────────────────────────┬────────────────────────────┤
        │ Telemetry Plots        │ System Info               │
        │ ┌────────────────────┐ │ FW: v1.2.3               │
        │ │ (pyqtgraph plots)  │ │ Protocol: 5              │
        │ └────────────────────┘ │ Uptime: 00:12:34         │
        └────────────────────────┴────────────────────────────┘
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
        self._setup_connections()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Connection bar
        layout.addWidget(self._create_connection_bar())

        # State machine visualization
        layout.addWidget(self._create_state_bar())

        # Main content area
        content = QHBoxLayout()
        content.setSpacing(16)

        # Left: Telemetry plots (give more space)
        self._telemetry_group = self._create_telemetry_section()
        content.addWidget(self._telemetry_group, 3)

        # Right: System info and quick actions (narrower)
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)
        self._system_group = self._create_system_info()
        right_panel.addWidget(self._system_group)
        self._actions_group = self._create_quick_actions()
        right_panel.addWidget(self._actions_group)
        right_panel.addStretch()

        right_container = QWidget()
        right_container.setMaximumWidth(260)
        right_container.setLayout(right_panel)
        content.addWidget(right_container)

        layout.addLayout(content, 1)

    def _create_connection_bar(self) -> QGroupBox:
        """Create the connection controls."""
        group = QGroupBox("Connection")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Transport type
        transport_label = QLabel("Transport")
        transport_label.setStyleSheet("color: #5C5C6E; font-size: 11px;")
        layout.addWidget(transport_label)

        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["Serial", "TCP"])
        self.transport_combo.setMinimumWidth(90)
        self.transport_combo.currentIndexChanged.connect(self._on_transport_changed)
        layout.addWidget(self.transport_combo)

        layout.addSpacing(8)

        # Serial port dropdown (visible when Serial selected)
        self.port_label = QLabel("Port")
        self.port_label.setStyleSheet("color: #5C5C6E; font-size: 11px;")
        layout.addWidget(self.port_label)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(220)
        layout.addWidget(self.port_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("secondary")
        self.refresh_btn.setMaximumWidth(80)
        self.refresh_btn.clicked.connect(self._refresh_ports)
        layout.addWidget(self.refresh_btn)

        # Baud rate selector (visible when Serial selected)
        self.baud_label = QLabel("Baud")
        self.baud_label.setStyleSheet("color: #5C5C6E; font-size: 11px;")
        layout.addWidget(self.baud_label)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["115200", "921600", "57600", "38400", "19200", "9600"])
        self.baud_combo.setMinimumWidth(90)
        layout.addWidget(self.baud_combo)

        # TCP host input (hidden by default)
        self.host_label = QLabel("Host")
        self.host_label.setStyleSheet("color: #5C5C6E; font-size: 11px;")
        self.host_label.setVisible(False)
        layout.addWidget(self.host_label)

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("192.168.4.1")
        self.host_input.setMinimumWidth(150)
        self.host_input.setVisible(False)
        layout.addWidget(self.host_input)

        # TCP port (hidden by default)
        self.tcp_port_label = QLabel("Port")
        self.tcp_port_label.setStyleSheet("color: #5C5C6E; font-size: 11px;")
        self.tcp_port_label.setVisible(False)
        layout.addWidget(self.tcp_port_label)

        self.tcp_port_input = QLineEdit()
        self.tcp_port_input.setText("3333")
        self.tcp_port_input.setMaximumWidth(70)
        self.tcp_port_input.setVisible(False)
        layout.addWidget(self.tcp_port_input)

        layout.addStretch()

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumWidth(100)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_btn)

        return group

    def _create_state_bar(self) -> QGroupBox:
        """Create the state machine visualization."""
        group = QGroupBox("State")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # State labels - minimal pills
        states = ["IDLE", "ARMED", "ACTIVE"]
        self.state_labels = {}

        for i, state in enumerate(states):
            if i > 0:
                arrow = QLabel("-")
                arrow.setStyleSheet("color: #52525B; padding: 0 4px;")
                layout.addWidget(arrow)

            label = QLabel(state)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(
                "background-color: #27272A; "
                "color: #71717A; "
                "padding: 4px 10px; "
                "border-radius: 4px; "
                "font-size: 10px; "
                "font-weight: 500;"
            )
            self.state_labels[state] = label
            layout.addWidget(label)

        layout.addStretch()

        # State control buttons - cleaner labels
        self.arm_btn = QPushButton("Arm")
        self.arm_btn.setObjectName("success")
        self.arm_btn.setMinimumWidth(70)
        self.arm_btn.clicked.connect(self.controller.arm)
        layout.addWidget(self.arm_btn)

        self.activate_btn = QPushButton("Activate")
        self.activate_btn.setMinimumWidth(85)
        self.activate_btn.clicked.connect(self.controller.activate)
        layout.addWidget(self.activate_btn)

        self.disarm_btn = QPushButton("Disarm")
        self.disarm_btn.setObjectName("secondary")
        self.disarm_btn.setMinimumWidth(80)
        self.disarm_btn.clicked.connect(self.controller.disarm)
        layout.addWidget(self.disarm_btn)

        self.estop_btn = QPushButton("Stop")
        self.estop_btn.setObjectName("danger")
        self.estop_btn.setMinimumWidth(70)
        self.estop_btn.clicked.connect(self.controller.estop)
        layout.addWidget(self.estop_btn)

        self.clear_estop_btn = QPushButton("Clear Stop")
        self.clear_estop_btn.setObjectName("warning")
        self.clear_estop_btn.setMinimumWidth(100)
        self.clear_estop_btn.clicked.connect(self.controller.clear_estop)
        self.clear_estop_btn.setVisible(False)
        layout.addWidget(self.clear_estop_btn)

        return group

    def _create_telemetry_section(self) -> QGroupBox:
        """Create the telemetry display section."""
        group = QGroupBox("Telemetry")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 16, 12, 12)

        # Compact numeric displays row
        numeric_frame = QFrame()
        numeric_layout = QHBoxLayout(numeric_frame)
        numeric_layout.setContentsMargins(0, 0, 0, 0)
        numeric_layout.setSpacing(16)

        # IMU numeric display - compact single row
        self.imu_labels = {}
        axes = ["ax", "ay", "az", "gx", "gy", "gz"]
        axis_names = ["aX", "aY", "aZ", "gX", "gY", "gZ"]

        for key, name in zip(axes, axis_names):
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #52525B; font-size: 9px;")
            numeric_layout.addWidget(name_label)

            value_label = QLabel("0.0")
            value_label.setStyleSheet(
                "font-family: 'Menlo', monospace; "
                "color: #A1A1AA; "
                "font-size: 10px; "
                "min-width: 35px;"
            )
            self.imu_labels[key] = value_label
            numeric_layout.addWidget(value_label)

        # Encoder display
        self.encoder_labels = {}
        for i in range(2):
            lbl = QLabel(f"E{i}")
            lbl.setStyleSheet("color: #52525B; font-size: 9px;")
            numeric_layout.addWidget(lbl)

            label = QLabel("0")
            label.setStyleSheet(
                "font-family: 'Menlo', monospace; "
                "color: #A1A1AA; "
                "font-size: 10px; "
                "min-width: 40px;"
            )
            self.encoder_labels[i] = label
            numeric_layout.addWidget(label)

        numeric_layout.addStretch()
        layout.addWidget(numeric_frame)

        # Real-time plots - stacked vertically
        plot_splitter = QSplitter(Qt.Vertical)
        plot_splitter.setChildrenCollapsible(False)

        # Accelerometer plot
        self.imu_plot = ImuPlotWidget()
        plot_splitter.addWidget(self.imu_plot)

        # Gyroscope plot
        self.gyro_plot = GyroPlotWidget()
        plot_splitter.addWidget(self.gyro_plot)

        # Set equal initial sizes
        plot_splitter.setSizes([200, 200])

        layout.addWidget(plot_splitter, 1)

        return group

    def _create_system_info(self) -> QGroupBox:
        """Create system information display."""
        group = QGroupBox("System")
        layout = QGridLayout(group)
        layout.setSpacing(12)
        layout.setColumnStretch(1, 1)

        # Info fields
        fields = [
            ("Firmware", "firmware_label", "--"),
            ("Protocol", "protocol_label", "--"),
            ("Board", "board_label", "--"),
            ("Uptime", "uptime_label", "00:00:00"),
        ]

        for row, (name, attr, default) in enumerate(fields):
            name_label = QLabel(name)
            name_label.setStyleSheet(
                "color: #5C5C6E; "
                "font-size: 11px;"
            )
            layout.addWidget(name_label, row, 0)

            value_label = QLabel(default)
            value_label.setStyleSheet(
                "color: #E8E8EC; "
                "font-family: 'Menlo', 'JetBrains Mono', monospace; "
                "font-size: 12px;"
            )
            setattr(self, attr, value_label)
            layout.addWidget(value_label, row, 1)

        return group

    def _create_quick_actions(self) -> QGroupBox:
        """Create quick actions panel."""
        group = QGroupBox("Actions")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # LED control
        led_layout = QHBoxLayout()
        led_layout.setSpacing(8)

        led_on = QPushButton("LED On")
        led_on.setObjectName("secondary")
        led_on.clicked.connect(lambda: self.controller.gpio_write(0, 1))
        led_layout.addWidget(led_on)

        led_off = QPushButton("LED Off")
        led_off.setObjectName("secondary")
        led_off.clicked.connect(lambda: self.controller.gpio_write(0, 0))
        led_layout.addWidget(led_off)

        layout.addLayout(led_layout)

        # Stop all button
        stop_btn = QPushButton("Stop All Motion")
        stop_btn.setObjectName("danger")
        stop_btn.clicked.connect(self.controller.stop_motion)
        layout.addWidget(stop_btn)

        # Export telemetry
        export_btn = QPushButton("Export Telemetry")
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self._export_telemetry)
        layout.addWidget(export_btn)

        return group

    def _setup_connections(self) -> None:
        """Connect signals to slots."""
        self.signals.connection_changed.connect(self._on_connection_changed)
        self.signals.state_changed.connect(self._on_state_changed)
        self.signals.imu_data.connect(self._on_imu_data)
        self.signals.encoder_data.connect(self._on_encoder_data)
        self.signals.capabilities_changed.connect(self._on_capabilities_changed)

    def _refresh_ports(self) -> None:
        """Refresh available serial ports."""
        self.port_combo.clear()

        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
        except ImportError:
            ports = []

        if not ports:
            self.port_combo.addItem("No ports found")
            self.port_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)
        else:
            self.port_combo.setEnabled(True)
            self.connect_btn.setEnabled(True)

            for port in sorted(ports, key=lambda p: p.device):
                display = port.device
                if port.description and port.description != port.device:
                    display = f"{port.device} - {port.description[:30]}"
                self.port_combo.addItem(display, port.device)

            # Try to select last used port
            last_port = self.settings.get_last_port()
            if last_port:
                for i in range(self.port_combo.count()):
                    if self.port_combo.itemData(i) == last_port:
                        self.port_combo.setCurrentIndex(i)
                        break

    def _load_settings(self) -> None:
        """Load saved settings."""
        # Transport type
        transport = self.settings.get_transport_type()
        idx = 1 if transport == "tcp" else 0
        self.transport_combo.setCurrentIndex(idx)
        self._on_transport_changed(idx)

        # Port/Host
        if transport == "tcp":
            self.host_input.setText(self.settings.get_last_host())
            self.tcp_port_input.setText(str(self.settings.get_last_tcp_port()))

    def _on_transport_changed(self, index: int) -> None:
        """Handle transport type change."""
        is_tcp = index == 1

        # Serial controls
        self.port_label.setVisible(not is_tcp)
        self.port_combo.setVisible(not is_tcp)
        self.refresh_btn.setVisible(not is_tcp)
        self.baud_label.setVisible(not is_tcp)
        self.baud_combo.setVisible(not is_tcp)

        # TCP controls
        self.host_label.setVisible(is_tcp)
        self.host_input.setVisible(is_tcp)
        self.tcp_port_label.setVisible(is_tcp)
        self.tcp_port_input.setVisible(is_tcp)

        if not is_tcp:
            self._refresh_ports()

    def _on_connect_clicked(self) -> None:
        """Handle connect button click."""
        if self.controller.is_connected:
            self.controller.disconnect()
            return

        is_tcp = self.transport_combo.currentIndex() == 1

        if is_tcp:
            host = self.host_input.text().strip()
            if not host:
                self.signals.status_error.emit("Please enter a host address")
                return

            tcp_port = int(self.tcp_port_input.text() or "3333")
            self.settings.set_transport_type("tcp")
            self.settings.set_last_host(host)
            self.settings.set_last_tcp_port(tcp_port)
            self.controller.connect_tcp(host, tcp_port)
        else:
            port = self.port_combo.currentData()
            if not port:
                self.signals.status_error.emit("Please select a serial port")
                return

            baudrate = int(self.baud_combo.currentText())
            self.settings.set_transport_type("serial")
            self.settings.set_last_port(port)
            self.settings.add_recent_port(port)
            self.controller.connect_serial(port, baudrate)

            # Notify other panels about the serial port selection
            self.signals.serial_port_selected.emit(port, baudrate)

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        """Handle connection state change."""
        self.connect_btn.setText("Disconnect" if connected else "Connect")

        # Enable/disable controls
        for btn in [self.arm_btn, self.activate_btn, self.disarm_btn, self.estop_btn, self.clear_estop_btn]:
            btn.setEnabled(connected)

        # Update system info
        if connected and self.controller.state.firmware_version:
            self.firmware_label.setText(self.controller.state.firmware_version)
            self.protocol_label.setText(str(self.controller.state.protocol_version))

    def _on_state_changed(self, state: str) -> None:
        """Handle robot state change."""
        # Show/hide Clear E-STOP button based on state
        is_estopped = state == "ESTOP"
        self.clear_estop_btn.setVisible(is_estopped)
        self.estop_btn.setVisible(not is_estopped)

        # Update state labels
        state_colors = {
            "IDLE": "#52525B",
            "ARMED": "#F59E0B",
            "ACTIVE": "#8B5CF6",
            "ESTOP": "#EF4444",
        }
        text_colors = {
            "ARMED": "#18181B",
        }

        for s, label in self.state_labels.items():
            if s == state:
                color = state_colors.get(state, "#52525B")
                text_color = text_colors.get(state, "white")
                label.setStyleSheet(
                    f"background-color: {color}; "
                    f"color: {text_color}; "
                    f"padding: 4px 10px; "
                    f"border-radius: 4px; "
                    f"font-size: 10px; "
                    f"font-weight: 500;"
                )
            else:
                label.setStyleSheet(
                    "background-color: #27272A; "
                    "color: #71717A; "
                    "padding: 4px 10px; "
                    "border-radius: 4px; "
                    "font-size: 10px; "
                    "font-weight: 500;"
                )

    def _on_imu_data(self, imu) -> None:
        """Handle IMU data update."""
        # Update numeric labels (compact format)
        for key in ["ax", "ay", "az", "gx", "gy", "gz"]:
            value = getattr(imu, key, 0.0)
            if key in self.imu_labels:
                self.imu_labels[key].setText(f"{value:.1f}")

        # Update plots
        if hasattr(self, 'imu_plot'):
            self.imu_plot.update_imu(imu)
        if hasattr(self, 'gyro_plot'):
            self.gyro_plot.update_gyro(imu)

    def _on_encoder_data(self, encoder_id: int, encoder) -> None:
        """Handle encoder data update."""
        if encoder_id in self.encoder_labels:
            ticks = getattr(encoder, 'ticks', 0)
            self.encoder_labels[encoder_id].setText(str(ticks))

    def _export_telemetry(self) -> None:
        """Export telemetry data to CSV."""
        from PySide6.QtWidgets import QFileDialog
        from datetime import datetime
        import csv

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"telemetry_{timestamp}.csv"

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Telemetry",
            default_name,
            "CSV Files (*.csv);;All Files (*)",
        )

        if not filename:
            return

        try:
            # Collect data from plots
            data_rows = []

            if hasattr(self, 'imu_plot') and self.imu_plot._series:
                # Get timestamps from any series
                first_series = next(iter(self.imu_plot._series.values()))
                timestamps = list(first_series.timestamps)

                for i, ts in enumerate(timestamps):
                    row = {"timestamp": ts}
                    for name, series in self.imu_plot._series.items():
                        if i < len(series.data):
                            row[name] = series.data[i]
                    if hasattr(self, 'gyro_plot'):
                        for name, series in self.gyro_plot._series.items():
                            if i < len(series.data):
                                row[name] = series.data[i]
                    data_rows.append(row)

            if data_rows:
                # Write CSV
                fieldnames = list(data_rows[0].keys())
                with open(filename, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data_rows)

                self.signals.status_message.emit(f"Exported {len(data_rows)} samples to {filename}")
            else:
                self.signals.status_error.emit("No telemetry data to export")

        except Exception as e:
            self.signals.status_error.emit(f"Export failed: {e}")

    def _on_capabilities_changed(self, caps: DeviceCapabilities) -> None:
        """
        Handle device capabilities change.

        Show/hide dashboard sections based on device capabilities.
        """
        # Telemetry section: show if IMU or telemetry is available
        has_telem = caps.has_imu or caps.has_telemetry or caps.has_encoder
        self._telemetry_group.setVisible(has_telem)

        # Update features display in system info
        if caps.features:
            self.signals.log_info(f"Dashboard: device has {len(caps.features)} features")
