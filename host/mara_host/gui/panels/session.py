# mara_host/gui/panels/session.py
"""
Session panel for recording and replay functionality.

Provides UI for recording robot sessions, replaying them,
and managing saved sessions.
"""

from typing import Optional
from pathlib import Path
from dataclasses import dataclass

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
    QLineEdit,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QFrame,
    QTextEdit,
    QCheckBox,
    QSlider,
    QProgressBar,
    QScrollArea,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject

from mara_host.gui.core import GuiSignals, RobotController, GuiSettings
from mara_host.services.recording.recording_service import (
    RecordingService,
    ReplayService,
    RecordingConfig,
    SessionInfo,
    RecordedEvent,
)


class RecordingWorker(QObject):
    """Worker for background recording."""

    started = Signal(str)  # session name
    progress = Signal(int, int)  # events, duration_ms
    stopped = Signal(str, dict)  # name, stats
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._service: Optional[RecordingService] = None
        self._running = False

    def start_recording(
        self,
        session_name: str,
        serial_port: str,
        baudrate: int,
        duration_s: float = 0,
        log_dir: str = "logs",
    ) -> None:
        """Start a recording session."""
        import asyncio

        async def _record():
            config = RecordingConfig(
                session_name=session_name,
                log_dir=Path(log_dir),
                serial_port=serial_port,
                baudrate=baudrate,
                duration_s=duration_s,
                console_output=False,
            )

            self._service = RecordingService(config)
            self._running = True

            try:
                path = await self._service.start()
                self.started.emit(session_name)

                start_time = asyncio.get_event_loop().time()

                while self._running:
                    await asyncio.sleep(0.1)

                    # Update progress
                    elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                    event_count = self._service._event_count
                    self.progress.emit(event_count, elapsed_ms)

                    # Check duration limit
                    if duration_s > 0 and elapsed_ms / 1000 >= duration_s:
                        break

                info = await self._service.stop()
                self.stopped.emit(session_name, {
                    "event_count": info.event_count,
                    "duration_s": info.duration_s,
                    "path": str(info.path),
                })

            except Exception as e:
                self.error.emit(str(e))
                self._running = False

        # Run in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_record())

    def stop_recording(self) -> None:
        """Stop the current recording."""
        self._running = False


class ReplayWorker(QObject):
    """Worker for session replay."""

    started = Signal(str)  # session name
    progress = Signal(int, int, int)  # current_ms, total_ms, events_played
    event = Signal(dict)  # event data
    stopped = Signal()
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._running = False
        self._paused = False

    def start_replay(
        self,
        session_name: str,
        log_dir: str = "logs",
        speed: float = 1.0,
        filter_topics: Optional[list] = None,
    ) -> None:
        """Start replaying a session."""
        import asyncio
        import time

        async def _replay():
            service = ReplayService(session_name, Path(log_dir))
            info = service.get_session_info()

            if not info:
                self.error.emit(f"Session not found: {session_name}")
                return

            self._running = True
            self.started.emit(session_name)

            total_ms = int(info.duration_s * 1000)
            events_played = 0
            start_time = time.time()
            last_event_ts = None

            for event in service.events():
                if not self._running:
                    break

                while self._paused and self._running:
                    await asyncio.sleep(0.1)

                # Filter by topic
                if filter_topics and event.topic not in filter_topics:
                    continue

                # Apply timing
                if last_event_ts is not None and speed > 0:
                    delay = (event.timestamp - last_event_ts) / speed
                    if delay > 0:
                        await asyncio.sleep(delay)

                last_event_ts = event.timestamp
                events_played += 1

                # Emit event
                self.event.emit({
                    "timestamp": event.timestamp,
                    "topic": event.topic,
                    "data": event.data,
                })

                # Progress
                if info.start_time:
                    current_ms = int((event.timestamp - info.start_time) * 1000)
                    self.progress.emit(current_ms, total_ms, events_played)

            self.stopped.emit()
            self._running = False

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_replay())

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._running = False


class RecordingTab(QWidget):
    """Recording control tab."""

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

        self._worker: Optional[RecordingWorker] = None
        self._worker_thread: Optional[QThread] = None
        self._recording = False

        self._setup_ui()
        self._setup_connections()

        # Update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_status)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Current status
        status_group = QGroupBox("Current Session")
        status_layout = QGridLayout(status_group)

        status_layout.addWidget(QLabel("Session:"), 0, 0)
        self.session_name_label = QLabel("--")
        self.session_name_label.setStyleSheet("color: #FAFAFA; font-weight: bold;")
        status_layout.addWidget(self.session_name_label, 0, 1)

        status_layout.addWidget(QLabel("Status:"), 0, 2)
        self.status_indicator = QLabel("Idle")
        self.status_indicator.setStyleSheet("color: #71717A;")
        status_layout.addWidget(self.status_indicator, 0, 3)

        status_layout.addWidget(QLabel("Duration:"), 1, 0)
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "font-size: 16px; color: #FAFAFA;"
        )
        status_layout.addWidget(self.duration_label, 1, 1)

        status_layout.addWidget(QLabel("Events:"), 1, 2)
        self.events_label = QLabel("0")
        self.events_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "font-size: 16px; color: #FAFAFA;"
        )
        status_layout.addWidget(self.events_label, 1, 3)

        status_layout.setColumnStretch(4, 1)
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
            "Unlimited",
            "10 seconds",
            "30 seconds",
            "1 minute",
            "5 minutes",
            "10 minutes",
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

    def _setup_connections(self) -> None:
        pass

    def _get_duration_seconds(self) -> float:
        """Get duration from combo box."""
        text = self.duration_combo.currentText()
        if "Unlimited" in text:
            return 0
        if "10 seconds" in text:
            return 10
        if "30 seconds" in text:
            return 30
        if "1 minute" in text:
            return 60
        if "5 minutes" in text:
            return 300
        if "10 minutes" in text:
            return 600
        return 0

    def _start_recording(self) -> None:
        """Start a new recording."""
        session_name = self.session_name_edit.text().strip()
        if not session_name:
            import time
            session_name = f"session_{int(time.time())}"
            self.session_name_edit.setText(session_name)

        duration = self._get_duration_seconds()

        # Get connection details
        state = self.controller.state
        if not state.is_connected:
            self.signals.status_error.emit("Not connected to robot")
            return

        port = state.transport_config.port
        baudrate = state.transport_config.baudrate

        # Start worker
        self._worker = RecordingWorker()
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)

        self._worker.started.connect(self._on_recording_started)
        self._worker.progress.connect(self._on_recording_progress)
        self._worker.stopped.connect(self._on_recording_stopped)
        self._worker.error.connect(self._on_recording_error)

        self._worker_thread.started.connect(
            lambda: self._worker.start_recording(
                session_name, port, baudrate, duration
            )
        )
        self._worker_thread.start()

    def _stop_recording(self) -> None:
        """Stop the current recording."""
        if self._worker:
            self._worker.stop_recording()

    def _on_recording_started(self, name: str) -> None:
        self._recording = True
        self.session_name_label.setText(name)
        self.status_indicator.setText("Recording")
        self.status_indicator.setStyleSheet("color: #EF4444;")

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self._update_timer.start(100)

    def _on_recording_progress(self, events: int, duration_ms: int) -> None:
        self.events_label.setText(str(events))

        secs = duration_ms // 1000
        mins = secs // 60
        hours = mins // 60
        self.duration_label.setText(
            f"{hours:02d}:{mins % 60:02d}:{secs % 60:02d}"
        )

    def _on_recording_stopped(self, name: str, stats: dict) -> None:
        self._recording = False
        self._update_timer.stop()

        self.status_indicator.setText("Stopped")
        self.status_indicator.setStyleSheet("color: #22C55E;")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        self.signals.status_message.emit(
            f"Recording saved: {stats.get('event_count', 0)} events"
        )

        # Cleanup
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread = None
        self._worker = None

    def _on_recording_error(self, error: str) -> None:
        self._recording = False
        self._update_timer.stop()

        self.status_indicator.setText("Error")
        self.status_indicator.setStyleSheet("color: #EF4444;")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        self.signals.status_error.emit(f"Recording error: {error}")

    def _update_status(self) -> None:
        """Periodic status update."""
        pass


class ReplayTab(QWidget):
    """Replay control tab."""

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

        self._worker: Optional[ReplayWorker] = None
        self._worker_thread: Optional[QThread] = None
        self._playing = False
        self._paused = False

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
        info_layout = QGridLayout(info_group)

        info_layout.addWidget(QLabel("Duration:"), 0, 0)
        self.info_duration_label = QLabel("--")
        info_layout.addWidget(self.info_duration_label, 0, 1)

        info_layout.addWidget(QLabel("Events:"), 0, 2)
        self.info_events_label = QLabel("--")
        info_layout.addWidget(self.info_events_label, 0, 3)

        info_layout.addWidget(QLabel("Topics:"), 1, 0)
        self.info_topics_label = QLabel("--")
        self.info_topics_label.setWordWrap(True)
        info_layout.addWidget(self.info_topics_label, 1, 1, 1, 3)

        info_layout.setColumnStretch(4, 1)
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
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        controls_layout.addWidget(self.progress_bar)

        # Time display
        time_row = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace;"
        )
        time_row.addWidget(self.current_time_label)

        time_row.addWidget(QLabel("/"))

        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet(
            "font-family: 'Menlo', 'JetBrains Mono', monospace;"
        )
        time_row.addWidget(self.total_time_label)

        time_row.addStretch()

        self.events_played_label = QLabel("0 events")
        time_row.addWidget(self.events_played_label)
        controls_layout.addLayout(time_row)

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
            "font-family: 'Menlo', 'JetBrains Mono', monospace; "
            "font-size: 11px; background-color: #18181B; color: #A1A1AA;"
        )
        log_layout.addWidget(self.event_log)

        layout.addWidget(log_group)
        layout.addStretch()

    def _refresh_sessions(self) -> None:
        """Refresh the list of available sessions."""
        sessions = ReplayService.list_sessions()
        self.session_combo.clear()
        self.session_combo.addItems(sessions)

    def _on_session_selected(self, name: str) -> None:
        """Handle session selection."""
        if not name:
            return

        service = ReplayService(name)
        info = service.get_session_info()

        if info:
            self.info_duration_label.setText(f"{info.duration_s:.1f} sec")
            self.info_events_label.setText(str(info.event_count))
            topics = ", ".join(info.topics[:5])
            if len(info.topics) > 5:
                topics += f" (+{len(info.topics) - 5} more)"
            self.info_topics_label.setText(topics or "None")

            # Set total time
            mins = int(info.duration_s) // 60
            secs = int(info.duration_s) % 60
            self.total_time_label.setText(f"{mins:02d}:{secs:02d}")

    def _get_speed(self) -> float:
        """Get playback speed."""
        text = self.speed_combo.currentText()
        return float(text.replace("x", ""))

    def _play(self) -> None:
        """Start or resume playback."""
        session_name = self.session_combo.currentText()
        if not session_name:
            return

        if self._paused and self._worker:
            self._worker.resume()
            self._paused = False
            self.play_btn.setText("Play")
            self.pause_btn.setEnabled(True)
            return

        # Start new playback
        self._worker = ReplayWorker()
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)

        self._worker.started.connect(self._on_replay_started)
        self._worker.progress.connect(self._on_replay_progress)
        self._worker.event.connect(self._on_replay_event)
        self._worker.stopped.connect(self._on_replay_stopped)
        self._worker.error.connect(self._on_replay_error)

        speed = self._get_speed()
        self._worker_thread.started.connect(
            lambda: self._worker.start_replay(session_name, "logs", speed)
        )
        self._worker_thread.start()

    def _pause(self) -> None:
        """Pause playback."""
        if self._worker and not self._paused:
            self._worker.pause()
            self._paused = True
            self.play_btn.setText("Resume")
            self.pause_btn.setEnabled(False)

    def _stop(self) -> None:
        """Stop playback."""
        if self._worker:
            self._worker.stop()

    def _on_replay_started(self, name: str) -> None:
        self._playing = True
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.event_log.clear()

    def _on_replay_progress(self, current_ms: int, total_ms: int, events: int) -> None:
        if total_ms > 0:
            progress = int(current_ms / total_ms * 100)
            self.progress_bar.setValue(progress)

        secs = current_ms // 1000
        mins = secs // 60
        self.current_time_label.setText(f"{mins:02d}:{secs % 60:02d}")
        self.events_played_label.setText(f"{events} events")

    def _on_replay_event(self, event_data: dict) -> None:
        topic = event_data.get("topic", "?")
        ts = event_data.get("timestamp", 0)
        self.event_log.append(f"[{ts:.3f}] {topic}")

        # Auto-scroll
        cursor = self.event_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.event_log.setTextCursor(cursor)

    def _on_replay_stopped(self) -> None:
        self._playing = False
        self._paused = False
        self.play_btn.setText("Play")
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

        # Cleanup
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread = None
        self._worker = None

    def _on_replay_error(self, error: str) -> None:
        self.signals.status_error.emit(f"Replay error: {error}")
        self._on_replay_stopped()


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
        details_layout = QGridLayout(details_group)

        details_layout.addWidget(QLabel("Name:"), 0, 0)
        self.detail_name_label = QLabel("--")
        details_layout.addWidget(self.detail_name_label, 0, 1)

        details_layout.addWidget(QLabel("Path:"), 1, 0)
        self.detail_path_label = QLabel("--")
        self.detail_path_label.setWordWrap(True)
        self.detail_path_label.setStyleSheet("color: #71717A; font-size: 11px;")
        details_layout.addWidget(self.detail_path_label, 1, 1)

        details_layout.addWidget(QLabel("Duration:"), 2, 0)
        self.detail_duration_label = QLabel("--")
        details_layout.addWidget(self.detail_duration_label, 2, 1)

        details_layout.addWidget(QLabel("Events:"), 2, 2)
        self.detail_events_label = QLabel("--")
        details_layout.addWidget(self.detail_events_label, 2, 3)

        details_layout.setColumnStretch(4, 1)
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
        """Refresh sessions list."""
        sessions = ReplayService.list_sessions()
        self.sessions_list.clear()

        for name in sessions:
            item = QListWidgetItem(name)
            self.sessions_list.addItem(item)

    def _on_session_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle session selection."""
        if not current:
            self.delete_btn.setEnabled(False)
            return

        name = current.text()
        service = ReplayService(name)
        info = service.get_session_info()

        if info:
            self.detail_name_label.setText(info.name)
            self.detail_path_label.setText(str(info.path))
            self.detail_duration_label.setText(f"{info.duration_s:.1f} sec")
            self.detail_events_label.setText(str(info.event_count))
            self.delete_btn.setEnabled(True)
        else:
            self.detail_name_label.setText("--")
            self.detail_path_label.setText("--")
            self.detail_duration_label.setText("--")
            self.detail_events_label.setText("--")
            self.delete_btn.setEnabled(False)

    def _delete_session(self) -> None:
        """Delete the selected session."""
        item = self.sessions_list.currentItem()
        if not item:
            return

        name = item.text()

        reply = QMessageBox.question(
            self,
            "Delete Session",
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
    """
    Session panel for recording and replay.

    Layout:
        ┌───────────────┬───────────────────────────────────┐
        │ Recording     │  (tab content)                    │
        │ Replay        │                                    │
        │ Sessions      │                                    │
        └───────────────┴───────────────────────────────────┘
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

    def _setup_ui(self) -> None:
        """Set up the session panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tab widget
        self.tabs = QTabWidget()

        # Recording tab
        self.recording_tab = RecordingTab(self.signals, self.controller, self.settings)
        self.tabs.addTab(self.recording_tab, "Recording")

        # Replay tab
        self.replay_tab = ReplayTab(self.signals, self.controller, self.settings)
        self.tabs.addTab(self.replay_tab, "Replay")

        # Sessions tab
        self.sessions_tab = SessionsTab(self.signals, self.controller, self.settings)
        self.tabs.addTab(self.sessions_tab, "Sessions")

        layout.addWidget(self.tabs)
