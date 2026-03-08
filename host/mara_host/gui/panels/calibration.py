# mara_host/gui/panels/calibration.py
"""
Calibration panel for robot calibration wizards.

Uses workflow layer for calibration logic and extracted widgets for UI.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "calibration",
    "label": "Calibration",
    "order": 50,
}

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QFrame,
)
from PySide6.QtCore import Qt

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.gui.widgets import (
    ProgressIndicator,
    ParameterGrid,
    ParameterSpec,
    ServoSliderGroup,
    TelemetryGrid,
    TelemetrySpec,
)


class MotorCalibrationUI(QWidget):
    """Motor calibration wizard UI."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self._setup_ui()

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
        instructions = QLabel(
            "This wizard will find the motor's dead zone and direction.\n"
            "You will be asked to confirm when the motor starts moving."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #A1A1AA;")
        layout.addWidget(instructions)

        # Progress
        self.progress = ProgressIndicator()
        layout.addWidget(self.progress)

        # User confirmation buttons
        self.confirm_frame = QFrame()
        confirm_layout = QHBoxLayout(self.confirm_frame)
        confirm_layout.addWidget(QLabel("Motor moving?"))

        self.yes_btn = QPushButton("Yes")
        self.yes_btn.clicked.connect(lambda: self._respond("yes"))
        confirm_layout.addWidget(self.yes_btn)

        self.no_btn = QPushButton("No")
        self.no_btn.clicked.connect(lambda: self._respond("no"))
        confirm_layout.addWidget(self.no_btn)
        confirm_layout.addStretch()
        self.confirm_frame.setVisible(False)
        layout.addWidget(self.confirm_frame)

        # Results
        self.results = TelemetryGrid([
            TelemetrySpec("dead_zone", "Dead zone", "%", "{:.0f}"),
            TelemetrySpec("inverted", "Inverted", "", "{}"),
        ], columns=2)
        self.results.setVisible(False)
        layout.addWidget(self.results)

        layout.addStretch()

        # Control buttons
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start Calibration")
        self.start_btn.clicked.connect(self._start)
        btn_row.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._workflow = None

    def _start(self) -> None:
        """Start calibration workflow."""
        from mara_host.workflows import MotorCalibrationWorkflow

        if not self.controller.client:
            self.signals.status_error.emit("Not connected")
            return

        self._workflow = MotorCalibrationWorkflow(self.controller.client)
        self._workflow.on_progress = self._on_progress
        self._workflow.on_user_prompt = self._on_user_prompt

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.results.setVisible(False)
        self.progress.reset()

        # Run workflow in background
        import asyncio
        asyncio.run_coroutine_threadsafe(
            self._run_workflow(),
            self.controller._loop
        )

    async def _run_workflow(self) -> None:
        motor_id = self.motor_spin.value()
        result = await self._workflow.run(motor_id=motor_id)

        # Update UI from main thread
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self, "_on_complete",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(object, result)
        )

    def _on_complete(self, result) -> None:
        """Handle workflow completion."""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.confirm_frame.setVisible(False)

        if result.ok:
            self.progress.complete("Calibration complete!")
            self.results.update("dead_zone", result.data.get("dead_zone_percent", 0))
            self.results.setText("inverted", str(result.data.get("inverted", False)))
            self.results.setVisible(True)
            self.signals.log_info(f"Motor calibration: {result.data}")
        elif result.state.value == "cancelled":
            self.progress.setProgress(0, "Cancelled")
        else:
            self.progress.error(result.error or "Calibration failed")

    def _cancel(self) -> None:
        if self._workflow:
            self._workflow.cancel()

    def _on_progress(self, percent: int, status: str) -> None:
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            self.progress, "setProgress",
            Qt.ConnectionType.QueuedConnection,
            percent, status
        )

    def _on_user_prompt(self, question: str, options: list) -> None:
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            self.confirm_frame, "setVisible",
            Qt.ConnectionType.QueuedConnection,
            True
        )

    def _respond(self, response: str) -> None:
        self.confirm_frame.setVisible(False)
        if self._workflow:
            self._workflow.respond("Yes" if response == "yes" else "No")


class ServoCalibrationUI(QWidget):
    """Servo calibration wizard UI."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self._setup_ui()

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

        # Servo slider for manual control
        self.servo_slider = ServoSliderGroup(servo_id=0)
        self.servo_slider.value_changed.connect(self._on_angle_changed)
        layout.addWidget(self.servo_slider)

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
        self.results = TelemetryGrid([
            TelemetrySpec("min", "Min", "deg", "{:.0f}"),
            TelemetrySpec("max", "Max", "deg", "{:.0f}"),
            TelemetrySpec("center", "Center", "deg", "{:.0f}"),
        ], columns=3)
        layout.addWidget(self.results)

        layout.addStretch()

        # Save button
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Calibration")
        self.save_btn.clicked.connect(self._save)
        btn_row.addWidget(self.save_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._min_angle: Optional[int] = None
        self._max_angle: Optional[int] = None

    def _on_angle_changed(self, servo_id: int, angle: float) -> None:
        actual_id = self.servo_spin.value()
        self.controller.set_servo_angle(actual_id, angle)

    def _set_min(self) -> None:
        self._min_angle = self.servo_slider.value()
        self._update_results()

    def _set_max(self) -> None:
        self._max_angle = self.servo_slider.value()
        self._update_results()

    def _update_results(self) -> None:
        if self._min_angle is not None:
            self.results.update("min", self._min_angle)
        if self._max_angle is not None:
            self.results.update("max", self._max_angle)
        if self._min_angle is not None and self._max_angle is not None:
            center = (self._min_angle + self._max_angle) // 2
            self.results.update("center", center)

    def _save(self) -> None:
        if self._min_angle is None or self._max_angle is None:
            self.signals.status_error.emit("Set both min and max angles first")
            return

        center = (self._min_angle + self._max_angle) // 2
        self.signals.status_message.emit("Servo calibration saved")
        self.signals.log_info(f"Servo calibration: min={self._min_angle}, max={self._max_angle}, center={center}")


class EncoderCalibrationUI(QWidget):
    """Encoder calibration wizard UI."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self._setup_ui()

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
        self.count_display = TelemetryGrid([
            TelemetrySpec("count", "Count", "", "{:.0f}", "0"),
        ], columns=1)
        layout.addWidget(self.count_display)

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
        self.result_display = TelemetryGrid([
            TelemetrySpec("tpr", "Ticks/rev", "", "{:.0f}"),
        ], columns=1)
        layout.addWidget(self.result_display)

        layout.addStretch()

        self._current_count = 0

    def _mark_zero(self) -> None:
        encoder_id = self.encoder_spin.value()
        self.controller.send_command("CMD_ENCODER_RESET", {"encoder_id": encoder_id})
        self._current_count = 0
        self.count_display.update("count", 0)

    def _save_count(self) -> None:
        tpr = abs(self._current_count)
        self.result_display.update("tpr", tpr)
        self.signals.log_info(f"Encoder calibration: ticks_per_rev={tpr}")

    def update_count(self, count: int) -> None:
        """Called from telemetry."""
        self._current_count = count
        self.count_display.update("count", count)


class WheelsCalibrationUI(QWidget):
    """Wheel dimensions configuration UI."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self._setup_ui()

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

        # Parameters
        self._params = ParameterGrid([
            ParameterSpec("diameter", "Wheel diameter", 10, 500, 65, 1, 1, " mm"),
            ParameterSpec("wheelbase", "Wheel base", 50, 1000, 150, 1, 1, " mm"),
        ], columns=1)
        self._params.value_changed.connect(self._update_calculated)
        layout.addWidget(self._params)

        # Calculated values
        calc_group = QGroupBox("Calculated Values")
        calc_layout = QVBoxLayout(calc_group)
        self._calculated = TelemetryGrid([
            TelemetrySpec("circumference", "Circumference", "mm", "{:.1f}"),
            TelemetrySpec("radius", "Radius", "m", "{:.4f}"),
        ], columns=2)
        calc_layout.addWidget(self._calculated)
        layout.addWidget(calc_group)

        self._update_calculated("", 0)

        layout.addStretch()

        # Save button
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self._save)
        btn_row.addWidget(self.save_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _update_calculated(self, key: str, value: float) -> None:
        import math
        diameter_mm = self._params.value("diameter")
        circumference = math.pi * diameter_mm
        radius_m = (diameter_mm / 2) / 1000

        self._calculated.update("circumference", circumference)
        self._calculated.update("radius", radius_m)

    def _save(self) -> None:
        diameter_m = self._params.value("diameter") / 1000
        wheelbase_m = self._params.value("wheelbase") / 1000

        self.signals.status_message.emit("Wheel configuration saved")
        self.signals.log_info(f"Wheel config: diameter={diameter_m}m, wheelbase={wheelbase_m}m")


class IMUCalibrationUI(QWidget):
    """IMU calibration wizard UI."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Instructions
        instructions = QLabel(
            "Place the robot on a flat, stable surface.\n"
            "Keep it completely still during calibration.\n"
            "This will collect samples to calculate sensor offsets."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #A1A1AA;")
        layout.addWidget(instructions)

        # Progress
        self.progress = ProgressIndicator()
        layout.addWidget(self.progress)

        # Results
        self.accel_results = TelemetryGrid([
            TelemetrySpec("ax", "Accel X", "", "{:.4f}"),
            TelemetrySpec("ay", "Y", "", "{:.4f}"),
            TelemetrySpec("az", "Z", "", "{:.4f}"),
        ], columns=3)
        layout.addWidget(self.accel_results)

        self.gyro_results = TelemetryGrid([
            TelemetrySpec("gx", "Gyro X", "", "{:.4f}"),
            TelemetrySpec("gy", "Y", "", "{:.4f}"),
            TelemetrySpec("gz", "Z", "", "{:.4f}"),
        ], columns=3)
        layout.addWidget(self.gyro_results)

        layout.addStretch()

        # Control buttons
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start Calibration")
        self.start_btn.clicked.connect(self._start)
        btn_row.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._workflow = None

    def _start(self) -> None:
        from mara_host.workflows import IMUCalibrationWorkflow

        if not self.controller.client:
            self.signals.status_error.emit("Not connected")
            return

        self._workflow = IMUCalibrationWorkflow(self.controller.client)
        self._workflow.on_progress = self._on_progress

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.reset()

        import asyncio
        asyncio.run_coroutine_threadsafe(
            self._run_workflow(),
            self.controller._loop
        )

    async def _run_workflow(self) -> None:
        result = await self._workflow.run(num_samples=100)

        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self, "_on_complete",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(object, result)
        )

    def _on_complete(self, result) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if result.ok:
            self.progress.complete("Calibration complete!")
            offsets = result.data.get("accel_offsets", [0, 0, 0])
            self.accel_results.update("ax", offsets[0])
            self.accel_results.update("ay", offsets[1])
            self.accel_results.update("az", offsets[2])

            gyro = result.data.get("gyro_offsets", [0, 0, 0])
            self.gyro_results.update("gx", gyro[0])
            self.gyro_results.update("gy", gyro[1])
            self.gyro_results.update("gz", gyro[2])
        else:
            self.progress.error(result.error or "Calibration failed")

    def _cancel(self) -> None:
        if self._workflow:
            self._workflow.cancel()

    def _on_progress(self, percent: int, status: str) -> None:
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            self.progress, "setProgress",
            Qt.ConnectionType.QueuedConnection,
            percent, status
        )


class PIDCalibrationUI(QWidget):
    """PID tuning wizard UI."""

    def __init__(self, signals: GuiSignals, controller: RobotController, parent=None):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self._setup_ui()

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
        gains_layout = QVBoxLayout(gains_group)
        self._gains = ParameterGrid([
            ParameterSpec("kp", "Kp", 0, 100, 1.0, 0.1, 3),
            ParameterSpec("ki", "Ki", 0, 100, 0.0, 0.01, 3),
            ParameterSpec("kd", "Kd", 0, 100, 0.0, 0.01, 3),
        ], columns=3)
        gains_layout.addWidget(self._gains)
        layout.addWidget(gains_group)

        # Test parameters
        test_group = QGroupBox("Test Parameters")
        test_layout = QVBoxLayout(test_group)
        self._test_params = ParameterGrid([
            ParameterSpec("target", "Target velocity", -50, 50, 10.0, 0.5, 1, " rad/s"),
            ParameterSpec("duration", "Hold time", 0.5, 30, 3.0, 0.5, 1, " sec"),
        ], columns=2)
        test_layout.addWidget(self._test_params)
        layout.addWidget(test_group)

        # Progress
        self.progress = ProgressIndicator()
        layout.addWidget(self.progress)

        # Results
        self.results = TelemetryGrid([
            TelemetrySpec("rise_time", "Rise time", "s", "{:.3f}"),
            TelemetrySpec("overshoot", "Overshoot", "%", "{:.1f}"),
            TelemetrySpec("settling", "Settling", "s", "{:.3f}"),
        ], columns=3)
        layout.addWidget(self.results)

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

        self._workflow = None

    def _apply_gains(self) -> None:
        motor_id = self.motor_spin.value()
        gains = self._gains.values()
        self.controller.send_command(
            "CMD_DC_SET_VEL_GAINS",
            {"motor_id": motor_id, **gains}
        )
        self.signals.status_message.emit(f"Applied gains to motor {motor_id}")

    def _run_test(self) -> None:
        from mara_host.workflows import PIDTuningWorkflow

        if not self.controller.client:
            self.signals.status_error.emit("Not connected")
            return

        motor_id = self.motor_spin.value()
        gains = self._gains.values()
        params = self._test_params.values()

        self._workflow = PIDTuningWorkflow(self.controller.client)
        self._workflow.on_progress = self._on_progress

        self.test_btn.setEnabled(False)
        self.progress.reset()

        import asyncio
        asyncio.run_coroutine_threadsafe(
            self._run_workflow(motor_id, gains, params),
            self.controller._loop
        )

    async def _run_workflow(self, motor_id: int, gains: dict, params: dict) -> None:
        result = await self._workflow.run(
            motor_id=motor_id,
            kp=gains["kp"],
            ki=gains["ki"],
            kd=gains["kd"],
            target_velocity=params["target"],
            test_duration=params["duration"],
        )

        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self, "_on_complete",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(object, result)
        )

    def _on_complete(self, result) -> None:
        self.test_btn.setEnabled(True)

        if result.ok:
            self.progress.complete("Test complete")
            self.results.update("rise_time", result.data.get("rise_time", 0))
            self.results.update("overshoot", result.data.get("overshoot", 0))
            self.results.update("settling", result.data.get("settling_time", 0))
        else:
            self.progress.error(result.error or "Test failed")

    def _stop(self) -> None:
        if self._workflow:
            self._workflow.cancel()
        motor_id = self.motor_spin.value()
        self.controller.send_command(
            "CMD_DC_VEL_PID_ENABLE",
            {"motor_id": motor_id, "enable": False}
        )
        self.controller.send_command(
            "CMD_DC_MOTOR_SET_SPEED",
            {"motor_id": motor_id, "speed": 0.0}
        )

    def _on_progress(self, percent: int, status: str) -> None:
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            self.progress, "setProgress",
            Qt.ConnectionType.QueuedConnection,
            percent, status
        )


class CalibrationPanel(QWidget):
    """
    Calibration panel with wizard selection.

    Uses workflow layer for calibration logic.
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

        # Create wizard UIs
        self._wizards["motor"] = MotorCalibrationUI(self.signals, self.controller)
        self._wizards["servo"] = ServoCalibrationUI(self.signals, self.controller)
        self._wizards["encoder"] = EncoderCalibrationUI(self.signals, self.controller)
        self._wizards["wheels"] = WheelsCalibrationUI(self.signals, self.controller)
        self._wizards["imu"] = IMUCalibrationUI(self.signals, self.controller)
        self._wizards["pid"] = PIDCalibrationUI(self.signals, self.controller)

        for wizard in self._wizards.values():
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(32, 32, 32, 32)
            container_layout.addWidget(wizard)
            self.wizard_stack.addWidget(container)

        layout.addWidget(self.wizard_stack, 1)
        self.wizard_list.setCurrentRow(0)

    def _setup_connections(self) -> None:
        self.signals.encoder_data.connect(self._on_encoder_data)

    def _on_wizard_changed(self, index: int) -> None:
        self.wizard_stack.setCurrentIndex(index)

    def _on_encoder_data(self, encoder_id: int, data: object) -> None:
        if "encoder" in self._wizards:
            wizard = self._wizards["encoder"]
            if hasattr(data, 'count'):
                wizard.update_count(data.count)
