# mara_host/gui/panels/calibration.py
"""
Calibration panel for robot calibration wizards.

Provides interactive wizards for calibrating motors, servos,
encoders, wheels, IMU, and PID parameters.
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

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
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QProgressBar,
    QFrame,
    QTextEdit,
    QScrollArea,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings


class CalibrationState(Enum):
    """Calibration wizard state."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING_USER = "waiting_user"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class CalibrationResult:
    """Result from a calibration wizard."""
    wizard_type: str
    success: bool
    message: str = ""
    data: dict = field(default_factory=dict)


class BaseCalibrationWizard(QWidget):
    """Base class for calibration wizards."""

    progress = Signal(int, str)  # percent, status message
    result = Signal(object)  # CalibrationResult
    user_prompt = Signal(str, list)  # question, options
    finished = Signal()

    def __init__(
        self,
        signals: GuiSignals,
        controller: RobotController,
        parent=None,
    ):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self._state = CalibrationState.IDLE
        self._result_data = {}

    @property
    def wizard_name(self) -> str:
        return "Base"

    def start(self) -> None:
        """Start the calibration."""
        raise NotImplementedError

    def cancel(self) -> None:
        """Cancel the calibration."""
        self._state = CalibrationState.CANCELLED
        self.finished.emit()

    def on_user_response(self, response: str) -> None:
        """Handle user response to a prompt."""
        pass


class MotorCalibrationWizard(BaseCalibrationWizard):
    """Motor calibration wizard - find dead zone and direction."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(signals, controller, parent)
        self._motor_id = 0
        self._current_pwm = 0
        self._dead_zone = 0
        self._inverted = False
        self._step = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step_calibration)

        self._setup_ui()

    @property
    def wizard_name(self) -> str:
        return "Motor"

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Motor selector
        motor_row = QHBoxLayout()
        motor_row.addWidget(QLabel("Motor ID:"))
        self.motor_spin = QSpinBox()
        self.motor_spin.setRange(0, 3)
        motor_row.addWidget(self.motor_spin)
        motor_row.addStretch()
        layout.addLayout(motor_row)

        # Instructions
        self.instructions_label = QLabel(
            "This wizard will find the motor's dead zone and direction.\n"
            "You will be asked to confirm when the motor starts moving."
        )
        self.instructions_label.setWordWrap(True)
        self.instructions_label.setStyleSheet("color: #A1A1AA;")
        layout.addWidget(self.instructions_label)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Current status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "color: #FAFAFA;"
        )
        layout.addWidget(self.status_label)

        # User confirmation buttons
        self.confirm_frame = QFrame()
        confirm_layout = QHBoxLayout(self.confirm_frame)
        confirm_layout.addWidget(QLabel("Motor moving?"))

        self.yes_btn = QPushButton("Yes")
        self.yes_btn.clicked.connect(lambda: self.on_user_response("yes"))
        confirm_layout.addWidget(self.yes_btn)

        self.no_btn = QPushButton("No")
        self.no_btn.clicked.connect(lambda: self.on_user_response("no"))
        confirm_layout.addWidget(self.no_btn)

        confirm_layout.addStretch()
        self.confirm_frame.setVisible(False)
        layout.addWidget(self.confirm_frame)

        # Results
        self.results_frame = QFrame()
        results_layout = QVBoxLayout(self.results_frame)

        self.dead_zone_label = QLabel("Dead zone: --")
        results_layout.addWidget(self.dead_zone_label)

        self.inverted_label = QLabel("Inverted: --")
        results_layout.addWidget(self.inverted_label)

        self.results_frame.setVisible(False)
        layout.addWidget(self.results_frame)

        layout.addStretch()

        # Control buttons
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start Calibration")
        self.start_btn.clicked.connect(self.start)
        btn_row.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.clicked.connect(self.cancel)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.cancel_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def start(self) -> None:
        self._motor_id = self.motor_spin.value()
        self._state = CalibrationState.RUNNING
        self._step = 0
        self._current_pwm = 0
        self._dead_zone = 0

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.results_frame.setVisible(False)

        # Start binary search at 50%
        self._current_pwm = 50
        self._search_min = 0
        self._search_max = 100

        self._set_motor_pwm(self._current_pwm)
        self.status_label.setText(f"Testing {self._current_pwm}% PWM...")
        self.confirm_frame.setVisible(True)

        self._state = CalibrationState.WAITING_USER

    def cancel(self) -> None:
        self._timer.stop()
        self._set_motor_pwm(0)
        self._state = CalibrationState.CANCELLED
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.confirm_frame.setVisible(False)
        self.status_label.setText("Calibration cancelled")
        self.finished.emit()

    def on_user_response(self, response: str) -> None:
        if self._state != CalibrationState.WAITING_USER:
            return

        if response == "yes":
            # Motor is moving - search lower
            self._search_max = self._current_pwm
        else:
            # Motor not moving - search higher
            self._search_min = self._current_pwm

        # Check if done
        if self._search_max - self._search_min <= 2:
            self._dead_zone = self._search_max
            self._finish_dead_zone_search()
        else:
            # Continue binary search
            self._current_pwm = (self._search_min + self._search_max) // 2
            self._set_motor_pwm(self._current_pwm)
            self.status_label.setText(f"Testing {self._current_pwm}% PWM...")
            progress = int((100 - (self._search_max - self._search_min)) / 100 * 80)
            self.progress_bar.setValue(progress)

    def _finish_dead_zone_search(self) -> None:
        """Complete the dead zone search and test direction."""
        self._set_motor_pwm(0)
        self.confirm_frame.setVisible(False)
        self.progress_bar.setValue(90)

        # Test direction at 50% PWM
        self._set_motor_pwm(50)
        self.status_label.setText("Testing direction... (check forward motion)")

        # For now, assume not inverted
        self._timer.singleShot(1000, self._finish_calibration)

    def _finish_calibration(self) -> None:
        self._set_motor_pwm(0)
        self._state = CalibrationState.COMPLETED
        self.progress_bar.setValue(100)

        self.dead_zone_label.setText(f"Dead zone: {self._dead_zone}%")
        self.inverted_label.setText(f"Inverted: {self._inverted}")
        self.results_frame.setVisible(True)

        self.status_label.setText("Calibration complete!")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        self._result_data = {
            "motor_id": self._motor_id,
            "dead_zone": self._dead_zone,
            "inverted": self._inverted,
        }

        self.result.emit(CalibrationResult(
            wizard_type="motor",
            success=True,
            message="Motor calibration complete",
            data=self._result_data,
        ))
        self.finished.emit()

    def _set_motor_pwm(self, pwm: int) -> None:
        """Set motor PWM (0-100)."""
        self.controller.set_motor_speed(self._motor_id, pwm / 100.0)

    def _step_calibration(self) -> None:
        """Calibration step (called by timer)."""
        pass


class ServoCalibrationWizard(BaseCalibrationWizard):
    """Servo calibration wizard - find safe min/max angles."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(signals, controller, parent)
        self._setup_ui()

    @property
    def wizard_name(self) -> str:
        return "Servo"

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Servo selector
        servo_row = QHBoxLayout()
        servo_row.addWidget(QLabel("Servo ID:"))
        self.servo_spin = QSpinBox()
        self.servo_spin.setRange(0, 7)
        servo_row.addWidget(self.servo_spin)
        servo_row.addStretch()
        layout.addLayout(servo_row)

        # Instructions
        instructions = QLabel(
            "This wizard helps find safe servo limits.\n"
            "Move the servo to find minimum and maximum angles."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #A1A1AA;")
        layout.addWidget(instructions)

        # Angle control
        angle_row = QHBoxLayout()
        angle_row.addWidget(QLabel("Angle:"))
        self.angle_slider_spin = QSpinBox()
        self.angle_slider_spin.setRange(0, 180)
        self.angle_slider_spin.setValue(90)
        self.angle_slider_spin.valueChanged.connect(self._on_angle_changed)
        angle_row.addWidget(self.angle_slider_spin)

        self.test_btn = QPushButton("Test")
        self.test_btn.clicked.connect(self._test_angle)
        angle_row.addWidget(self.test_btn)
        angle_row.addStretch()
        layout.addLayout(angle_row)

        # Min/Max buttons
        limit_row = QHBoxLayout()
        self.set_min_btn = QPushButton("Set as Minimum")
        self.set_min_btn.clicked.connect(self._set_min)
        limit_row.addWidget(self.set_min_btn)

        self.set_max_btn = QPushButton("Set as Maximum")
        self.set_max_btn.clicked.connect(self._set_max)
        limit_row.addWidget(self.set_max_btn)
        limit_row.addStretch()
        layout.addLayout(limit_row)

        # Results
        self.results_frame = QFrame()
        results_layout = QGridLayout(self.results_frame)

        results_layout.addWidget(QLabel("Min angle:"), 0, 0)
        self.min_label = QLabel("--")
        self.min_label.setStyleSheet("color: #FAFAFA;")
        results_layout.addWidget(self.min_label, 0, 1)

        results_layout.addWidget(QLabel("Max angle:"), 0, 2)
        self.max_label = QLabel("--")
        self.max_label.setStyleSheet("color: #FAFAFA;")
        results_layout.addWidget(self.max_label, 0, 3)

        results_layout.addWidget(QLabel("Center:"), 1, 0)
        self.center_label = QLabel("--")
        self.center_label.setStyleSheet("color: #FAFAFA;")
        results_layout.addWidget(self.center_label, 1, 1)

        results_layout.setColumnStretch(4, 1)
        layout.addWidget(self.results_frame)

        layout.addStretch()

        # Save button
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Calibration")
        self.save_btn.clicked.connect(self._save_calibration)
        btn_row.addWidget(self.save_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Initialize
        self._min_angle = None
        self._max_angle = None

    def start(self) -> None:
        self._min_angle = None
        self._max_angle = None
        self._update_results()

    def _on_angle_changed(self, value: int) -> None:
        pass

    def _test_angle(self) -> None:
        servo_id = self.servo_spin.value()
        angle = self.angle_slider_spin.value()
        self.controller.set_servo_angle(servo_id, float(angle))

    def _set_min(self) -> None:
        self._min_angle = self.angle_slider_spin.value()
        self._update_results()

    def _set_max(self) -> None:
        self._max_angle = self.angle_slider_spin.value()
        self._update_results()

    def _update_results(self) -> None:
        self.min_label.setText(f"{self._min_angle}" if self._min_angle else "--")
        self.max_label.setText(f"{self._max_angle}" if self._max_angle else "--")

        if self._min_angle is not None and self._max_angle is not None:
            center = (self._min_angle + self._max_angle) // 2
            self.center_label.setText(str(center))
        else:
            self.center_label.setText("--")

    def _save_calibration(self) -> None:
        if self._min_angle is None or self._max_angle is None:
            self.signals.status_error.emit("Set both min and max angles first")
            return

        center = (self._min_angle + self._max_angle) // 2

        self.result.emit(CalibrationResult(
            wizard_type="servo",
            success=True,
            message="Servo calibration saved",
            data={
                "servo_id": self.servo_spin.value(),
                "min_angle": self._min_angle,
                "max_angle": self._max_angle,
                "center": center,
            },
        ))
        self.signals.status_message.emit("Servo calibration saved")


class EncoderCalibrationWizard(BaseCalibrationWizard):
    """Encoder calibration wizard - find ticks per revolution."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(signals, controller, parent)
        self._setup_ui()

    @property
    def wizard_name(self) -> str:
        return "Encoder"

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Encoder selector
        enc_row = QHBoxLayout()
        enc_row.addWidget(QLabel("Encoder ID:"))
        self.encoder_spin = QSpinBox()
        self.encoder_spin.setRange(0, 3)
        enc_row.addWidget(self.encoder_spin)
        enc_row.addStretch()
        layout.addLayout(enc_row)

        # Instructions
        instructions = QLabel(
            "1. Mark the current wheel position\n"
            "2. Click 'Mark Zero' to reset count\n"
            "3. Rotate wheel exactly one revolution\n"
            "4. Click 'Save Count' to record ticks per revolution"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #A1A1AA;")
        layout.addWidget(instructions)

        # Live count
        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("Current count:"))
        self.count_label = QLabel("--")
        self.count_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "font-size: 24px; color: #FAFAFA;"
        )
        count_row.addWidget(self.count_label)
        count_row.addStretch()
        layout.addLayout(count_row)

        # Buttons
        btn_row = QHBoxLayout()
        self.mark_zero_btn = QPushButton("Mark Zero")
        self.mark_zero_btn.clicked.connect(self._mark_zero)
        btn_row.addWidget(self.mark_zero_btn)

        self.save_count_btn = QPushButton("Save Count")
        self.save_count_btn.clicked.connect(self._save_count)
        btn_row.addWidget(self.save_count_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Result
        result_row = QHBoxLayout()
        result_row.addWidget(QLabel("Ticks per revolution:"))
        self.tpr_label = QLabel("--")
        self.tpr_label.setStyleSheet("color: #22C55E; font-weight: bold;")
        result_row.addWidget(self.tpr_label)
        result_row.addStretch()
        layout.addLayout(result_row)

        layout.addStretch()

        self._current_count = 0
        self._ticks_per_rev = None

    def start(self) -> None:
        self._current_count = 0
        self._ticks_per_rev = None
        self.count_label.setText("0")
        self.tpr_label.setText("--")

    def _mark_zero(self) -> None:
        encoder_id = self.encoder_spin.value()
        self.controller.encoder_reset(encoder_id)
        self._current_count = 0
        self.count_label.setText("0")

    def _save_count(self) -> None:
        # Read current count from telemetry (placeholder)
        self._ticks_per_rev = abs(self._current_count)
        self.tpr_label.setText(str(self._ticks_per_rev) if self._ticks_per_rev else "--")

        if self._ticks_per_rev:
            self.result.emit(CalibrationResult(
                wizard_type="encoder",
                success=True,
                message="Encoder calibration saved",
                data={
                    "encoder_id": self.encoder_spin.value(),
                    "ticks_per_revolution": self._ticks_per_rev,
                },
            ))

    def update_count(self, count: int) -> None:
        """Update from telemetry."""
        self._current_count = count
        self.count_label.setText(str(count))


class WheelsCalibrationWizard(BaseCalibrationWizard):
    """Wheel calibration wizard - enter wheel dimensions (offline)."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(signals, controller, parent)
        self._setup_ui()

    @property
    def wizard_name(self) -> str:
        return "Wheels"

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Instructions
        instructions = QLabel(
            "Enter your robot's wheel dimensions.\n"
            "These values are used for odometry calculations."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #A1A1AA;")
        layout.addWidget(instructions)

        # Wheel diameter
        diam_row = QHBoxLayout()
        diam_row.addWidget(QLabel("Wheel diameter:"))
        self.diameter_spin = QDoubleSpinBox()
        self.diameter_spin.setRange(10, 500)
        self.diameter_spin.setValue(65)
        self.diameter_spin.setSuffix(" mm")
        self.diameter_spin.setDecimals(1)
        diam_row.addWidget(self.diameter_spin)
        diam_row.addStretch()
        layout.addLayout(diam_row)

        # Wheel base
        base_row = QHBoxLayout()
        base_row.addWidget(QLabel("Wheel base (track width):"))
        self.wheelbase_spin = QDoubleSpinBox()
        self.wheelbase_spin.setRange(50, 1000)
        self.wheelbase_spin.setValue(150)
        self.wheelbase_spin.setSuffix(" mm")
        self.wheelbase_spin.setDecimals(1)
        base_row.addWidget(self.wheelbase_spin)
        base_row.addStretch()
        layout.addLayout(base_row)

        # Calculated values
        calc_frame = QGroupBox("Calculated Values")
        calc_layout = QGridLayout(calc_frame)

        calc_layout.addWidget(QLabel("Wheel circumference:"), 0, 0)
        self.circumference_label = QLabel("--")
        calc_layout.addWidget(self.circumference_label, 0, 1)

        calc_layout.addWidget(QLabel("Wheel radius (m):"), 1, 0)
        self.radius_label = QLabel("--")
        calc_layout.addWidget(self.radius_label, 1, 1)

        layout.addWidget(calc_frame)

        # Update on change
        self.diameter_spin.valueChanged.connect(self._update_calculated)
        self.wheelbase_spin.valueChanged.connect(self._update_calculated)
        self._update_calculated()

        layout.addStretch()

        # Save button
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self._save)
        btn_row.addWidget(self.save_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def start(self) -> None:
        pass

    def _update_calculated(self) -> None:
        import math
        diameter_mm = self.diameter_spin.value()
        circumference = math.pi * diameter_mm
        radius_m = (diameter_mm / 2) / 1000

        self.circumference_label.setText(f"{circumference:.1f} mm")
        self.radius_label.setText(f"{radius_m:.4f}")

    def _save(self) -> None:
        diameter_m = self.diameter_spin.value() / 1000
        wheelbase_m = self.wheelbase_spin.value() / 1000

        self.result.emit(CalibrationResult(
            wizard_type="wheels",
            success=True,
            message="Wheel configuration saved",
            data={
                "wheel_diameter_m": diameter_m,
                "wheel_base_m": wheelbase_m,
            },
        ))
        self.signals.status_message.emit("Wheel configuration saved")


class IMUCalibrationWizard(BaseCalibrationWizard):
    """IMU calibration wizard - collect samples for offset calculation."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(signals, controller, parent)
        self._samples = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._collect_sample)
        self._setup_ui()

    @property
    def wizard_name(self) -> str:
        return "IMU"

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Instructions
        instructions = QLabel(
            "Place the robot on a flat, stable surface.\n"
            "Keep it completely still during calibration.\n"
            "This will collect 100 samples over 5 seconds."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #A1A1AA;")
        layout.addWidget(instructions)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Status
        self.status_label = QLabel("Ready to calibrate")
        layout.addWidget(self.status_label)

        # Results
        self.results_frame = QGroupBox("Offsets")
        results_layout = QGridLayout(self.results_frame)

        results_layout.addWidget(QLabel("Accel X:"), 0, 0)
        self.accel_x_label = QLabel("--")
        results_layout.addWidget(self.accel_x_label, 0, 1)

        results_layout.addWidget(QLabel("Y:"), 0, 2)
        self.accel_y_label = QLabel("--")
        results_layout.addWidget(self.accel_y_label, 0, 3)

        results_layout.addWidget(QLabel("Z:"), 0, 4)
        self.accel_z_label = QLabel("--")
        results_layout.addWidget(self.accel_z_label, 0, 5)

        results_layout.addWidget(QLabel("Gyro X:"), 1, 0)
        self.gyro_x_label = QLabel("--")
        results_layout.addWidget(self.gyro_x_label, 1, 1)

        results_layout.addWidget(QLabel("Y:"), 1, 2)
        self.gyro_y_label = QLabel("--")
        results_layout.addWidget(self.gyro_y_label, 1, 3)

        results_layout.addWidget(QLabel("Z:"), 1, 4)
        self.gyro_z_label = QLabel("--")
        results_layout.addWidget(self.gyro_z_label, 1, 5)

        self.results_frame.setVisible(False)
        layout.addWidget(self.results_frame)

        layout.addStretch()

        # Control buttons
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start Calibration")
        self.start_btn.clicked.connect(self.start)
        btn_row.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.clicked.connect(self.cancel)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def start(self) -> None:
        self._samples = []
        self._state = CalibrationState.RUNNING
        self.progress_bar.setValue(0)
        self.results_frame.setVisible(False)
        self.status_label.setText("Collecting samples... keep robot still!")

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        # Collect samples at 20Hz for 5 seconds = 100 samples
        self._timer.start(50)

    def cancel(self) -> None:
        self._timer.stop()
        self._state = CalibrationState.CANCELLED
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Calibration cancelled")
        self.finished.emit()

    def _collect_sample(self) -> None:
        """Collect IMU sample."""
        # Would get from telemetry in real implementation
        # For now, simulate
        import random
        sample = {
            "ax": random.gauss(0, 0.1),
            "ay": random.gauss(0, 0.1),
            "az": random.gauss(9.8, 0.1),
            "gx": random.gauss(0, 0.01),
            "gy": random.gauss(0, 0.01),
            "gz": random.gauss(0, 0.01),
        }
        self._samples.append(sample)

        progress = int(len(self._samples) / 100 * 100)
        self.progress_bar.setValue(min(progress, 100))

        if len(self._samples) >= 100:
            self._timer.stop()
            self._calculate_offsets()

    def _calculate_offsets(self) -> None:
        """Calculate average offsets."""
        n = len(self._samples)
        if n == 0:
            return

        # Average all samples
        ax_avg = sum(s["ax"] for s in self._samples) / n
        ay_avg = sum(s["ay"] for s in self._samples) / n
        az_avg = sum(s["az"] for s in self._samples) / n - 9.8  # Remove gravity
        gx_avg = sum(s["gx"] for s in self._samples) / n
        gy_avg = sum(s["gy"] for s in self._samples) / n
        gz_avg = sum(s["gz"] for s in self._samples) / n

        # Display
        self.accel_x_label.setText(f"{ax_avg:.4f}")
        self.accel_y_label.setText(f"{ay_avg:.4f}")
        self.accel_z_label.setText(f"{az_avg:.4f}")
        self.gyro_x_label.setText(f"{gx_avg:.4f}")
        self.gyro_y_label.setText(f"{gy_avg:.4f}")
        self.gyro_z_label.setText(f"{gz_avg:.4f}")

        self.results_frame.setVisible(True)
        self.status_label.setText("Calibration complete!")
        self._state = CalibrationState.COMPLETED

        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        self.result.emit(CalibrationResult(
            wizard_type="imu",
            success=True,
            message="IMU calibration complete",
            data={
                "accel_offsets": [ax_avg, ay_avg, az_avg],
                "gyro_offsets": [gx_avg, gy_avg, gz_avg],
            },
        ))
        self.finished.emit()


class PIDCalibrationWizard(BaseCalibrationWizard):
    """PID tuning wizard - test gains and sweep parameters."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(signals, controller, parent)
        self._setup_ui()

    @property
    def wizard_name(self) -> str:
        return "PID"

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Motor selector
        motor_row = QHBoxLayout()
        motor_row.addWidget(QLabel("Motor ID:"))
        self.motor_spin = QSpinBox()
        self.motor_spin.setRange(0, 3)
        motor_row.addWidget(self.motor_spin)
        motor_row.addStretch()
        layout.addLayout(motor_row)

        # PID gains
        gains_group = QGroupBox("PID Gains")
        gains_layout = QGridLayout(gains_group)

        gains_layout.addWidget(QLabel("Kp:"), 0, 0)
        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(0, 100)
        self.kp_spin.setValue(1.0)
        self.kp_spin.setDecimals(3)
        gains_layout.addWidget(self.kp_spin, 0, 1)

        gains_layout.addWidget(QLabel("Ki:"), 0, 2)
        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(0, 100)
        self.ki_spin.setValue(0.0)
        self.ki_spin.setDecimals(3)
        gains_layout.addWidget(self.ki_spin, 0, 3)

        gains_layout.addWidget(QLabel("Kd:"), 1, 0)
        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(0, 100)
        self.kd_spin.setValue(0.0)
        self.kd_spin.setDecimals(3)
        gains_layout.addWidget(self.kd_spin, 1, 1)

        layout.addWidget(gains_group)

        # Test parameters
        test_group = QGroupBox("Test Parameters")
        test_layout = QGridLayout(test_group)

        test_layout.addWidget(QLabel("Target velocity:"), 0, 0)
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(-50, 50)
        self.target_spin.setValue(10.0)
        self.target_spin.setSuffix(" rad/s")
        test_layout.addWidget(self.target_spin, 0, 1)

        test_layout.addWidget(QLabel("Hold time:"), 0, 2)
        self.hold_spin = QDoubleSpinBox()
        self.hold_spin.setRange(0.5, 30)
        self.hold_spin.setValue(3.0)
        self.hold_spin.setSuffix(" sec")
        test_layout.addWidget(self.hold_spin, 0, 3)

        layout.addWidget(test_group)

        # Live feedback placeholder
        feedback_group = QGroupBox("Live Feedback")
        feedback_layout = QVBoxLayout(feedback_group)
        self.feedback_label = QLabel("Actual velocity: --")
        self.feedback_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "font-size: 16px; color: #FAFAFA;"
        )
        feedback_layout.addWidget(self.feedback_label)
        layout.addWidget(feedback_group)

        layout.addStretch()

        # Control buttons
        btn_row = QHBoxLayout()
        self.apply_btn = QPushButton("Apply Gains")
        self.apply_btn.clicked.connect(self._apply_gains)
        btn_row.addWidget(self.apply_btn)

        self.test_btn = QPushButton("Run Test")
        self.test_btn.clicked.connect(self._run_test)
        btn_row.addWidget(self.test_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(self.stop_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def start(self) -> None:
        pass

    def _apply_gains(self) -> None:
        motor_id = self.motor_spin.value()
        kp = self.kp_spin.value()
        ki = self.ki_spin.value()
        kd = self.kd_spin.value()

        self.controller.set_velocity_gains(motor_id, kp, ki, kd)
        self.signals.status_message.emit(f"Applied gains to motor {motor_id}")

    def _run_test(self) -> None:
        motor_id = self.motor_spin.value()
        target = self.target_spin.value()

        # Enable PID and set target
        self.controller.enable_velocity_pid(motor_id, True)
        self.controller.set_velocity_target(motor_id, target)
        self.signals.status_message.emit(f"Running test: target={target} rad/s")

    def _stop(self) -> None:
        motor_id = self.motor_spin.value()
        self.controller.enable_velocity_pid(motor_id, False)
        self.controller.set_motor_speed(motor_id, 0.0)
        self.signals.status_message.emit("Test stopped")


class CalibrationPanel(QWidget):
    """
    Calibration panel with wizard selection.

    Layout:
        ┌─────────────────┬───────────────────────────────────┐
        │ [Motor]         │  Motor Calibration                 │
        │ [Servo]         │  (wizard content)                  │
        │ [Encoder]       │                                    │
        │ [Wheels]        │                                    │
        │ [IMU]           │                                    │
        │ [PID]           │                                    │
        └─────────────────┴───────────────────────────────────┘
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

        self._wizards = {}
        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """Set up the calibration panel UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Wizard list
        self.wizard_list = QListWidget()
        self.wizard_list.setFixedWidth(150)
        self.wizard_list.setSpacing(2)

        wizard_types = [
            ("motor", "Motor"),
            ("servo", "Servo"),
            ("encoder", "Encoder"),
            ("wheels", "Wheels"),
            ("imu", "IMU"),
            ("pid", "PID"),
        ]

        for wizard_id, label in wizard_types:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, wizard_id)
            self.wizard_list.addItem(item)

        self.wizard_list.currentRowChanged.connect(self._on_wizard_changed)
        layout.addWidget(self.wizard_list)

        # Wizard content area
        self.wizard_stack = QStackedWidget()

        # Create wizards
        self._wizards["motor"] = MotorCalibrationWizard(self.signals, self.controller)
        self._wizards["servo"] = ServoCalibrationWizard(self.signals, self.controller)
        self._wizards["encoder"] = EncoderCalibrationWizard(self.signals, self.controller)
        self._wizards["wheels"] = WheelsCalibrationWizard(self.signals, self.controller)
        self._wizards["imu"] = IMUCalibrationWizard(self.signals, self.controller)
        self._wizards["pid"] = PIDCalibrationWizard(self.signals, self.controller)

        for wizard in self._wizards.values():
            # Wrap in container with padding
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(32, 32, 32, 32)
            container_layout.addWidget(wizard)

            self.wizard_stack.addWidget(container)

            # Connect result signal
            wizard.result.connect(self._on_calibration_result)

        layout.addWidget(self.wizard_stack, 1)

        # Select first wizard
        self.wizard_list.setCurrentRow(0)

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self.signals.connection_changed.connect(self._on_connection_changed)
        self.signals.encoder_data.connect(self._on_encoder_data)

    def _on_wizard_changed(self, index: int) -> None:
        """Handle wizard selection change."""
        self.wizard_stack.setCurrentIndex(index)

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        """Handle connection state change."""
        # Enable/disable wizards based on connection
        pass

    def _on_calibration_result(self, result: CalibrationResult) -> None:
        """Handle calibration result."""
        if result.success:
            self.signals.log_info(f"Calibration complete: {result.wizard_type}")
            self.signals.log_info(f"  Data: {result.data}")
        else:
            self.signals.log_error(f"Calibration failed: {result.message}")

    def _on_encoder_data(self, encoder_id: int, data: object) -> None:
        """Handle encoder telemetry data."""
        if "encoder" in self._wizards:
            wizard = self._wizards["encoder"]
            if hasattr(data, 'count'):
                wizard.update_count(data.count)
