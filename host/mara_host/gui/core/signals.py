# mara_host/gui/core/signals.py
"""
Qt signals for thread-safe GUI communication.

These signals bridge the asyncio thread (robot operations)
and the Qt main thread (UI updates).
"""

from PySide6.QtCore import QObject, Signal


class GuiSignals(QObject):
    """
    Qt signals for GUI updates from async operations.

    All signals are emitted from the async thread and
    received/processed on the Qt main thread.

    Usage:
        signals = GuiSignals()
        signals.connection_changed.connect(on_connection_changed)
        signals.telemetry_received.connect(on_telemetry)

        # From async thread:
        signals.connection_changed.emit(True, "Connected to robot")
    """

    # Connection status
    connection_changed = Signal(bool, str)  # (connected, info_message)
    connection_error = Signal(str)  # error_message

    # Device capabilities (from firmware identity)
    capabilities_changed = Signal(object)  # DeviceCapabilities

    # Robot state machine
    state_changed = Signal(str)  # state (IDLE, ARMED, ACTIVE, ESTOP)

    # Telemetry data
    telemetry_received = Signal(object)  # TelemetrySnapshot or dict
    imu_data = Signal(object)  # ImuData
    encoder_data = Signal(int, object)  # (encoder_id, EncoderData)

    # Camera
    camera_frame = Signal(str, object)  # (camera_name, frame_data)
    camera_stats = Signal(object)  # StreamStats

    # Command responses
    command_ack = Signal(int, bool, str)  # (seq, success, error_or_data)
    command_sent = Signal(str, dict)  # (command_name, payload)

    # Logging
    log_message = Signal(str, str, str)  # (timestamp, level, message)

    # Status bar
    status_message = Signal(str)  # brief status text
    status_error = Signal(str)  # error message for status bar

    # Progress
    progress_started = Signal(str)  # operation_name
    progress_update = Signal(str, int)  # (operation_name, percent)
    progress_finished = Signal(str, bool)  # (operation_name, success)

    # Serial port selection (for sharing between panels)
    serial_port_selected = Signal(str, int)  # (port, baudrate)

    # Calibration
    calibration_started = Signal(str)  # calibration type
    calibration_progress = Signal(str, int, str)  # type, percent, status
    calibration_result = Signal(str, dict)  # type, results
    calibration_error = Signal(str, str)  # type, error message

    # Testing
    test_started = Signal(str)  # test name
    test_progress = Signal(str, int, str)  # name, percent, status
    test_result = Signal(str, object)  # name, TestResult
    all_tests_complete = Signal(list)  # list of TestResult

    # Recording
    recording_started = Signal(str)  # session name
    recording_progress = Signal(int, int)  # events, duration_ms
    recording_stopped = Signal(str, dict)  # name, stats

    # Replay
    replay_started = Signal(str)  # session name
    replay_progress = Signal(int, int, int)  # current_ms, total_ms, events
    replay_event = Signal(dict)  # event data
    replay_stopped = Signal()

    # Advanced control updates
    signals_updated = Signal(list)  # list of signal data
    controller_status_updated = Signal(int, dict)  # slot, status
    observer_status_updated = Signal(int, dict)  # slot, status

    def __init__(self, parent=None):
        super().__init__(parent)

    def log(self, level: str, message: str) -> None:
        """Helper to emit a log message with current timestamp."""
        import time

        timestamp = time.strftime("%H:%M:%S")
        self.log_message.emit(timestamp, level, message)

    def log_debug(self, message: str) -> None:
        """Emit a debug-level log message."""
        self.log("DEBUG", message)

    def log_info(self, message: str) -> None:
        """Emit an info-level log message."""
        self.log("INFO", message)

    def log_warning(self, message: str) -> None:
        """Emit a warning-level log message."""
        self.log("WARNING", message)

    def log_error(self, message: str) -> None:
        """Emit an error-level log message."""
        self.log("ERROR", message)
