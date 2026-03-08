# mara_host/gui/panels/session.py
"""
Session panel for recording and replay functionality.

Uses workflow layer for recording/replay logic.
"""

# Panel metadata for auto-discovery
PANEL_META = {
    "id": "session",
    "label": "Session",
    "order": 90,
}

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QTextEdit,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.gui.widgets import ProgressIndicator, TelemetryGrid, TelemetrySpec


class RecordingTab(QWidget):
    """Recording control tab using RecordingWorkflow."""

    def __init__(
        self,
        signals: GuiSignals,
        controller: RobotController,
        settings: GuiSettings,
        parent=None,
    ):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self.settings = settings

        self._workflow = None
        self._recording = False

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Current status
        status_group = QGroupBox("Current Session")
        status_layout = QVBoxLayout(status_group)

        self._status_display = TelemetryGrid([
            TelemetrySpec("session", "Session", "", "{}"),
            TelemetrySpec("status", "Status", "", "{}"),
        ], columns=2)
        self._status_display.setText("session", "--")
        self._status_display.setText("status", "Idle")
        status_layout.addWidget(self._status_display)

        self._stats_display = TelemetryGrid([
            TelemetrySpec("duration", "Duration", "", "{}"),
            TelemetrySpec("events", "Events", "", "{:.0f}"),
        ], columns=2)
        self._stats_display.setText("duration", "00:00:00")
        self._stats_display.update("events", 0)
        status_layout.addWidget(self._stats_display)

        layout.addWidget(status_group)

        # Control buttons
        btn_row = QHBoxLayout()
        self.stop_btn = QPushButton("Stop Recording")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_recording)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # New recording
        new_group = QGroupBox("New Recording")
        new_layout = QVBoxLayout(new_group)

        # Session name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Session Name:"))
        self.session_name_edit = QLineEdit()
        self.session_name_edit.setPlaceholderText("my_recording")
        name_row.addWidget(self.session_name_edit, 1)
        new_layout.addLayout(name_row)

        # Duration
        duration_row = QHBoxLayout()
        duration_row.addWidget(QLabel("Duration:"))
        self.duration_combo = QComboBox()
        self.duration_combo.addItems([
            "Unlimited", "10 seconds", "30 seconds",
            "1 minute", "5 minutes", "10 minutes",
        ])
        duration_row.addWidget(self.duration_combo)
        duration_row.addStretch()
        new_layout.addLayout(duration_row)

        # Start button
        self.start_btn = QPushButton("Start Recording")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start_recording)
        new_layout.addWidget(self.start_btn, 0, Qt.AlignLeft)

        layout.addWidget(new_group)
        layout.addStretch()

    def _setup_timer(self) -> None:
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_status)

    def _get_duration_seconds(self) -> float:
        text = self.duration_combo.currentText()
        durations = {
            "Unlimited": 0, "10 seconds": 10, "30 seconds": 30,
            "1 minute": 60, "5 minutes": 300, "10 minutes": 600,
        }
        return durations.get(text, 0)

    def _start_recording(self) -> None:
        from mara_host.workflows import RecordingWorkflow

        session_name = self.session_name_edit.text().strip()
        if not session_name:
            import time
            session_name = f"session_{int(time.time())}"
            self.session_name_edit.setText(session_name)

        duration = self._get_duration_seconds()

        if not self.controller.client:
            self.signals.status_error.emit("Not connected to robot")
            return

        self._workflow = RecordingWorkflow(self.controller.client)
        self._workflow.on_progress = self._on_progress
        self._recording = True

        self._status_display.setText("session", session_name)
        self._status_display.setText("status", "Recording")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self._update_timer.start(100)

        import asyncio
        asyncio.run_coroutine_threadsafe(
            self._run_workflow(session_name, duration),
            self.controller._loop
        )

    async def _run_workflow(self, session_name: str, duration: float) -> None:
        result = await self._workflow.run(
            session_name=session_name,
            duration_s=duration,
        )

        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self, "_on_complete",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(object, result)
        )

    def _on_complete(self, result) -> None:
        self._recording = False
        self._update_timer.stop()

        if result.ok:
            self._status_display.setText("status", "Saved")
            self.signals.status_message.emit(
                f"Recording saved: {result.data.get('event_count', 0)} events"
            )
        else:
            self._status_display.setText("status", "Error")
            self.signals.status_error.emit(f"Recording error: {result.error}")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _stop_recording(self) -> None:
        if self._workflow:
            self._workflow.cancel()

    def _on_progress(self, percent: int, status: str) -> None:
        pass  # Progress handled by timer

    def _update_status(self) -> None:
        if self._workflow and self._recording:
            events = self._workflow.event_count
            duration = self._workflow.duration_s

            secs = int(duration)
            mins = secs // 60
            hours = mins // 60
            self._stats_display.setText(
                "duration", f"{hours:02d}:{mins % 60:02d}:{secs % 60:02d}"
            )
            self._stats_display.update("events", events)


class ReplayTab(QWidget):
    """Replay control tab using ReplayWorkflow."""

    def __init__(
        self,
        signals: GuiSignals,
        controller: RobotController,
        settings: GuiSettings,
        parent=None,
    ):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self.settings = settings

        self._workflow = None
        self._playing = False

        self._setup_ui()
        self._refresh_sessions()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Session selector
        select_row = QHBoxLayout()
        select_row.addWidget(QLabel("Session:"))
        self.session_combo = QComboBox()
        self.session_combo.currentTextChanged.connect(self._on_session_selected)
        select_row.addWidget(self.session_combo, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self._refresh_sessions)
        select_row.addWidget(refresh_btn)
        layout.addLayout(select_row)

        # Session info
        info_group = QGroupBox("Session Info")
        info_layout = QVBoxLayout(info_group)
        self._info_display = TelemetryGrid([
            TelemetrySpec("duration", "Duration", "sec", "{:.1f}"),
            TelemetrySpec("events", "Events", "", "{:.0f}"),
        ], columns=2)
        info_layout.addWidget(self._info_display)
        layout.addWidget(info_group)

        # Playback controls
        controls_group = QGroupBox("Playback")
        controls_layout = QVBoxLayout(controls_group)

        # Speed
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "2x", "5x", "10x"])
        self.speed_combo.setCurrentText("1x")
        speed_row.addWidget(self.speed_combo)
        speed_row.addStretch()
        controls_layout.addLayout(speed_row)

        # Progress
        self.progress = ProgressIndicator()
        controls_layout.addWidget(self.progress)

        # Play/Pause/Stop buttons
        btn_row = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self._play)
        btn_row.addWidget(self.play_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._pause)
        btn_row.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("secondary")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch()
        controls_layout.addLayout(btn_row)

        layout.addWidget(controls_group)

        # Event log
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout(log_group)
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(150)
        self.event_log.setStyleSheet(
            "font-family: 'Menlo', monospace; font-size: 11px; "
            "background-color: #18181B; color: #A1A1AA;"
        )
        log_layout.addWidget(self.event_log)
        layout.addWidget(log_group)

        layout.addStretch()

    def _refresh_sessions(self) -> None:
        from mara_host.workflows import ReplayWorkflow
        sessions = ReplayWorkflow.list_sessions()
        self.session_combo.clear()
        self.session_combo.addItems(sessions)

    def _on_session_selected(self, name: str) -> None:
        if not name:
            return

        from mara_host.workflows import ReplayWorkflow
        workflow = ReplayWorkflow(None)  # Don't need client for info
        info = workflow.get_session_info(name)

        if info:
            self._info_display.update("duration", info.duration_s)
            self._info_display.update("events", info.event_count)

    def _get_speed(self) -> float:
        text = self.speed_combo.currentText()
        return float(text.replace("x", ""))

    def _play(self) -> None:
        from mara_host.workflows import ReplayWorkflow

        session_name = self.session_combo.currentText()
        if not session_name:
            return

        if self._workflow and self._workflow.is_paused:
            self._workflow.resume()
            self.play_btn.setText("Play")
            self.pause_btn.setEnabled(True)
            return

        self._workflow = ReplayWorkflow(self.controller.client)
        self._workflow.on_progress = self._on_progress
        self._workflow.on_event = self._on_event

        self._playing = True
        self.event_log.clear()
        self.progress.reset()
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)

        speed = self._get_speed()

        import asyncio
        asyncio.run_coroutine_threadsafe(
            self._run_workflow(session_name, speed),
            self.controller._loop
        )

    async def _run_workflow(self, session_name: str, speed: float) -> None:
        result = await self._workflow.run(
            session_name=session_name,
            speed=speed,
        )

        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self, "_on_complete",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(object, result)
        )

    def _on_complete(self, result) -> None:
        self._playing = False
        self.play_btn.setText("Play")
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

        if result.ok:
            self.progress.complete(f"Played {result.data.get('events_played', 0)} events")
        elif result.state.value == "cancelled":
            self.progress.setProgress(0, "Stopped")
        else:
            self.progress.error(result.error or "Playback failed")

    def _pause(self) -> None:
        if self._workflow and not self._workflow.is_paused:
            self._workflow.pause()
            self.play_btn.setText("Resume")
            self.pause_btn.setEnabled(False)

    def _stop(self) -> None:
        if self._workflow:
            self._workflow.cancel()

    def _on_progress(self, percent: int, status: str) -> None:
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            self.progress, "setProgress",
            Qt.ConnectionType.QueuedConnection,
            percent, status
        )

    def _on_event(self, event) -> None:
        topic = event.topic
        ts = event.timestamp
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            self, "_append_event",
            Qt.ConnectionType.QueuedConnection,
            f"[{ts:.3f}] {topic}"
        )

    def _append_event(self, text: str) -> None:
        self.event_log.append(text)
        cursor = self.event_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.event_log.setTextCursor(cursor)


class SessionsTab(QWidget):
    """Sessions management tab."""

    def __init__(
        self,
        signals: GuiSignals,
        controller: RobotController,
        settings: GuiSettings,
        parent=None,
    ):
        super().__init__(parent)
        self.signals = signals
        self.controller = controller
        self.settings = settings

        self._setup_ui()
        self._refresh_sessions()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Sessions list
        self.sessions_list = QListWidget()
        self.sessions_list.currentItemChanged.connect(self._on_session_selected)
        layout.addWidget(self.sessions_list, 1)

        # Session details
        details_group = QGroupBox("Session Details")
        details_layout = QVBoxLayout(details_group)
        self._details = TelemetryGrid([
            TelemetrySpec("name", "Name", "", "{}"),
            TelemetrySpec("duration", "Duration", "sec", "{:.1f}"),
            TelemetrySpec("events", "Events", "", "{:.0f}"),
        ], columns=3)
        details_layout.addWidget(self._details)
        layout.addWidget(details_group)

        # Action buttons
        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self._refresh_sessions)
        btn_row.addWidget(refresh_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete_session)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _refresh_sessions(self) -> None:
        from mara_host.workflows import ReplayWorkflow
        sessions = ReplayWorkflow.list_sessions()
        self.sessions_list.clear()
        for name in sessions:
            self.sessions_list.addItem(QListWidgetItem(name))

    def _on_session_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        if not current:
            self.delete_btn.setEnabled(False)
            return

        name = current.text()
        from mara_host.workflows import ReplayWorkflow
        workflow = ReplayWorkflow(None)
        info = workflow.get_session_info(name)

        if info:
            self._details.setText("name", info.name)
            self._details.update("duration", info.duration_s)
            self._details.update("events", info.event_count)
            self.delete_btn.setEnabled(True)
        else:
            self._details.setText("name", "--")
            self._details.setText("duration", "--")
            self._details.setText("events", "--")
            self.delete_btn.setEnabled(False)

    def _delete_session(self) -> None:
        item = self.sessions_list.currentItem()
        if not item:
            return

        name = item.text()

        reply = QMessageBox.question(
            self, "Delete Session",
            f"Delete session '{name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            import shutil
            session_path = Path("logs") / name
            if session_path.exists():
                shutil.rmtree(session_path)
                self._refresh_sessions()
                self.signals.status_message.emit(f"Deleted session: {name}")


class SessionPanel(QWidget):
    """Session panel for recording and replay."""

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

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        self.recording_tab = RecordingTab(self.signals, self.controller, self.settings)
        self.tabs.addTab(self.recording_tab, "Recording")

        self.replay_tab = ReplayTab(self.signals, self.controller, self.settings)
        self.tabs.addTab(self.replay_tab, "Replay")

        self.sessions_tab = SessionsTab(self.signals, self.controller, self.settings)
        self.tabs.addTab(self.sessions_tab, "Sessions")

        layout.addWidget(self.tabs)
