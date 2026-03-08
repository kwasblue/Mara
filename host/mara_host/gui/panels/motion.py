# mara_host/gui/panels/motion.py
"""
Motion Primitives Panel.

High-level motion commands: drive straight, turn, arc movements.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "motion",
    "label": "Motion",
    "order": 21,
}

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QScrollArea,
    QFrame,
    QProgressBar,
    QComboBox,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings


class MotionPanel(QWidget):
    """Motion Primitives Panel."""

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Header
        header = QLabel("Motion Primitives")
        header.setStyleSheet("font-weight: bold; font-size: 16px; color: #FAFAFA;")
        layout.addWidget(header)

        info = QLabel("Execute high-level motion commands. Robot must be armed and active.")
        info.setStyleSheet("color: #71717A;")
        layout.addWidget(info)

        # Drive Straight
        layout.addWidget(self._create_drive_straight_group())

        # Turn in Place
        layout.addWidget(self._create_turn_group())

        # Arc Movement
        layout.addWidget(self._create_arc_group())

        # Velocity Control
        layout.addWidget(self._create_velocity_group())

        # Quick actions
        layout.addWidget(self._create_quick_actions())

        # Emergency stop
        estop_btn = QPushButton("EMERGENCY STOP")
        estop_btn.setObjectName("danger")
        estop_btn.setMinimumHeight(52)
        estop_btn.setStyleSheet("font-size: 15px; font-weight: 600;")
        estop_btn.clicked.connect(self._estop)
        layout.addWidget(estop_btn)

        layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _create_drive_straight_group(self) -> QGroupBox:
        """Create drive straight control group."""
        group = QGroupBox("Drive Straight")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Distance and speed
        params = QGridLayout()

        params.addWidget(QLabel("Distance:"), 0, 0)
        self.drive_distance_spin = QDoubleSpinBox()
        self.drive_distance_spin.setRange(-10.0, 10.0)
        self.drive_distance_spin.setValue(1.0)
        self.drive_distance_spin.setSingleStep(0.1)
        self.drive_distance_spin.setSuffix(" m")
        params.addWidget(self.drive_distance_spin, 0, 1)

        params.addWidget(QLabel("Speed:"), 0, 2)
        self.drive_speed_spin = QDoubleSpinBox()
        self.drive_speed_spin.setRange(0.01, 2.0)
        self.drive_speed_spin.setValue(0.5)
        self.drive_speed_spin.setSingleStep(0.1)
        self.drive_speed_spin.setSuffix(" m/s")
        params.addWidget(self.drive_speed_spin, 0, 3)

        layout.addLayout(params)

        # Quick distance buttons
        btn_row = QHBoxLayout()
        for dist in [-1.0, -0.5, -0.1, 0.1, 0.5, 1.0]:
            sign = "+" if dist > 0 else ""
            btn = QPushButton(f"{sign}{dist}m")
            btn.setObjectName("secondary")
            btn.clicked.connect(lambda _, d=dist: self._drive_quick(d))
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)

        # Execute button
        execute_btn = QPushButton("Drive")
        execute_btn.setObjectName("primary")
        execute_btn.clicked.connect(self._drive_straight)
        layout.addWidget(execute_btn)

        return group

    def _create_turn_group(self) -> QGroupBox:
        """Create turn in place control group."""
        group = QGroupBox("Turn in Place")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Angle and speed
        params = QGridLayout()

        params.addWidget(QLabel("Angle:"), 0, 0)
        self.turn_angle_spin = QDoubleSpinBox()
        self.turn_angle_spin.setRange(-360.0, 360.0)
        self.turn_angle_spin.setValue(90.0)
        self.turn_angle_spin.setSingleStep(15.0)
        self.turn_angle_spin.setSuffix("°")
        params.addWidget(self.turn_angle_spin, 0, 1)

        params.addWidget(QLabel("Speed:"), 0, 2)
        self.turn_speed_spin = QDoubleSpinBox()
        self.turn_speed_spin.setRange(0.1, 5.0)
        self.turn_speed_spin.setValue(1.0)
        self.turn_speed_spin.setSingleStep(0.1)
        self.turn_speed_spin.setSuffix(" rad/s")
        params.addWidget(self.turn_speed_spin, 0, 3)

        layout.addLayout(params)

        # Quick angle buttons
        btn_row = QHBoxLayout()
        for angle in [-180, -90, -45, 45, 90, 180]:
            sign = "+" if angle > 0 else ""
            btn = QPushButton(f"{sign}{angle}°")
            btn.setObjectName("secondary")
            btn.clicked.connect(lambda _, a=angle: self._turn_quick(a))
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)

        # Execute button
        execute_btn = QPushButton("Turn")
        execute_btn.setObjectName("primary")
        execute_btn.clicked.connect(self._turn)
        layout.addWidget(execute_btn)

        return group

    def _create_arc_group(self) -> QGroupBox:
        """Create arc movement control group."""
        group = QGroupBox("Arc Movement")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Parameters
        params = QGridLayout()

        params.addWidget(QLabel("Radius:"), 0, 0)
        self.arc_radius_spin = QDoubleSpinBox()
        self.arc_radius_spin.setRange(0.1, 10.0)
        self.arc_radius_spin.setValue(1.0)
        self.arc_radius_spin.setSingleStep(0.1)
        self.arc_radius_spin.setSuffix(" m")
        params.addWidget(self.arc_radius_spin, 0, 1)

        params.addWidget(QLabel("Angle:"), 0, 2)
        self.arc_angle_spin = QDoubleSpinBox()
        self.arc_angle_spin.setRange(-360.0, 360.0)
        self.arc_angle_spin.setValue(90.0)
        self.arc_angle_spin.setSingleStep(15.0)
        self.arc_angle_spin.setSuffix("°")
        params.addWidget(self.arc_angle_spin, 0, 3)

        params.addWidget(QLabel("Speed:"), 1, 0)
        self.arc_speed_spin = QDoubleSpinBox()
        self.arc_speed_spin.setRange(0.01, 2.0)
        self.arc_speed_spin.setValue(0.3)
        self.arc_speed_spin.setSingleStep(0.1)
        self.arc_speed_spin.setSuffix(" m/s")
        params.addWidget(self.arc_speed_spin, 1, 1)

        layout.addLayout(params)

        # Execute button
        execute_btn = QPushButton("Execute Arc")
        execute_btn.setObjectName("primary")
        execute_btn.clicked.connect(self._arc)
        layout.addWidget(execute_btn)

        return group

    def _create_velocity_group(self) -> QGroupBox:
        """Create velocity control group."""
        group = QGroupBox("Velocity Setpoint")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        params = QGridLayout()

        params.addWidget(QLabel("Linear (vx):"), 0, 0)
        self.vel_linear_spin = QDoubleSpinBox()
        self.vel_linear_spin.setRange(-2.0, 2.0)
        self.vel_linear_spin.setValue(0.0)
        self.vel_linear_spin.setSingleStep(0.1)
        self.vel_linear_spin.setSuffix(" m/s")
        params.addWidget(self.vel_linear_spin, 0, 1)

        params.addWidget(QLabel("Angular (ω):"), 0, 2)
        self.vel_angular_spin = QDoubleSpinBox()
        self.vel_angular_spin.setRange(-5.0, 5.0)
        self.vel_angular_spin.setValue(0.0)
        self.vel_angular_spin.setSingleStep(0.1)
        self.vel_angular_spin.setSuffix(" rad/s")
        params.addWidget(self.vel_angular_spin, 0, 3)

        layout.addLayout(params)

        btn_row = QHBoxLayout()

        set_btn = QPushButton("Set Velocity")
        set_btn.setObjectName("primary")
        set_btn.clicked.connect(self._set_velocity)
        btn_row.addWidget(set_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.setObjectName("secondary")
        stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(stop_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        return group

    def _create_quick_actions(self) -> QGroupBox:
        """Create quick action buttons."""
        group = QGroupBox("Quick Actions")
        layout = QHBoxLayout(group)

        actions = [
            ("Forward 1m", lambda: self._drive_quick(1.0)),
            ("Back 1m", lambda: self._drive_quick(-1.0)),
            ("Left 90°", lambda: self._turn_quick(90)),
            ("Right 90°", lambda: self._turn_quick(-90)),
            ("U-Turn", lambda: self._turn_quick(180)),
        ]

        for label, callback in actions:
            btn = QPushButton(label)
            btn.setObjectName("secondary")
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        return group

    def _setup_connections(self) -> None:
        self.signals.connection_changed.connect(self._on_connection_changed)

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        # Enable/disable all controls based on connection
        pass  # Widgets handle this automatically

    def _drive_straight(self) -> None:
        distance = self.drive_distance_spin.value()
        speed = self.drive_speed_spin.value()
        self.controller.send_command(
            "CMD_MOTION_DRIVE_STRAIGHT",
            {"distance_m": distance, "speed_mps": speed}
        )
        self.signals.status_message.emit(f"Driving {distance}m at {speed}m/s")

    def _drive_quick(self, distance: float) -> None:
        speed = self.drive_speed_spin.value()
        self.controller.send_command(
            "CMD_MOTION_DRIVE_STRAIGHT",
            {"distance_m": distance, "speed_mps": speed}
        )
        self.signals.status_message.emit(f"Driving {distance}m")

    def _turn(self) -> None:
        angle = self.turn_angle_spin.value()
        speed = self.turn_speed_spin.value()
        self.controller.send_command(
            "CMD_MOTION_TURN",
            {"angle_deg": angle, "speed_rps": speed}
        )
        self.signals.status_message.emit(f"Turning {angle}°")

    def _turn_quick(self, angle: float) -> None:
        speed = self.turn_speed_spin.value()
        self.controller.send_command(
            "CMD_MOTION_TURN",
            {"angle_deg": angle, "speed_rps": speed}
        )
        self.signals.status_message.emit(f"Turning {angle}°")

    def _arc(self) -> None:
        radius = self.arc_radius_spin.value()
        angle = self.arc_angle_spin.value()
        speed = self.arc_speed_spin.value()
        self.controller.send_command(
            "CMD_MOTION_ARC",
            {"radius_m": radius, "angle_deg": angle, "speed_mps": speed}
        )
        self.signals.status_message.emit(f"Arc r={radius}m, θ={angle}°")

    def _set_velocity(self) -> None:
        vx = self.vel_linear_spin.value()
        omega = self.vel_angular_spin.value()
        self.controller.set_velocity(vx, omega)

    def _stop(self) -> None:
        self.vel_linear_spin.setValue(0.0)
        self.vel_angular_spin.setValue(0.0)
        self.controller.stop_motion()

    def _estop(self) -> None:
        self.controller.estop()
        self.signals.status_message.emit("Emergency stop activated")
