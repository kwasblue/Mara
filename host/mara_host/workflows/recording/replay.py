# mara_host/workflows/recording/replay.py
"""
Replay workflow.

Replays recorded robot sessions.
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from mara_host.workflows.base import BaseWorkflow, WorkflowResult, WorkflowState


@dataclass
class RecordedEvent:
    """A recorded event."""
    timestamp: float
    topic: str
    data: dict[str, Any]


@dataclass
class SessionInfo:
    """Session metadata."""
    name: str
    path: Path
    event_count: int
    duration_s: float
    start_time: float
    topics: list[str]


class ReplayWorkflow(BaseWorkflow):
    """
    Replay workflow.

    Replays a recorded session with configurable speed
    and filtering.

    Usage:
        workflow = ReplayWorkflow(client)
        workflow.on_progress = lambda p, s: print(f"{p}%: {s}")
        workflow.on_event = lambda e: print(f"Event: {e.topic}")

        result = await workflow.run(
            session_name="my_session",
            speed=1.0,
        )
    """

    def __init__(self, client):
        super().__init__(client)
        self._paused = False
        self._session_info: Optional[SessionInfo] = None
        self.on_event: Callable[[RecordedEvent], None] = lambda e: None

    @property
    def name(self) -> str:
        return "Replay"

    @staticmethod
    def list_sessions(log_dir: str = "logs") -> list[str]:
        """
        List available sessions.

        Args:
            log_dir: Directory containing recordings

        Returns:
            List of session names
        """
        log_path = Path(log_dir)
        if not log_path.exists():
            return []

        sessions = []
        for path in log_path.iterdir():
            if path.is_dir():
                meta_file = path / "meta.json"
                events_file = path / "events.jsonl"
                if meta_file.exists() or events_file.exists():
                    sessions.append(path.name)

        return sorted(sessions)

    def get_session_info(
        self, session_name: str, log_dir: str = "logs"
    ) -> Optional[SessionInfo]:
        """
        Get session metadata.

        Args:
            session_name: Session name
            log_dir: Directory containing recordings

        Returns:
            SessionInfo or None if not found
        """
        session_path = Path(log_dir) / session_name
        meta_path = session_path / "meta.json"

        if not meta_path.exists():
            return None

        with open(meta_path) as f:
            meta = json.load(f)

        return SessionInfo(
            name=meta.get("session_name", session_name),
            path=session_path,
            event_count=meta.get("event_count", 0),
            duration_s=meta.get("duration_s", 0.0),
            start_time=meta.get("start_time", 0.0),
            topics=meta.get("topics", []),
        )

    def _load_events(
        self, session_name: str, log_dir: str = "logs"
    ) -> Iterator[RecordedEvent]:
        """
        Load events from session file.

        Args:
            session_name: Session name
            log_dir: Directory containing recordings

        Yields:
            RecordedEvent objects
        """
        events_path = Path(log_dir) / session_name / "events.jsonl"

        if not events_path.exists():
            return

        with open(events_path) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    yield RecordedEvent(
                        timestamp=data.get("timestamp", 0.0),
                        topic=data.get("topic", ""),
                        data=data.get("data", {}),
                    )

    async def run(
        self,
        session_name: str,
        log_dir: str = "logs",
        speed: float = 1.0,
        filter_topics: Optional[list[str]] = None,
        execute_commands: bool = False,
    ) -> WorkflowResult:
        """
        Replay a session.

        Args:
            session_name: Session to replay
            log_dir: Directory containing recordings
            speed: Playback speed (1.0 = real-time, 0 = instant)
            filter_topics: Only replay these topics (None = all)
            execute_commands: Actually send commands to robot

        Returns:
            WorkflowResult with replay stats
        """
        self.reset()
        self._set_state(WorkflowState.RUNNING)
        self._paused = False

        # Load session info
        info = self.get_session_info(session_name, log_dir)
        if not info:
            return WorkflowResult.failure(f"Session not found: {session_name}")

        self._session_info = info
        total_ms = int(info.duration_s * 1000)

        self._emit_progress(0, f"Replaying: {session_name}")

        events_played = 0
        last_timestamp: Optional[float] = None

        try:
            for event in self._load_events(session_name, log_dir):
                if self._check_cancelled():
                    return WorkflowResult.cancelled()

                # Handle pause
                while self._paused and not self._check_cancelled():
                    await asyncio.sleep(0.1)

                # Filter by topic
                if filter_topics and event.topic not in filter_topics:
                    continue

                # Apply timing
                if last_timestamp is not None and speed > 0:
                    delay = (event.timestamp - last_timestamp) / speed
                    if delay > 0:
                        await asyncio.sleep(delay)

                last_timestamp = event.timestamp

                # Emit event
                self.on_event(event)
                events_played += 1

                # Execute commands if requested
                if execute_commands and event.topic == "command":
                    cmd_name = event.data.get("command", "")
                    cmd_payload = event.data.get("payload", {})
                    if cmd_name:
                        await self._send_command(cmd_name, cmd_payload)

                # Progress
                if info.start_time > 0:
                    current_ms = int((event.timestamp - info.start_time) * 1000)
                    progress = int((current_ms / total_ms) * 100) if total_ms > 0 else 50
                    self._emit_progress(
                        min(progress, 100),
                        f"Replaying... {events_played} events"
                    )

            self._emit_progress(100, f"Complete: {events_played} events")

            return WorkflowResult.success({
                "session_name": session_name,
                "events_played": events_played,
                "total_events": info.event_count,
                "duration_s": info.duration_s,
            })

        except Exception as e:
            return WorkflowResult.failure(str(e))

    def pause(self) -> None:
        """Pause replay."""
        self._paused = True

    def resume(self) -> None:
        """Resume replay."""
        self._paused = False

    @property
    def is_paused(self) -> bool:
        """Check if replay is paused."""
        return self._paused
