# mara_host/gui/panels/sensors.py
"""
Sensors Panel.

Control and monitor encoders, ultrasonic sensors, and IMU.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "sensors",
    "label": "Sensors",
    "order": 27,
}

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QScrollArea,
    QFrame,
    QTabWidget,
    QCheckBox,
)
from PySide6.QtCore import Qt, QTimer

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings


class EncoderWidget(QFrame):
    """Widget for a single encoder."""

    def __init__(self, encoder_id: int, controller: RobotController, parent=None):
        super().__init__(parent)
        self.encoder_id = encoder_id
        self.controller = controller

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background-color: #1A1A1C; border-radius: 8px; padding: 12px; }"
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel(f"Encoder {self.encoder_id}")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #FAFAFA;")
        header.addWidget(title)
        header.addStretch()

        self.status_label = QLabel("Not attached")
        self.status_label.setStyleSheet("color: #71717A;")
        header.addWidget(self.status_label)
        layout.addLayout(header)

        # Readings
        readings = QGridLayout()
        readings.setSpacing(8)

        readings.addWidget(QLabel("Count:"), 0, 0)
        self.count_label = QLabel("--")
        self.count_label.setStyleSheet("font-weight: bold; font-size: 18px; color: #22C55E;")
        readings.addWidget(self.count_label, 0, 1)

        readings.addWidget(QLabel("Velocity:"), 0, 2)
        self.velocity_label = QLabel("-- rad/s")
        self.velocity_label.setStyleSheet("font-weight: bold; color: #3B82F6;")
        readings.addWidget(self.velocity_label, 0, 3)

        readings.addWidget(QLabel("Revolutions:"), 1, 0)
        self.revs_label = QLabel("--")
        self.revs_label.setStyleSheet("color: #A1A1AA;")
        readings.addWidget(self.revs_label, 1, 1)

        layout.addLayout(readings)

        # Attachment settings
        attach_group = QGroupBox("Configuration")
        attach_layout = QGridLayout(attach_group)

        attach_layout.addWidget(QLabel("Pin A:"), 0, 0)
        self.pin_a_spin = QSpinBox()
        self.pin_a_spin.setRange(0, 39)
        self.pin_a_spin.setValue(34)
        attach_layout.addWidget(self.pin_a_spin, 0, 1)

        attach_layout.addWidget(QLabel("Pin B:"), 0, 2)
        self.pin_b_spin = QSpinBox()
        self.pin_b_spin.setRange(0, 39)
        self.pin_b_spin.setValue(35)
        attach_layout.addWidget(self.pin_b_spin, 0, 3)

        attach_layout.addWidget(QLabel("PPR:"), 1, 0)
        self.ppr_spin = QSpinBox()
        self.ppr_spin.setRange(1, 10000)
        self.ppr_spin.setValue(11)
        attach_layout.addWidget(self.ppr_spin, 1, 1)

        layout.addWidget(attach_group)

        # Buttons
        btn_row = QHBoxLayout()

        attach_btn = QPushButton("Attach")
        attach_btn.setObjectName("primary")
        attach_btn.clicked.connect(self._attach)
        btn_row.addWidget(attach_btn)

        detach_btn = QPushButton("Detach")
        detach_btn.setObjectName("secondary")
        detach_btn.clicked.connect(self._detach)
        btn_row.addWidget(detach_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("secondary")
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _attach(self) -> None:
        self.controller.send_command(
            "CMD_ENCODER_ATTACH",
            {
                "encoder_id": self.encoder_id,
                "pin_a": self.pin_a_spin.value(),
                "pin_b": self.pin_b_spin.value(),
                "ppr": self.ppr_spin.value(),
            }
        )
        self.status_label.setText("Attached")
        self.status_label.setStyleSheet("color: #22C55E;")

    def _detach(self) -> None:
        self.controller.send_command(
            "CMD_ENCODER_DETACH",
            {"encoder_id": self.encoder_id}
        )
        self.status_label.setText("Not attached")
        self.status_label.setStyleSheet("color: #71717A;")

    def _reset(self) -> None:
        self.controller.send_command(
            "CMD_ENCODER_RESET",
            {"encoder_id": self.encoder_id}
        )
        self.count_label.setText("0")
        self.revs_label.setText("0.00")

    def update_reading(self, count: int, velocity: float) -> None:
        self.count_label.setText(str(count))
        self.velocity_label.setText(f"{velocity:.2f} rad/s")
        ppr = self.ppr_spin.value()
        if ppr > 0:
            revs = count / (ppr * 4)  # Quadrature
            self.revs_label.setText(f"{revs:.2f}")


class UltrasonicWidget(QFrame):
    """Widget for a single ultrasonic sensor."""

    def __init__(self, sensor_id: int, controller: RobotController, parent=None):
        super().__init__(parent)
        self.sensor_id = sensor_id
        self.controller = controller

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { background-color: #1A1A1C; border-radius: 8px; padding: 12px; }"
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel(f"Ultrasonic {self.sensor_id}")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #FAFAFA;")
        header.addWidget(title)
        header.addStretch()

        self.status_label = QLabel("Not attached")
        self.status_label.setStyleSheet("color: #71717A;")
        header.addWidget(self.status_label)
        layout.addLayout(header)

        # Distance display
        distance_row = QHBoxLayout()
        distance_row.addWidget(QLabel("Distance:"))
        self.distance_label = QLabel("-- cm")
        self.distance_label.setStyleSheet("font-weight: bold; font-size: 24px; color: #F59E0B;")
        distance_row.addWidget(self.distance_label)
        distance_row.addStretch()
        layout.addLayout(distance_row)

        # Configuration
        config_layout = QGridLayout()

        config_layout.addWidget(QLabel("Trigger Pin:"), 0, 0)
        self.trig_spin = QSpinBox()
        self.trig_spin.setRange(0, 39)
        self.trig_spin.setValue(12)
        config_layout.addWidget(self.trig_spin, 0, 1)

        config_layout.addWidget(QLabel("Echo Pin:"), 0, 2)
        self.echo_spin = QSpinBox()
        self.echo_spin.setRange(0, 39)
        self.echo_spin.setValue(14)
        config_layout.addWidget(self.echo_spin, 0, 3)

        layout.addLayout(config_layout)

        # Buttons
        btn_row = QHBoxLayout()

        attach_btn = QPushButton("Attach")
        attach_btn.setObjectName("primary")
        attach_btn.clicked.connect(self._attach)
        btn_row.addWidget(attach_btn)

        detach_btn = QPushButton("Detach")
        detach_btn.setObjectName("secondary")
        detach_btn.clicked.connect(self._detach)
        btn_row.addWidget(detach_btn)

        read_btn = QPushButton("Read")
        read_btn.setObjectName("secondary")
        read_btn.clicked.connect(self._read)
        btn_row.addWidget(read_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _attach(self) -> None:
        self.controller.send_command(
            "CMD_ULTRASONIC_ATTACH",
            {
                "sensor_id": self.sensor_id,
                "trig_pin": self.trig_spin.value(),
                "echo_pin": self.echo_spin.value(),
            }
        )
        self.status_label.setText("Attached")
        self.status_label.setStyleSheet("color: #22C55E;")

    def _detach(self) -> None:
        self.controller.send_command(
            "CMD_ULTRASONIC_DETACH",
            {"sensor_id": self.sensor_id}
        )
        self.status_label.setText("Not attached")
        self.status_label.setStyleSheet("color: #71717A;")

    def _read(self) -> None:
        self.controller.send_command(
            "CMD_ULTRASONIC_READ",
            {"sensor_id": self.sensor_id}
        )

    def update_reading(self, distance_cm: float) -> None:
        if distance_cm < 0:
            self.distance_label.setText("Out of range")
        else:
            self.distance_label.setText(f"{distance_cm:.1f} cm")


class IMUWidget(QGroupBox):
    """Widget for IMU control and display."""

    def __init__(self, controller: RobotController, parent=None):
        super().__init__("IMU (Accelerometer / Gyroscope)", parent)
        self.controller = controller
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Accelerometer readings
        accel_group = QGroupBox("Acceleration (m/s²)")
        accel_layout = QGridLayout(accel_group)

        for i, axis in enumerate(["X", "Y", "Z"]):
            accel_layout.addWidget(QLabel(f"{axis}:"), 0, i * 2)
            label = QLabel("--")
            label.setStyleSheet("font-weight: bold; color: #3B82F6;")
            label.setObjectName(f"accel_{axis.lower()}")
            setattr(self, f"accel_{axis.lower()}_label", label)
            accel_layout.addWidget(label, 0, i * 2 + 1)

        layout.addWidget(accel_group)

        # Gyroscope readings
        gyro_group = QGroupBox("Angular Velocity (rad/s)")
        gyro_layout = QGridLayout(gyro_group)

        for i, axis in enumerate(["X", "Y", "Z"]):
            gyro_layout.addWidget(QLabel(f"{axis}:"), 0, i * 2)
            label = QLabel("--")
            label.setStyleSheet("font-weight: bold; color: #22C55E;")
            setattr(self, f"gyro_{axis.lower()}_label", label)
            gyro_layout.addWidget(label, 0, i * 2 + 1)

        layout.addWidget(gyro_group)

        # Temperature
        temp_row = QHBoxLayout()
        temp_row.addWidget(QLabel("Temperature:"))
        self.temp_label = QLabel("-- °C")
        self.temp_label.setStyleSheet("font-weight: bold;")
        temp_row.addWidget(self.temp_label)
        temp_row.addStretch()
        layout.addLayout(temp_row)

        # Calibration
        cal_group = QGroupBox("Calibration")
        cal_layout = QVBoxLayout(cal_group)

        cal_info = QLabel("Place robot on flat surface before calibrating.")
        cal_info.setStyleSheet("color: #71717A;")
        cal_layout.addWidget(cal_info)

        cal_btn_row = QHBoxLayout()

        cal_btn = QPushButton("Calibrate Bias")
        cal_btn.setObjectName("primary")
        cal_btn.clicked.connect(self._calibrate)
        cal_btn_row.addWidget(cal_btn)

        zero_btn = QPushButton("Zero Orientation")
        zero_btn.setObjectName("secondary")
        zero_btn.clicked.connect(self._zero)
        cal_btn_row.addWidget(zero_btn)

        cal_btn_row.addStretch()
        cal_layout.addLayout(cal_btn_row)

        layout.addWidget(cal_group)

    def _calibrate(self) -> None:
        self.controller.send_command(
            "CMD_IMU_CALIBRATE",
            {"samples": 100, "delay_ms": 10}
        )

    def _zero(self) -> None:
        self.controller.send_command("CMD_IMU_ZERO", {})

    def update_reading(self, ax: float, ay: float, az: float,
                       gx: float, gy: float, gz: float, temp: float) -> None:
        self.accel_x_label.setText(f"{ax:.2f}")
        self.accel_y_label.setText(f"{ay:.2f}")
        self.accel_z_label.setText(f"{az:.2f}")
        self.gyro_x_label.setText(f"{gx:.2f}")
        self.gyro_y_label.setText(f"{gy:.2f}")
        self.gyro_z_label.setText(f"{gz:.2f}")
        self.temp_label.setText(f"{temp:.1f} °C")


class SensorsPanel(QWidget):
    """Sensors Panel - Encoders, Ultrasonic, IMU."""

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

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget for sensor types
        tabs = QTabWidget()

        # Encoders tab
        encoder_widget = QWidget()
        encoder_layout = QVBoxLayout(encoder_widget)
        encoder_layout.setContentsMargins(16, 16, 16, 16)
        encoder_layout.setSpacing(12)

        self.encoder_widgets: dict[int, EncoderWidget] = {}
        for enc_id in range(4):
            widget = EncoderWidget(enc_id, self.controller)
            self.encoder_widgets[enc_id] = widget
            encoder_layout.addWidget(widget)
        encoder_layout.addStretch()

        encoder_scroll = QScrollArea()
        encoder_scroll.setWidgetResizable(True)
        encoder_scroll.setFrameShape(QFrame.Shape.NoFrame)
        encoder_scroll.setWidget(encoder_widget)
        tabs.addTab(encoder_scroll, "Encoders")

        # Ultrasonic tab
        ultrasonic_widget = QWidget()
        ultrasonic_layout = QVBoxLayout(ultrasonic_widget)
        ultrasonic_layout.setContentsMargins(16, 16, 16, 16)
        ultrasonic_layout.setSpacing(12)

        self.ultrasonic_widgets: dict[int, UltrasonicWidget] = {}
        for us_id in range(4):
            widget = UltrasonicWidget(us_id, self.controller)
            self.ultrasonic_widgets[us_id] = widget
            ultrasonic_layout.addWidget(widget)
        ultrasonic_layout.addStretch()

        ultrasonic_scroll = QScrollArea()
        ultrasonic_scroll.setWidgetResizable(True)
        ultrasonic_scroll.setFrameShape(QFrame.Shape.NoFrame)
        ultrasonic_scroll.setWidget(ultrasonic_widget)
        tabs.addTab(ultrasonic_scroll, "Ultrasonic")

        # IMU tab
        imu_widget = QWidget()
        imu_layout = QVBoxLayout(imu_widget)
        imu_layout.setContentsMargins(16, 16, 16, 16)

        self.imu_widget = IMUWidget(self.controller)
        imu_layout.addWidget(self.imu_widget)
        imu_layout.addStretch()

        imu_scroll = QScrollArea()
        imu_scroll.setWidgetResizable(True)
        imu_scroll.setFrameShape(QFrame.Shape.NoFrame)
        imu_scroll.setWidget(imu_widget)
        tabs.addTab(imu_scroll, "IMU")

        main_layout.addWidget(tabs)

    def _setup_connections(self) -> None:
        self.signals.connection_changed.connect(self._on_connection_changed)
        self.signals.telemetry_received.connect(self._on_telemetry)

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        for widget in self.encoder_widgets.values():
            widget.setEnabled(connected)
        for widget in self.ultrasonic_widgets.values():
            widget.setEnabled(connected)
        self.imu_widget.setEnabled(connected)

    def _on_telemetry(self, topic: str, data: dict) -> None:
        if topic == "encoder":
            enc_id = data.get("encoder_id", 0)
            if enc_id in self.encoder_widgets:
                self.encoder_widgets[enc_id].update_reading(
                    data.get("count", 0),
                    data.get("velocity", 0.0)
                )
        elif topic == "ultrasonic":
            sensor_id = data.get("sensor_id", 0)
            if sensor_id in self.ultrasonic_widgets:
                self.ultrasonic_widgets[sensor_id].update_reading(
                    data.get("distance_cm", -1)
                )
        elif topic == "imu":
            self.imu_widget.update_reading(
                data.get("ax", 0), data.get("ay", 0), data.get("az", 0),
                data.get("gx", 0), data.get("gy", 0), data.get("gz", 0),
                data.get("temp", 0)
            )
