# mara_host/gui/panels/control.py
"""
Control panel for manual robot control.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt, QTimer, Signal

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.gui.core.state import DeviceCapabilities
from mara_host.gui.widgets.joystick import JoystickWidget
from mara_host.gui.widgets.gamepad import GamepadHandler


class ControlPanel(QWidget):
    """
    Control panel for manual robot operation.

    Dynamically shows/hides sections based on device capabilities.
    When no device is connected, all sections are shown.
    When connected, only features reported by the device are visible.

    Layout:
        ┌────────────────────────┬────────────────────────────┐
        │ Velocity Control       │ Motors                     │
        │ ┌────────────────────┐ │ M0: [----slider----]      │
        │ │      [Joystick]    │ │ M1: [----slider----]      │
        │ │   vx: 0.0  ω: 0.0  │ ├────────────────────────────┤
        │ └────────────────────┘ │ Servos                     │
        ├────────────────────────┤ S0: [---0-180 deg---]      │
        │ GPIO                   │ S1: [---0-180 deg---]      │
        │ [CH0 ON] [CH0 OFF]    │                            │
        │ [CH1 ON] [CH1 OFF]    │                            │
        ├────────────────────────┴────────────────────────────┤
        │              [        E-STOP        ]               │
        └─────────────────────────────────────────────────────┘
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

        # Throttled motor/servo command timer (50ms = 20Hz max)
        self._slider_timer = QTimer(self)
        self._slider_timer.timeout.connect(self._send_pending_slider_commands)
        self._slider_timer.start(50)  # 20Hz update rate

        # Pending values (None = no pending update)
        self._pending_motor_speeds: dict[int, float | None] = {}
        self._pending_servo_angles: dict[int, float | None] = {}
        self._last_sent_motor_speeds: dict[int, float] = {}
        self._last_sent_servo_angles: dict[int, float] = {}

    def _setup_ui(self) -> None:
        """Set up the control panel UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Main content
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
        self._encoder_group = self._create_encoder_control()
        left.addWidget(self._encoder_group)
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
        self._stepper_group = self._create_stepper_control()
        right.addWidget(self._stepper_group)
        self._ultrasonic_group = self._create_ultrasonic_control()
        right.addWidget(self._ultrasonic_group)
        right.addStretch()

        right_container = QWidget()
        right_container.setLayout(right)
        content.addWidget(right_container, 1)

        layout.addLayout(content, 1)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # E-STOP button at bottom (outside scroll)
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

        # Velocity display
        vel_layout = QHBoxLayout()
        vel_layout.setSpacing(10)

        vx_name = QLabel("vx")
        vx_name.setStyleSheet("color: #52525B; font-size: 11px;")
        vel_layout.addWidget(vx_name)

        self.vx_label = QLabel("0.00")
        self.vx_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "min-width: 50px; "
            "color: #FAFAFA; "
            "font-size: 13px;"
        )
        vel_layout.addWidget(self.vx_label)

        unit1 = QLabel("m/s")
        unit1.setStyleSheet("color: #52525B; font-size: 11px;")
        vel_layout.addWidget(unit1)
        vel_layout.addSpacing(20)

        omega_name = QLabel("omega")
        omega_name.setStyleSheet("color: #52525B; font-size: 11px;")
        vel_layout.addWidget(omega_name)

        self.omega_label = QLabel("0.00")
        self.omega_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "min-width: 50px; "
            "color: #FAFAFA; "
            "font-size: 13px;"
        )
        vel_layout.addWidget(self.omega_label)

        unit2 = QLabel("rad/s")
        unit2.setStyleSheet("color: #52525B; font-size: 11px;")
        vel_layout.addWidget(unit2)
        vel_layout.addStretch()

        layout.addLayout(vel_layout)

        # Velocity limits
        limits_layout = QHBoxLayout()

        limits_layout.addWidget(QLabel("Max Linear:"))
        self.max_linear_spin = QDoubleSpinBox()
        self.max_linear_spin.setRange(0.1, 5.0)
        self.max_linear_spin.setValue(self.settings.get_max_linear_velocity())
        self.max_linear_spin.setSingleStep(0.1)
        self.max_linear_spin.setSuffix(" m/s")
        self.max_linear_spin.valueChanged.connect(self._on_max_linear_changed)
        limits_layout.addWidget(self.max_linear_spin)

        limits_layout.addSpacing(20)

        limits_layout.addWidget(QLabel("Max Angular:"))
        self.max_angular_spin = QDoubleSpinBox()
        self.max_angular_spin.setRange(0.1, 10.0)
        self.max_angular_spin.setValue(self.settings.get_max_angular_velocity())
        self.max_angular_spin.setSingleStep(0.1)
        self.max_angular_spin.setSuffix(" rad/s")
        self.max_angular_spin.valueChanged.connect(self._on_max_angular_changed)
        limits_layout.addWidget(self.max_angular_spin)

        limits_layout.addStretch()

        layout.addLayout(limits_layout)

        return group

    def _create_motor_control(self) -> QGroupBox:
        """Create DC motor control section."""
        group = QGroupBox("Motors")
        layout = QVBoxLayout(group)
        layout.setSpacing(20)

        self.motor_sliders = {}
        self.motor_labels = {}

        for motor_id in range(2):
            motor_layout = QHBoxLayout()
            motor_layout.setSpacing(16)

            label = QLabel(f"M{motor_id}")
            label.setMinimumWidth(24)
            label.setStyleSheet("color: #71717A; font-size: 12px;")
            motor_layout.addWidget(label)

            slider = QSlider(Qt.Horizontal)
            slider.setRange(-100, 100)
            slider.setValue(0)
            slider.valueChanged.connect(
                lambda v, mid=motor_id: self._on_motor_changed(mid, v)
            )
            slider.sliderReleased.connect(
                lambda mid=motor_id: self._on_motor_released(mid)
            )
            self.motor_sliders[motor_id] = slider
            motor_layout.addWidget(slider, 1)

            value_label = QLabel("0")
            value_label.setMinimumWidth(36)
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_label.setStyleSheet(
                "font-family: 'Menlo', 'JetBrains Mono', monospace; "
                "color: #FAFAFA; "
                "font-size: 12px;"
            )
            self.motor_labels[motor_id] = value_label
            motor_layout.addWidget(value_label)

            unit = QLabel("%")
            unit.setStyleSheet("color: #52525B; font-size: 11px;")
            motor_layout.addWidget(unit)

            layout.addLayout(motor_layout)

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

        self.servo_sliders = {}
        self.servo_labels = {}

        for servo_id in range(2):
            servo_layout = QHBoxLayout()
            servo_layout.setSpacing(16)

            label = QLabel(f"S{servo_id}")
            label.setMinimumWidth(24)
            label.setStyleSheet("color: #71717A; font-size: 12px;")
            servo_layout.addWidget(label)

            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 180)
            slider.setValue(90)
            slider.valueChanged.connect(
                lambda v, sid=servo_id: self._on_servo_changed(sid, v)
            )
            slider.sliderReleased.connect(
                lambda sid=servo_id: self._on_servo_released(sid)
            )
            self.servo_sliders[servo_id] = slider
            servo_layout.addWidget(slider, 1)

            value_label = QLabel("90")
            value_label.setMinimumWidth(36)
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_label.setStyleSheet(
                "font-family: 'Menlo', 'JetBrains Mono', monospace; "
                "color: #FAFAFA; "
                "font-size: 12px;"
            )
            self.servo_labels[servo_id] = value_label
            servo_layout.addWidget(value_label)

            unit = QLabel("deg")
            unit.setStyleSheet("color: #52525B; font-size: 11px;")
            servo_layout.addWidget(unit)

            layout.addLayout(servo_layout)

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

        # Motor selector
        motor_row = QHBoxLayout()
        motor_row.addWidget(QLabel("Motor:"))
        self.pid_motor_spin = QSpinBox()
        self.pid_motor_spin.setRange(0, 3)
        self.pid_motor_spin.setValue(0)
        motor_row.addWidget(self.pid_motor_spin)
        motor_row.addStretch()

        self.pid_enable_check = QCheckBox("Enable PID")
        self.pid_enable_check.stateChanged.connect(self._on_pid_enable_changed)
        motor_row.addWidget(self.pid_enable_check)
        layout.addLayout(motor_row)

        # PID gains
        gains_layout = QGridLayout()
        gains_layout.setSpacing(8)

        gains_layout.addWidget(QLabel("Kp:"), 0, 0)
        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(0, 100)
        self.kp_spin.setValue(1.0)
        self.kp_spin.setSingleStep(0.1)
        self.kp_spin.setDecimals(3)
        gains_layout.addWidget(self.kp_spin, 0, 1)

        gains_layout.addWidget(QLabel("Ki:"), 0, 2)
        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(0, 100)
        self.ki_spin.setValue(0.0)
        self.ki_spin.setSingleStep(0.01)
        self.ki_spin.setDecimals(3)
        gains_layout.addWidget(self.ki_spin, 0, 3)

        gains_layout.addWidget(QLabel("Kd:"), 1, 0)
        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(0, 100)
        self.kd_spin.setValue(0.0)
        self.kd_spin.setSingleStep(0.01)
        self.kd_spin.setDecimals(3)
        gains_layout.addWidget(self.kd_spin, 1, 1)

        layout.addLayout(gains_layout)

        # Velocity target
        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Velocity Target:"))
        self.vel_target_spin = QDoubleSpinBox()
        self.vel_target_spin.setRange(-100, 100)
        self.vel_target_spin.setValue(0.0)
        self.vel_target_spin.setSingleStep(0.5)
        self.vel_target_spin.setSuffix(" rad/s")
        target_row.addWidget(self.vel_target_spin)
        target_row.addStretch()
        layout.addLayout(target_row)

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

    def _create_stepper_control(self) -> QGroupBox:
        """Create stepper motor control section."""
        group = QGroupBox("Stepper Motors")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Motor selector
        motor_row = QHBoxLayout()
        motor_row.addWidget(QLabel("Motor:"))
        self.stepper_motor_spin = QSpinBox()
        self.stepper_motor_spin.setRange(0, 3)
        self.stepper_motor_spin.setValue(0)
        motor_row.addWidget(self.stepper_motor_spin)
        motor_row.addStretch()
        layout.addLayout(motor_row)

        # Steps input
        steps_row = QHBoxLayout()
        steps_row.addWidget(QLabel("Steps:"))
        self.stepper_steps_spin = QSpinBox()
        self.stepper_steps_spin.setRange(-100000, 100000)
        self.stepper_steps_spin.setValue(200)
        steps_row.addWidget(self.stepper_steps_spin)

        steps_row.addWidget(QLabel("Speed:"))
        self.stepper_speed_spin = QDoubleSpinBox()
        self.stepper_speed_spin.setRange(1, 10000)
        self.stepper_speed_spin.setValue(500)
        self.stepper_speed_spin.setSuffix(" steps/s")
        steps_row.addWidget(self.stepper_speed_spin)
        steps_row.addStretch()
        layout.addLayout(steps_row)

        # Buttons
        btn_row = QHBoxLayout()
        move_btn = QPushButton("Move")
        move_btn.setObjectName("secondary")
        move_btn.clicked.connect(self._on_stepper_move)
        btn_row.addWidget(move_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.setObjectName("secondary")
        stop_btn.clicked.connect(self._on_stepper_stop)
        btn_row.addWidget(stop_btn)

        self.stepper_enable_check = QCheckBox("Enable")
        self.stepper_enable_check.setChecked(True)
        self.stepper_enable_check.stateChanged.connect(self._on_stepper_enable_changed)
        btn_row.addWidget(self.stepper_enable_check)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return group

    def _create_encoder_control(self) -> QGroupBox:
        """Create encoder control section."""
        group = QGroupBox("Encoders")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Encoder selector
        enc_row = QHBoxLayout()
        enc_row.addWidget(QLabel("Encoder:"))
        self.encoder_id_spin = QSpinBox()
        self.encoder_id_spin.setRange(0, 3)
        self.encoder_id_spin.setValue(0)
        enc_row.addWidget(self.encoder_id_spin)
        enc_row.addStretch()
        layout.addLayout(enc_row)

        # Live display
        display_layout = QGridLayout()
        display_layout.setSpacing(8)

        display_layout.addWidget(QLabel("Count:"), 0, 0)
        self.encoder_count_label = QLabel("--")
        self.encoder_count_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "color: #FAFAFA; font-size: 13px;"
        )
        display_layout.addWidget(self.encoder_count_label, 0, 1)

        display_layout.addWidget(QLabel("Velocity:"), 0, 2)
        self.encoder_velocity_label = QLabel("--")
        self.encoder_velocity_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "color: #FAFAFA; font-size: 13px;"
        )
        display_layout.addWidget(self.encoder_velocity_label, 0, 3)

        unit = QLabel("cts/s")
        unit.setStyleSheet("color: #52525B; font-size: 11px;")
        display_layout.addWidget(unit, 0, 4)
        layout.addLayout(display_layout)

        # Attach inputs
        attach_row = QHBoxLayout()
        attach_row.addWidget(QLabel("Pin A:"))
        self.encoder_pin_a_spin = QSpinBox()
        self.encoder_pin_a_spin.setRange(0, 39)
        self.encoder_pin_a_spin.setValue(32)
        attach_row.addWidget(self.encoder_pin_a_spin)

        attach_row.addWidget(QLabel("Pin B:"))
        self.encoder_pin_b_spin = QSpinBox()
        self.encoder_pin_b_spin.setRange(0, 39)
        self.encoder_pin_b_spin.setValue(33)
        attach_row.addWidget(self.encoder_pin_b_spin)
        attach_row.addStretch()
        layout.addLayout(attach_row)

        # Buttons
        btn_row = QHBoxLayout()
        attach_btn = QPushButton("Attach")
        attach_btn.setObjectName("secondary")
        attach_btn.clicked.connect(self._on_encoder_attach)
        btn_row.addWidget(attach_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("secondary")
        reset_btn.clicked.connect(self._on_encoder_reset)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return group

    def _create_ultrasonic_control(self) -> QGroupBox:
        """Create ultrasonic sensor control section."""
        group = QGroupBox("Ultrasonic Sensors")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Sensor selector
        sensor_row = QHBoxLayout()
        sensor_row.addWidget(QLabel("Sensor:"))
        self.ultrasonic_id_spin = QSpinBox()
        self.ultrasonic_id_spin.setRange(0, 3)
        self.ultrasonic_id_spin.setValue(0)
        sensor_row.addWidget(self.ultrasonic_id_spin)
        sensor_row.addStretch()
        layout.addLayout(sensor_row)

        # Distance display
        distance_row = QHBoxLayout()
        distance_row.addWidget(QLabel("Distance:"))
        self.ultrasonic_distance_label = QLabel("--")
        self.ultrasonic_distance_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "color: #FAFAFA; font-size: 16px; min-width: 60px;"
        )
        distance_row.addWidget(self.ultrasonic_distance_label)

        unit = QLabel("cm")
        unit.setStyleSheet("color: #52525B; font-size: 11px;")
        distance_row.addWidget(unit)

        # Status indicator
        self.ultrasonic_status_label = QLabel("")
        self.ultrasonic_status_label.setStyleSheet("color: #52525B; font-size: 11px;")
        distance_row.addWidget(self.ultrasonic_status_label)
        distance_row.addStretch()
        layout.addLayout(distance_row)

        # Buttons
        btn_row = QHBoxLayout()
        attach_btn = QPushButton("Attach")
        attach_btn.setObjectName("secondary")
        attach_btn.clicked.connect(self._on_ultrasonic_attach)
        btn_row.addWidget(attach_btn)

        read_btn = QPushButton("Read")
        read_btn.setObjectName("secondary")
        read_btn.clicked.connect(self._on_ultrasonic_read)
        btn_row.addWidget(read_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return group

    def _create_estop_button(self) -> QWidget:
        """Create the E-STOP and Clear E-STOP buttons."""
        from PySide6.QtWidgets import QHBoxLayout

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # E-STOP button
        self.estop_btn = QPushButton("Emergency Stop")
        self.estop_btn.setObjectName("danger")
        self.estop_btn.setMinimumHeight(52)
        self.estop_btn.setStyleSheet(
            "QPushButton { "
            "font-size: 15px; "
            "font-weight: 600; "
            "letter-spacing: 0.5px; "
            "}"
        )
        self.estop_btn.clicked.connect(self._on_estop_clicked)
        layout.addWidget(self.estop_btn)

        # Clear E-STOP button (hidden by default)
        self.clear_estop_btn = QPushButton("Clear Emergency Stop")
        self.clear_estop_btn.setObjectName("warning")
        self.clear_estop_btn.setMinimumHeight(52)
        self.clear_estop_btn.setStyleSheet(
            "QPushButton { "
            "font-size: 15px; "
            "font-weight: 600; "
            "letter-spacing: 0.5px; "
            "}"
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

            # Try to connect to gamepad
            if self._gamepad.start():
                self.signals.status_message.emit(
                    f"Gamepad connected: {self._gamepad.get_connected_name()}"
                )

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        """Handle connection state change."""
        self.joystick.setEnabled(connected)

        for slider in self.motor_sliders.values():
            slider.setEnabled(connected)

        for slider in self.servo_sliders.values():
            slider.setEnabled(connected)

        # When disconnected, show all sections (default state)
        if not connected:
            self._velocity_group.setVisible(True)
            self._motor_group.setVisible(True)
            self._motor_pid_group.setVisible(True)
            self._servo_group.setVisible(True)
            self._gpio_group.setVisible(True)
            self._stepper_group.setVisible(True)
            self._encoder_group.setVisible(True)
            self._ultrasonic_group.setVisible(True)

    def _on_capabilities_changed(self, caps: DeviceCapabilities) -> None:
        """
        Handle device capabilities change.

        Show/hide control sections based on what the device supports.
        """
        # Velocity control: show if motion control is available
        self._velocity_group.setVisible(caps.has_motion_ctrl or caps.has_dc_motor)

        # DC Motors: show only if device has DC motor capability
        self._motor_group.setVisible(caps.has_dc_motor)

        # Motor PID: show if DC motor capability
        self._motor_pid_group.setVisible(caps.has_dc_motor)

        # Servos: show only if device has servo capability
        self._servo_group.setVisible(caps.has_servo)

        # GPIO: show only if device has GPIO capability
        self._gpio_group.setVisible(caps.has_gpio)

        # Stepper: show if stepper capability
        self._stepper_group.setVisible(caps.has_stepper)

        # Encoder: show if encoder capability
        self._encoder_group.setVisible(caps.has_encoder)

        # Ultrasonic: always show (common sensor)
        self._ultrasonic_group.setVisible(True)

        # Log what's visible
        visible = []
        if self._velocity_group.isVisible():
            visible.append("velocity")
        if self._motor_group.isVisible():
            visible.append("motors")
        if self._motor_pid_group.isVisible():
            visible.append("motor_pid")
        if self._servo_group.isVisible():
            visible.append("servos")
        if self._gpio_group.isVisible():
            visible.append("gpio")
        if self._stepper_group.isVisible():
            visible.append("stepper")
        if self._encoder_group.isVisible():
            visible.append("encoder")

        if visible:
            self.signals.log_info(f"Control panel: {', '.join(visible)}")

    def _on_joystick_changed(self, x: float, y: float) -> None:
        """Handle joystick position change."""
        # Map joystick to velocity
        max_linear = self.max_linear_spin.value()
        max_angular = self.max_angular_spin.value()

        self._last_vx = y * max_linear  # Forward/back
        self._last_omega = -x * max_angular  # Left/right rotation

        self.vx_label.setText(f"{self._last_vx:6.2f}")
        self.omega_label.setText(f"{self._last_omega:6.2f}")

        # Start or continue velocity command timer
        if not self._velocity_timer.isActive():
            self._velocity_timer.start(50)  # 20 Hz

    def _send_velocity(self) -> None:
        """Send current velocity command."""
        if not self.controller.is_connected:
            self._velocity_timer.stop()
            return

        # Check if joystick is centered
        if abs(self._last_vx) < 0.01 and abs(self._last_omega) < 0.01:
            self._velocity_timer.stop()
            self.controller.stop_motion()
        else:
            self.controller.set_velocity(self._last_vx, self._last_omega)

    def _on_gamepad_stick(self, x: float, y: float) -> None:
        """Handle gamepad left stick input."""
        # Same as joystick
        self._on_joystick_changed(x, y)

    def _on_gamepad_button(self, button: str) -> None:
        """Handle gamepad button press."""
        if button == "A":
            self.controller.arm()
        elif button == "B":
            self.controller.disarm()
        elif button == "X":
            self.controller.activate()
        elif button == "Y":
            self.controller.estop()
        elif button == "Start":
            self.controller.clear_estop()

    def _on_gamepad_connected(self, name: str) -> None:
        """Handle gamepad connection."""
        self.signals.status_message.emit(f"Gamepad connected: {name}")

    def _on_gamepad_disconnected(self) -> None:
        """Handle gamepad disconnection."""
        self.signals.status_message.emit("Gamepad disconnected")

    def _send_pending_slider_commands(self) -> None:
        """Send pending motor/servo commands (called by timer at 20Hz)."""
        if not self.controller.is_connected:
            return

        # Send pending motor commands
        for motor_id, speed in list(self._pending_motor_speeds.items()):
            if speed is not None:
                # Only send if value changed since last send
                last_sent = self._last_sent_motor_speeds.get(motor_id)
                if last_sent is None or abs(speed - last_sent) > 0.001:
                    self.controller.set_motor_speed(motor_id, speed)
                    self._last_sent_motor_speeds[motor_id] = speed
                self._pending_motor_speeds[motor_id] = None

        # Send pending servo commands
        for servo_id, angle in list(self._pending_servo_angles.items()):
            if angle is not None:
                # Only send if value changed since last send
                last_sent = self._last_sent_servo_angles.get(servo_id)
                if last_sent is None or abs(angle - last_sent) > 0.1:
                    self.controller.set_servo_angle(servo_id, angle)
                    self._last_sent_servo_angles[servo_id] = angle
                self._pending_servo_angles[servo_id] = None

    def _on_max_linear_changed(self, value: float) -> None:
        """Handle max linear velocity change."""
        self.settings.set_max_linear_velocity(value)

    def _on_max_angular_changed(self, value: float) -> None:
        """Handle max angular velocity change."""
        self.settings.set_max_angular_velocity(value)

    def _on_motor_changed(self, motor_id: int, value: int) -> None:
        """Handle motor slider change (throttled)."""
        self.motor_labels[motor_id].setText(f"{value}")
        speed = value / 100.0
        # Store pending value - will be sent by timer
        self._pending_motor_speeds[motor_id] = speed

    def _on_motor_released(self, motor_id: int) -> None:
        """Handle motor slider release (auto-zero)."""
        self.motor_sliders[motor_id].setValue(0)

    def _stop_all_motors(self) -> None:
        """Stop all motors."""
        for motor_id in self.motor_sliders:
            self.motor_sliders[motor_id].setValue(0)
            self.controller.stop_motor(motor_id)

    def _on_servo_changed(self, servo_id: int, value: int) -> None:
        """Handle servo slider change (throttled)."""
        self.servo_labels[servo_id].setText(f"{value}")
        # Store pending value - will be sent by timer
        self._pending_servo_angles[servo_id] = float(value)

    def _on_servo_released(self, servo_id: int) -> None:
        """Handle servo slider release (send reliable final command)."""
        value = self.servo_sliders[servo_id].value()
        self.controller.set_servo_angle_reliable(servo_id, float(value))

    def _center_all_servos(self) -> None:
        """Center all servos to 90 degrees."""
        for servo_id in self.servo_sliders:
            self.servo_sliders[servo_id].setValue(90)

    def _on_estop_clicked(self) -> None:
        """Handle E-STOP button click."""
        self.controller.estop()
        self._stop_all_motors()
        self._velocity_timer.stop()

    def _on_clear_estop_clicked(self) -> None:
        """Handle Clear E-STOP button click."""
        self.controller.clear_estop()

    def _on_state_changed(self, state: str) -> None:
        """Handle robot state change."""
        is_estopped = state == "ESTOP"
        self.estop_btn.setVisible(not is_estopped)
        self.clear_estop_btn.setVisible(is_estopped)

    # ==================== Motor PID Handlers ====================

    def _on_pid_enable_changed(self, state: int) -> None:
        """Handle PID enable checkbox change."""
        motor_id = self.pid_motor_spin.value()
        enable = state == Qt.CheckState.Checked.value
        self.controller.enable_velocity_pid(motor_id, enable)

    def _on_apply_pid_gains(self) -> None:
        """Apply PID gains to selected motor."""
        motor_id = self.pid_motor_spin.value()
        kp = self.kp_spin.value()
        ki = self.ki_spin.value()
        kd = self.kd_spin.value()
        self.controller.set_velocity_gains(motor_id, kp, ki, kd)
        self.signals.status_message.emit(f"Applied PID gains to motor {motor_id}")

    def _on_set_velocity_target(self) -> None:
        """Set velocity target for selected motor."""
        motor_id = self.pid_motor_spin.value()
        omega = self.vel_target_spin.value()
        self.controller.set_velocity_target(motor_id, omega)

    # ==================== Stepper Handlers ====================

    def _on_stepper_move(self) -> None:
        """Move stepper motor."""
        motor_id = self.stepper_motor_spin.value()
        steps = self.stepper_steps_spin.value()
        speed = self.stepper_speed_spin.value()
        self.controller.stepper_move(motor_id, steps, speed)

    def _on_stepper_stop(self) -> None:
        """Stop stepper motor."""
        motor_id = self.stepper_motor_spin.value()
        self.controller.stepper_stop(motor_id)

    def _on_stepper_enable_changed(self, state: int) -> None:
        """Handle stepper enable checkbox change."""
        motor_id = self.stepper_motor_spin.value()
        enable = state == Qt.CheckState.Checked.value
        self.controller.stepper_enable(motor_id, enable)

    # ==================== Encoder Handlers ====================

    def _on_encoder_attach(self) -> None:
        """Attach encoder to pins."""
        encoder_id = self.encoder_id_spin.value()
        pin_a = self.encoder_pin_a_spin.value()
        pin_b = self.encoder_pin_b_spin.value()
        self.controller.encoder_attach(encoder_id, pin_a, pin_b)
        self.signals.status_message.emit(f"Attached encoder {encoder_id} to pins {pin_a}, {pin_b}")

    def _on_encoder_reset(self) -> None:
        """Reset encoder count."""
        encoder_id = self.encoder_id_spin.value()
        self.controller.encoder_reset(encoder_id)
        self.encoder_count_label.setText("0")

    def _update_encoder_display(self, encoder_id: int, data: object) -> None:
        """Update encoder display from telemetry."""
        if encoder_id == self.encoder_id_spin.value():
            if hasattr(data, 'count'):
                self.encoder_count_label.setText(str(data.count))
            if hasattr(data, 'velocity'):
                self.encoder_velocity_label.setText(f"{data.velocity:.1f}")

    # ==================== Ultrasonic Handlers ====================

    def _on_ultrasonic_attach(self) -> None:
        """Attach ultrasonic sensor."""
        sensor_id = self.ultrasonic_id_spin.value()
        self.controller.ultrasonic_attach(sensor_id)
        self.signals.status_message.emit(f"Attached ultrasonic sensor {sensor_id}")

    def _on_ultrasonic_read(self) -> None:
        """Trigger ultrasonic read."""
        sensor_id = self.ultrasonic_id_spin.value()
        self.controller.ultrasonic_read(sensor_id)

    def _update_ultrasonic_display(self, sensor_id: int, distance_cm: float) -> None:
        """Update ultrasonic display."""
        if sensor_id == self.ultrasonic_id_spin.value():
            if distance_cm < 0:
                self.ultrasonic_distance_label.setText("--")
                self.ultrasonic_status_label.setText("No echo")
            else:
                self.ultrasonic_distance_label.setText(f"{distance_cm:.1f}")
                self.ultrasonic_status_label.setText("")
