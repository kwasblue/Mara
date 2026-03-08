# mara_host/gui/panels/testing.py
"""
Testing panel for running hardware tests.

Provides UI for running quick tests, hardware tests, and advanced tests
with results display.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "testing",
    "label": "Testing",
    "order": 60,
}

from typing import Optional

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
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QColor

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.services.testing.test_service import TestService, TestResult, TestStatus


class TestWorker(QObject):
    """Worker for running tests in a background thread."""

    test_started = Signal(str)  # test name
    test_progress = Signal(str, int, str)  # test name, percent, status
    test_finished = Signal(str, object)  # test name, TestResult
    all_finished = Signal(list)  # all results
    error = Signal(str)  # error message

    def __init__(self, controller: RobotController):
        super().__init__()
        self._controller = controller
        self._cancelled = False
        self._tests_to_run: list[str] = []
        self._test_params: dict = {}

    def set_tests(self, tests: list[str], params: dict = None) -> None:
        """Set tests to run."""
        self._tests_to_run = tests
        self._test_params = params or {}
        self._cancelled = False

    def cancel(self) -> None:
        """Cancel running tests."""
        self._cancelled = True

    def run(self) -> None:
        """Run the tests."""
        import asyncio

        async def run_tests():
            results = []

            if not self._controller._connection_service:
                self.error.emit("Not connected to robot")
                return

            client = self._controller._connection_service.client
            test_service = TestService(client)

            for test_name in self._tests_to_run:
                if self._cancelled:
                    break

                self.test_started.emit(test_name)

                try:
                    # Get the test method
                    params = self._test_params.get(test_name, {})

                    if test_name == "connection":
                        result = await test_service.test_connection()
                    elif test_name == "ping":
                        result = await test_service.test_ping()
                    elif test_name == "arm_disarm":
                        result = await test_service.test_arm_disarm()
                    elif test_name == "led":
                        result = await test_service.test_led()
                    elif test_name == "heartbeat":
                        result = await test_service.test_heartbeat()
                    elif test_name == "motors":
                        motor_ids = params.get("motor_ids", [0])
                        result = await test_service.test_motors(motor_ids=motor_ids)
                    elif test_name == "servos":
                        servo_ids = params.get("servo_ids", [0])
                        result = await test_service.test_servos(servo_ids=servo_ids)
                    elif test_name == "encoders":
                        duration = params.get("duration_s", 2.0)
                        result = await test_service.test_encoders(duration_s=duration)
                    elif test_name == "sensors":
                        duration = params.get("duration_s", 2.0)
                        result = await test_service.test_sensors(duration_s=duration)
                    elif test_name == "gpio":
                        pin = params.get("pin", 2)
                        result = await test_service.test_gpio(pin=pin)
                    else:
                        result = TestResult(
                            name=test_name,
                            status=TestStatus.SKIPPED,
                            message=f"Unknown test: {test_name}"
                        )

                    results.append(result)
                    self.test_finished.emit(test_name, result)

                except Exception as e:
                    result = TestResult(
                        name=test_name,
                        status=TestStatus.FAILED,
                        message=str(e)
                    )
                    results.append(result)
                    self.test_finished.emit(test_name, result)

            self.all_finished.emit(results)

        # Run in the controller's event loop
        if self._controller._loop and self._controller._running:
            import asyncio
            future = asyncio.run_coroutine_threadsafe(run_tests(), self._controller._loop)
            try:
                future.result(timeout=120)  # 2 minute timeout for all tests
            except Exception as e:
                self.error.emit(str(e))


class TestingPanel(QWidget):
    """
    Testing panel for hardware verification.

    Layout:
        ┌─────────────────────────────────────────────────────┐
        │ Quick Tests:  [Connection] [Ping] [LED] [Heartbeat] │
        ├─────────────────────────────────────────────────────┤
        │ Hardware Tests:                                      │
        │ ┌────────────────────────────────────────────────┐  │
        │ │ [ ] Motors    IDs: [0,1,2,3]                   │  │
        │ │ [ ] Servos    IDs: [0,1]                       │  │
        │ │ [ ] Encoders  Duration: [2.0] sec              │  │
        │ │ [ ] Sensors   Duration: [2.0] sec              │  │
        │ │ [ ] GPIO      Pin: [2]                         │  │
        │ └────────────────────────────────────────────────┘  │
        │ [Run Selected]  [Run All]  [Stop]                   │
        ├─────────────────────────────────────────────────────┤
        │ Results:                                             │
        │ ┌────────────────────────────────────────────────┐  │
        │ │ Test         Status  Duration  Details         │  │
        │ │ Connection   PASS    12ms      v1.2.3          │  │
        │ │ Ping         PASS    8ms       RTT: 8ms        │  │
        │ └────────────────────────────────────────────────┘  │
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

        self._worker: Optional[TestWorker] = None
        self._worker_thread: Optional[QThread] = None

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        """Set up the testing panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Quick tests section
        layout.addWidget(self._create_quick_tests())

        # Hardware tests section
        layout.addWidget(self._create_hardware_tests())

        # Control buttons
        layout.addWidget(self._create_control_buttons())

        # Results table
        layout.addWidget(self._create_results_table(), 1)

        # Advanced tests
        layout.addWidget(self._create_advanced_tests())

    def _create_quick_tests(self) -> QGroupBox:
        """Create quick tests section."""
        group = QGroupBox("Quick Tests")
        layout = QHBoxLayout(group)
        layout.setSpacing(12)

        self.quick_test_buttons = {}

        tests = [
            ("connection", "Connection"),
            ("ping", "Ping"),
            ("led", "LED"),
            ("heartbeat", "Heartbeat"),
        ]

        for test_id, label in tests:
            btn = QPushButton(label)
            btn.setObjectName("secondary")
            btn.clicked.connect(lambda _, t=test_id: self._run_single_test(t))
            self.quick_test_buttons[test_id] = btn
            layout.addWidget(btn)

        layout.addStretch()
        return group

    def _create_hardware_tests(self) -> QGroupBox:
        """Create hardware tests section."""
        group = QGroupBox("Hardware Tests")
        layout = QGridLayout(group)
        layout.setSpacing(12)

        self.hardware_test_checks = {}
        self.test_params_widgets = {}

        # Motors
        self.motor_check = QCheckBox("Motors")
        layout.addWidget(self.motor_check, 0, 0)
        self.hardware_test_checks["motors"] = self.motor_check

        motor_label = QLabel("IDs:")
        motor_label.setStyleSheet("color: #71717A;")
        layout.addWidget(motor_label, 0, 1)

        self.motor_ids_input = QLabel("0, 1")
        self.motor_ids_input.setStyleSheet("color: #FAFAFA;")
        layout.addWidget(self.motor_ids_input, 0, 2)

        # Servos
        self.servo_check = QCheckBox("Servos")
        layout.addWidget(self.servo_check, 1, 0)
        self.hardware_test_checks["servos"] = self.servo_check

        servo_label = QLabel("IDs:")
        servo_label.setStyleSheet("color: #71717A;")
        layout.addWidget(servo_label, 1, 1)

        self.servo_ids_input = QLabel("0, 1")
        self.servo_ids_input.setStyleSheet("color: #FAFAFA;")
        layout.addWidget(self.servo_ids_input, 1, 2)

        # Encoders
        self.encoder_check = QCheckBox("Encoders")
        layout.addWidget(self.encoder_check, 2, 0)
        self.hardware_test_checks["encoders"] = self.encoder_check

        enc_label = QLabel("Duration:")
        enc_label.setStyleSheet("color: #71717A;")
        layout.addWidget(enc_label, 2, 1)

        self.encoder_duration_spin = QDoubleSpinBox()
        self.encoder_duration_spin.setRange(0.5, 30.0)
        self.encoder_duration_spin.setValue(2.0)
        self.encoder_duration_spin.setSuffix(" sec")
        layout.addWidget(self.encoder_duration_spin, 2, 2)
        self.test_params_widgets["encoders"] = {"duration_s": self.encoder_duration_spin}

        # Sensors
        self.sensor_check = QCheckBox("Sensors")
        layout.addWidget(self.sensor_check, 3, 0)
        self.hardware_test_checks["sensors"] = self.sensor_check

        sensor_label = QLabel("Duration:")
        sensor_label.setStyleSheet("color: #71717A;")
        layout.addWidget(sensor_label, 3, 1)

        self.sensor_duration_spin = QDoubleSpinBox()
        self.sensor_duration_spin.setRange(0.5, 30.0)
        self.sensor_duration_spin.setValue(2.0)
        self.sensor_duration_spin.setSuffix(" sec")
        layout.addWidget(self.sensor_duration_spin, 3, 2)
        self.test_params_widgets["sensors"] = {"duration_s": self.sensor_duration_spin}

        # GPIO
        self.gpio_check = QCheckBox("GPIO")
        layout.addWidget(self.gpio_check, 4, 0)
        self.hardware_test_checks["gpio"] = self.gpio_check

        gpio_label = QLabel("Pin:")
        gpio_label.setStyleSheet("color: #71717A;")
        layout.addWidget(gpio_label, 4, 1)

        self.gpio_pin_spin = QSpinBox()
        self.gpio_pin_spin.setRange(0, 39)
        self.gpio_pin_spin.setValue(2)
        layout.addWidget(self.gpio_pin_spin, 4, 2)
        self.test_params_widgets["gpio"] = {"pin": self.gpio_pin_spin}

        # Add column stretch
        layout.setColumnStretch(3, 1)

        return group

    def _create_control_buttons(self) -> QWidget:
        """Create control buttons."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.run_selected_btn = QPushButton("Run Selected")
        self.run_selected_btn.clicked.connect(self._run_selected_tests)
        layout.addWidget(self.run_selected_btn)

        self.run_all_btn = QPushButton("Run All")
        self.run_all_btn.setObjectName("primary")
        self.run_all_btn.clicked.connect(self._run_all_tests)
        layout.addWidget(self.run_all_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_tests)
        layout.addWidget(self.stop_btn)

        layout.addStretch()

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #71717A;")
        layout.addWidget(self.status_label)

        return container

    def _create_results_table(self) -> QGroupBox:
        """Create results table."""
        group = QGroupBox("Results")
        layout = QVBoxLayout(group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Test", "Status", "Duration", "Details"])

        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.verticalHeader().setVisible(False)

        layout.addWidget(self.results_table)

        # Clear button
        clear_btn = QPushButton("Clear Results")
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self._clear_results)
        layout.addWidget(clear_btn, 0, Qt.AlignRight)

        return group

    def _create_advanced_tests(self) -> QGroupBox:
        """Create advanced tests section."""
        group = QGroupBox("Advanced Tests")
        layout = QHBoxLayout(group)

        latency_btn = QPushButton("Latency Test")
        latency_btn.setObjectName("secondary")
        latency_btn.clicked.connect(self._run_latency_test)
        layout.addWidget(latency_btn)

        protocol_btn = QPushButton("Command Protocol Test")
        protocol_btn.setObjectName("secondary")
        protocol_btn.clicked.connect(self._run_protocol_test)
        layout.addWidget(protocol_btn)

        layout.addStretch()
        return group

    def _setup_connections(self) -> None:
        """Set up signal connections."""
        self.signals.connection_changed.connect(self._on_connection_changed)

    def _on_connection_changed(self, connected: bool, info: str) -> None:
        """Handle connection state change."""
        self.run_selected_btn.setEnabled(connected)
        self.run_all_btn.setEnabled(connected)

        for btn in self.quick_test_buttons.values():
            btn.setEnabled(connected)

    def _get_test_params(self) -> dict:
        """Get parameters for tests."""
        params = {}

        # Motor IDs
        params["motors"] = {"motor_ids": [0, 1]}  # Default

        # Servo IDs
        params["servos"] = {"servo_ids": [0, 1]}  # Default

        # Encoder duration
        params["encoders"] = {"duration_s": self.encoder_duration_spin.value()}

        # Sensor duration
        params["sensors"] = {"duration_s": self.sensor_duration_spin.value()}

        # GPIO pin
        params["gpio"] = {"pin": self.gpio_pin_spin.value()}

        return params

    def _run_single_test(self, test_name: str) -> None:
        """Run a single test."""
        self._run_tests([test_name], self._get_test_params())

    def _run_selected_tests(self) -> None:
        """Run selected hardware tests."""
        tests = []
        for name, check in self.hardware_test_checks.items():
            if check.isChecked():
                tests.append(name)

        if tests:
            self._run_tests(tests, self._get_test_params())
        else:
            self.signals.status_message.emit("No tests selected")

    def _run_all_tests(self) -> None:
        """Run all tests."""
        tests = ["connection", "ping", "led", "heartbeat"]
        tests.extend(self.hardware_test_checks.keys())
        self._run_tests(tests, self._get_test_params())

    def _run_tests(self, tests: list[str], params: dict) -> None:
        """Run the specified tests."""
        if not self.controller.is_connected:
            self.signals.status_error.emit("Not connected")
            return

        # Set up worker
        self._worker = TestWorker(self.controller)
        self._worker.set_tests(tests, params)

        # Connect signals
        self._worker.test_started.connect(self._on_test_started)
        self._worker.test_finished.connect(self._on_test_finished)
        self._worker.all_finished.connect(self._on_all_tests_finished)
        self._worker.error.connect(self._on_test_error)

        # Update UI
        self.run_selected_btn.setEnabled(False)
        self.run_all_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText(f"Running {len(tests)} tests...")

        # Run in thread
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker_thread.start()

    def _stop_tests(self) -> None:
        """Stop running tests."""
        if self._worker:
            self._worker.cancel()
        self.status_label.setText("Stopping...")

    def _on_test_started(self, test_name: str) -> None:
        """Handle test start."""
        self.status_label.setText(f"Running: {test_name}")

        # Add row with running status
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(test_name))

        status_item = QTableWidgetItem("RUNNING")
        status_item.setForeground(QColor("#60A5FA"))
        self.results_table.setItem(row, 1, status_item)
        self.results_table.setItem(row, 2, QTableWidgetItem("--"))
        self.results_table.setItem(row, 3, QTableWidgetItem(""))

    def _on_test_finished(self, test_name: str, result: TestResult) -> None:
        """Handle test completion."""
        # Find the row for this test
        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, 0)
            if item and item.text() == test_name:
                # Update status
                status_text = result.status.value.upper()
                status_item = QTableWidgetItem(status_text)

                if result.status == TestStatus.PASSED:
                    status_item.setForeground(QColor("#22C55E"))
                elif result.status == TestStatus.FAILED:
                    status_item.setForeground(QColor("#EF4444"))
                elif result.status == TestStatus.SKIPPED:
                    status_item.setForeground(QColor("#F59E0B"))
                else:
                    status_item.setForeground(QColor("#71717A"))

                self.results_table.setItem(row, 1, status_item)

                # Duration
                duration_text = f"{result.duration_ms:.0f}ms"
                self.results_table.setItem(row, 2, QTableWidgetItem(duration_text))

                # Details
                details = result.message
                if result.details:
                    details_str = ", ".join(f"{k}={v}" for k, v in result.details.items())
                    details = f"{details} ({details_str})" if details else details_str
                self.results_table.setItem(row, 3, QTableWidgetItem(details))

                break

    def _on_all_tests_finished(self, results: list[TestResult]) -> None:
        """Handle all tests complete."""
        # Calculate summary
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        total = len(results)

        if failed == 0:
            self.status_label.setText(f"All {passed}/{total} tests passed")
            self.status_label.setStyleSheet("color: #22C55E;")
        else:
            self.status_label.setText(f"Passed: {passed}/{total}, Failed: {failed}")
            self.status_label.setStyleSheet("color: #EF4444;")

        # Re-enable buttons
        self.run_selected_btn.setEnabled(True)
        self.run_all_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # Cleanup thread
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread = None
        self._worker = None

    def _on_test_error(self, error: str) -> None:
        """Handle test error."""
        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet("color: #EF4444;")
        self.signals.log_error(f"Test error: {error}")

        # Re-enable buttons
        self.run_selected_btn.setEnabled(True)
        self.run_all_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _clear_results(self) -> None:
        """Clear the results table."""
        self.results_table.setRowCount(0)
        self.status_label.setText("")
        self.status_label.setStyleSheet("color: #71717A;")

    def _run_latency_test(self) -> None:
        """Run latency test (multiple pings)."""
        # For now, run ping test multiple times
        self._run_tests(["ping"] * 5, {})

    def _run_protocol_test(self) -> None:
        """Run command protocol test."""
        # Run connection + ping + arm_disarm
        self._run_tests(["connection", "ping", "arm_disarm", "led"], {})
