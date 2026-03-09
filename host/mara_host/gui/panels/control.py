# mara_host/gui/panels/control.py
"""
Control panel for manual robot control.

Uses extracted widgets for motor/servo sliders and parameter grids.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "control",
    "label": "Control",
    "order": 20,
}

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt, QTimer

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.gui.core.state import DeviceCapabilities
from mara_host.gui.widgets import (
    JoystickWidget,
    MotorSliderGroup,
    ServoSliderGroup,
    ParameterGrid,
    ParameterSpec,
    TelemetryGrid,
    TelemetrySpec,
)
from mara_host.gui.widgets.gamepad import GamepadHandler


class ControlPanel(QWidget):
    """
    Control panel for manual robot operation.

    Dynamically shows/hides sections based on device capabilities.
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

        # Velocity command timer
        self._velocity_timer = QTimer(self)
        self._velocity_timer.timeout.connect(self._send_velocity)
        self._last_vx = 0.0
        self._last_omega = 0.0

        # Throttled slider timer (100ms = 10Hz max, gentler on WiFi)
        self._slider_timer = QTimer(self)
        self._slider_timer.timeout.connect(self._send_pending_slider_commands)
        self._slider_timer.start(100)

        # Pending values
        self._pending_motor_speeds: dict[int, float | None] = {}
        self._pending_servo_angles: dict[int, float | None] = {}
        self._last_sent_motor_speeds: dict[int, float] = {}
        self._last_sent_servo_angles: dict[int, float] = {}

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Main content in two columns
        content = QHBoxLayout()
        content.setSpacing(24)

        # Left column
        left = QVBoxLayout()
        left.setSpacing(16)
        self._velocity_group = self._create_velocity_control()
        left.addWidget(self._velocity_group)
        self._gpio_group = self._create_gpio_control()
        left.addWidget(self._gpio_group)
        self._motor_pid_group = self._create_motor_pid_control()
        left.addWidget(self._motor_pid_group)
        left.addStretch()

        left_container = QWidget()
        left_container.setLayout(left)
        content.addWidget(left_container, 1)

        # Right column
        right = QVBoxLayout()
        right.setSpacing(16)
        self._motor_group = self._create_motor_control()
        right.addWidget(self._motor_group)
        self._servo_group = self._create_servo_control()
        right.addWidget(self._servo_group)
        right.addStretch()

        right_container = QWidget()
        right_container.setLayout(right)
        content.addWidget(right_container, 1)

        layout.addLayout(content, 1)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # E-STOP button at bottom
        estop_container = QWidget()
        estop_layout = QVBoxLayout(estop_container)
        estop_layout.setContentsMargins(32, 16, 32, 16)
        estop_layout.addWidget(self._create_estop_button())
        main_layout.addWidget(estop_container)

    def _create_velocity_control(self) -> QGroupBox:
        """Create velocity control with joystick."""
        group = QGroupBox("Velocity Control")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Joystick
        self.joystick = JoystickWidget()
        self.joystick.setMinimumSize(200, 200)
        self.joystick.velocity_changed.connect(self._on_joystick_changed)
        layout.addWidget(self.joystick, 0, Qt.AlignCenter)

        # Velocity display using TelemetryGrid
        self._velocity_display = TelemetryGrid([
            TelemetrySpec("vx", "vx", "m/s", "{:6.2f}", "0.00"),
            TelemetrySpec("omega", "omega", "rad/s", "{:6.2f}", "0.00"),
        ], columns=2)
        layout.addWidget(self._velocity_display)

        # Velocity limits using ParameterGrid
        self._velocity_limits = ParameterGrid([
            ParameterSpec("max_linear", "Max Linear", 0.1, 5.0,
                         self.settings.get_max_linear_velocity(), 0.1, 1, " m/s"),
            ParameterSpec("max_angular", "Max Angular", 0.1, 10.0,
                         self.settings.get_max_angular_velocity(), 0.1, 1, " rad/s"),
        ], columns=2)
        self._velocity_limits.value_changed.connect(self._on_velocity_limit_changed)
        layout.addWidget(self._velocity_limits)

        return group

    def _create_motor_control(self) -> QGroupBox:
        """Create DC motor control section."""
        group = QGroupBox("Motors")
        layout = QVBoxLayout(group)
        layout.setSpacing(20)

        self.motor_sliders: dict[int, MotorSliderGroup] = {}

        for motor_id in range(2):
            slider = MotorSliderGroup(motor_id=motor_id, auto_zero=True)
            slider.value_changed.connect(self._on_motor_changed)
            slider.released.connect(self._on_motor_released)
            self.motor_sliders[motor_id] = slider
            layout.addWidget(slider)

        # Stop all button
        stop_btn = QPushButton("Stop All")
        stop_btn.setObjectName("secondary")
        stop_btn.clicked.connect(self._stop_all_motors)
        layout.addWidget(stop_btn)

        return group

    def _create_servo_control(self) -> QGroupBox:
        """Create servo control section."""
        group = QGroupBox("Servos")
        layout = QVBoxLayout(group)
        layout.setSpacing(20)

        self.servo_sliders: dict[int, ServoSliderGroup] = {}

        for servo_id in range(2):
            slider = ServoSliderGroup(servo_id=servo_id)
            slider.value_changed.connect(self._on_servo_changed)
            slider.released.connect(self._on_servo_released)
            self.servo_sliders[servo_id] = slider
            layout.addWidget(slider)

        # Center all button
        center_btn = QPushButton("Center All")
        center_btn.setObjectName("secondary")
        center_btn.clicked.connect(self._center_all_servos)
        layout.addWidget(center_btn)

        return group

    def _create_gpio_control(self) -> QGroupBox:
        """Create GPIO control section."""
        group = QGroupBox("GPIO")
        layout = QGridLayout(group)
        layout.setSpacing(12)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(4, 1)

        for channel in range(4):
            row = channel // 2
            col_base = (channel % 2) * 3

            label = QLabel(f"CH{channel}")
            label.setStyleSheet("color: #71717A; font-size: 12px;")
            label.setMinimumWidth(40)
            layout.addWidget(label, row, col_base)

            on_btn = QPushButton("On")
            on_btn.setObjectName("secondary")
            on_btn.setMaximumWidth(60)
            on_btn.clicked.connect(lambda _, ch=channel: self.controller.gpio_write(ch, 1))
            layout.addWidget(on_btn, row, col_base + 1)

            off_btn = QPushButton("Off")
            off_btn.setObjectName("secondary")
            off_btn.setMaximumWidth(60)
            off_btn.clicked.connect(lambda _, ch=channel: self.controller.gpio_write(ch, 0))
            layout.addWidget(off_btn, row, col_base + 2)

        return group

    def _create_motor_pid_control(self) -> QGroupBox:
        """Create motor PID control section."""
        group = QGroupBox("Motor Velocity PID")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Motor selector row
        motor_row = QHBoxLayout()
        motor_row.addWidget(QLabel("Motor:"))

        from PySide6.QtWidgets import QSpinBox, QCheckBox
        self.pid_motor_spin = QSpinBox()
        self.pid_motor_spin.setRange(0, 3)
        self.pid_motor_spin.setValue(0)
        motor_row.addWidget(self.pid_motor_spin)
        motor_row.addStretch()

        self.pid_enable_check = QCheckBox("Enable PID")
        self.pid_enable_check.stateChanged.connect(self._on_pid_enable_changed)
        motor_row.addWidget(self.pid_enable_check)
        layout.addLayout(motor_row)

        # PID gains using ParameterGrid
        self._pid_gains = ParameterGrid([
            ParameterSpec("kp", "Kp", 0, 100, 1.0, 0.1, 3),
            ParameterSpec("ki", "Ki", 0, 100, 0.0, 0.01, 3),
            ParameterSpec("kd", "Kd", 0, 100, 0.0, 0.01, 3),
        ], columns=3)
        layout.addWidget(self._pid_gains)

        # Velocity target
        from mara_host.gui.widgets import SpinBoxRow
        self._vel_target = SpinBoxRow("Velocity Target:", -100, 100, 0.0, 0.5, 1, " rad/s")
        layout.addWidget(self._vel_target)

        # Buttons
        btn_row = QHBoxLayout()
        apply_btn = QPushButton("Apply Gains")
        apply_btn.setObjectName("secondary")
        apply_btn.clicked.connect(self._on_apply_pid_gains)
        btn_row.addWidget(apply_btn)

        set_target_btn = QPushButton("Set Target")
        set_target_btn.setObjectName("secondary")
        set_target_btn.clicked.connect(self._on_set_velocity_target)
        btn_row.addWidget(set_target_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return group

    def _create_estop_button(self) -> QWidget:
        """Create the E-STOP and Clear E-STOP buttons."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.estop_btn = QPushButton("Emergency Stop")
        self.estop_btn.setObjectName("danger")
        self.estop_btn.setMinimumHeight(52)
        self.estop_btn.setStyleSheet(
            "QPushButton { font-size: 15px; font-weight: 600; letter-spacing: 0.5px; }"
        )
        self.estop_btn.clicked.connect(self._on_estop_clicked)
        layout.addWidget(self.estop_btn)

        self.clear_estop_btn = QPushButton("Clear Emergency Stop")
        self.clear_estop_btn.setObjectName("warning")
        self.clear_estop_btn.setMinimumHeight(52)
        self.clear_estop_btn.setStyleSheet(
            "QPushButton { font-size: 15px; font-weight: 600; letter-spacing: 0.5px; }"
        )
        self.clear_estop_btn.clicked.connect(self._on_clear_estop_clicked)
        self.clear_estop_btn.setVisible(False)
        layout.addWidget(self.clear_estop_btn)

        return container

    def _setup_connections(self) -> None:
        """Connect signals."""
        self.signals.connection_changed.connect(self._on_connection_changed)
        self.signals.state_changed.connect(self._on_state_changed)
        self.signals.capabilities_changed.connect(self._on_capabilities_changed)

        # Set up gamepad
        self._gamepad = GamepadHandler(self)
        if self._gamepad.is_available:
            self._gamepad.left_stick.connect(self._on_gamepad_stick)
            self._gamepad.button_pressed.connect(self._on_gamepad_button)
            self._gamepad.connected.connect(self._on_gamepad_connected)
            self._gamepad.disconnected.connect(self._on_gamepad_disconnected)

            if self._gamepad.start():
                self.signals.status_message.emit(
                    f"Gamepad connected: {self._gamepad.get_connected_name()}"
                )

    # ==================== Event Handlers ====================

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        self.joystick.setEnabled(connected)
        for slider in self.motor_sliders.values():
            slider.setEnabled(connected)
        for slider in self.servo_sliders.values():
            slider.setEnabled(connected)

        if not connected:
            # Show all sections when disconnected
            self._velocity_group.setVisible(True)
            self._motor_group.setVisible(True)
            self._motor_pid_group.setVisible(True)
            self._servo_group.setVisible(True)
            self._gpio_group.setVisible(True)

    def _on_capabilities_changed(self, caps: DeviceCapabilities) -> None:
        self._velocity_group.setVisible(caps.has_motion_ctrl or caps.has_dc_motor)
        self._motor_group.setVisible(caps.has_dc_motor)
        self._motor_pid_group.setVisible(caps.has_dc_motor)
        self._servo_group.setVisible(caps.has_servo)
        self._gpio_group.setVisible(caps.has_gpio)

    def _on_joystick_changed(self, x: float, y: float) -> None:
        max_linear = self._velocity_limits.value("max_linear")
        max_angular = self._velocity_limits.value("max_angular")

        self._last_vx = y * max_linear
        self._last_omega = -x * max_angular

        self._velocity_display.update("vx", self._last_vx)
        self._velocity_display.update("omega", self._last_omega)

        if not self._velocity_timer.isActive():
            self._velocity_timer.start(50)

    def _send_velocity(self) -> None:
        if not self.controller.is_connected:
            self._velocity_timer.stop()
            return

        if abs(self._last_vx) < 0.01 and abs(self._last_omega) < 0.01:
            self._velocity_timer.stop()
            self.controller.stop_motion()
        else:
            self.controller.set_velocity(self._last_vx, self._last_omega)

    def _on_velocity_limit_changed(self, key: str, value: float) -> None:
        if key == "max_linear":
            self.settings.set_max_linear_velocity(value)
        elif key == "max_angular":
            self.settings.set_max_angular_velocity(value)

    def _on_gamepad_stick(self, x: float, y: float) -> None:
        self._on_joystick_changed(x, y)

    def _on_gamepad_button(self, button: str) -> None:
        button_actions = {
            "A": self.controller.arm,
            "B": self.controller.disarm,
            "X": self.controller.activate,
            "Y": self.controller.estop,
            "Start": self.controller.clear_estop,
        }
        if button in button_actions:
            button_actions[button]()

    def _on_gamepad_connected(self, name: str) -> None:
        self.signals.status_message.emit(f"Gamepad connected: {name}")

    def _on_gamepad_disconnected(self) -> None:
        self.signals.status_message.emit("Gamepad disconnected")

    def _send_pending_slider_commands(self) -> None:
        if not self.controller.is_connected:
            return

        for motor_id, speed in list(self._pending_motor_speeds.items()):
            if speed is not None:
                last_sent = self._last_sent_motor_speeds.get(motor_id)
                if last_sent is None or abs(speed - last_sent) > 0.001:
                    self.controller.set_motor_speed(motor_id, speed)
                    self._last_sent_motor_speeds[motor_id] = speed
                self._pending_motor_speeds[motor_id] = None

        for servo_id, angle in list(self._pending_servo_angles.items()):
            if angle is not None:
                last_sent = self._last_sent_servo_angles.get(servo_id)
                if last_sent is None or abs(angle - last_sent) > 0.1:
                    self.controller.set_servo_angle(servo_id, angle)
                    self._last_sent_servo_angles[servo_id] = angle
                self._pending_servo_angles[servo_id] = None

    def _on_motor_changed(self, motor_id: int, speed: float) -> None:
        self._pending_motor_speeds[motor_id] = speed

    def _on_motor_released(self, motor_id: int) -> None:
        pass  # Auto-zero handled by widget

    def _stop_all_motors(self) -> None:
        for motor_id, slider in self.motor_sliders.items():
            slider.setValue(0)
            self.controller.stop_motor(motor_id)

    def _on_servo_changed(self, servo_id: int, angle: float) -> None:
        self._pending_servo_angles[servo_id] = angle

    def _on_servo_released(self, servo_id: int, angle: float) -> None:
        self.controller.set_servo_angle_reliable(servo_id, angle)

    def _center_all_servos(self) -> None:
        for slider in self.servo_sliders.values():
            slider.center()

    def _on_estop_clicked(self) -> None:
        self.controller.estop()
        self._stop_all_motors()
        self._velocity_timer.stop()

    def _on_clear_estop_clicked(self) -> None:
        self.controller.clear_estop()

    def _on_state_changed(self, state: str) -> None:
        is_estopped = state == "ESTOP"
        self.estop_btn.setVisible(not is_estopped)
        self.clear_estop_btn.setVisible(is_estopped)

    # ==================== PID Handlers ====================

    def _on_pid_enable_changed(self, state: int) -> None:
        motor_id = self.pid_motor_spin.value()
        enable = state == Qt.CheckState.Checked.value
        self.controller.send_command(
            "CMD_DC_VEL_PID_ENABLE",
            {"motor_id": motor_id, "enable": enable}
        )

    def _on_apply_pid_gains(self) -> None:
        motor_id = self.pid_motor_spin.value()
        gains = self._pid_gains.values()
        self.controller.send_command(
            "CMD_DC_SET_VEL_GAINS",
            {"motor_id": motor_id, "kp": gains["kp"], "ki": gains["ki"], "kd": gains["kd"]}
        )
        self.signals.status_message.emit(f"Applied PID gains to motor {motor_id}")

    def _on_set_velocity_target(self) -> None:
        motor_id = self.pid_motor_spin.value()
        omega = self._vel_target.value()
        self.controller.send_command(
            "CMD_DC_SET_VEL_TARGET",
            {"motor_id": motor_id, "omega": omega}
        )
