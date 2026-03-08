# mara_host/api/recording.py
"""
Recording and Replay API.

Provides session recording and replay capabilities for logging
telemetry, commands, and events.

Example:
    async with Robot("/dev/ttyUSB0") as robot:
        # Start recording
        session = await robot.recording.start("my_session")

        # Do robot stuff...
        await robot.motion.drive_straight(1.0, 0.5)

        # Stop and save
        await session.stop()

        # Later, replay
        await robot.recording.replay("my_session")

        # Export to file
        await robot.recording.export("my_session", "session.jsonl")
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List, Callable, Any
from pathlib import Path
from datetime import datetime
import json

if TYPE_CHECKING:
    from mara_host.robot import Robot


@dataclass
class RecordingEvent:
    """A single recorded event."""
    timestamp: float
    event_type: str
    data: dict


@dataclass
class RecordingSession:
    """A recording session."""
    name: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    events: List[RecordingEvent] = field(default_factory=list)
    is_recording: bool = True

    @property
    def duration_seconds(self) -> float:
        """Duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def event_count(self) -> int:
        """Number of recorded events."""
        return len(self.events)


class Recording:
    """
    Recording and replay interface.

    Provides:
    - Session recording (telemetry, commands, events)
    - Session replay
    - Export to JSONL format
    - Session listing and management

    Usage:
        rec = robot.recording
        session = await rec.start("experiment_1")
        # ... do stuff ...
        await session.stop()
        await rec.export("experiment_1", "data.jsonl")
    """

    def __init__(self, robot: "Robot") -> None:
        self._robot = robot
        self._sessions: dict[str, RecordingSession] = {}
        self._active_session: Optional[RecordingSession] = None
        self._event_callbacks: List[Callable[[RecordingEvent], None]] = []

    @property
    def is_recording(self) -> bool:
        """Whether recording is active."""
        return self._active_session is not None and self._active_session.is_recording

    @property
    def active_session(self) -> Optional[RecordingSession]:
        """Current recording session."""
        return self._active_session

    async def start(self, name: str) -> RecordingSession:
        """
        Start a new recording session.

        Args:
            name: Session name

        Returns:
            The RecordingSession object
        """
        if self._active_session and self._active_session.is_recording:
            await self.stop()

        session = RecordingSession(name=name)
        self._sessions[name] = session
        self._active_session = session

        # Subscribe to telemetry
        self._robot.bus.subscribe("telemetry.*", self._on_telemetry)
        self._robot.bus.subscribe("command.*", self._on_command)

        return session

    async def stop(self) -> Optional[RecordingSession]:
        """
        Stop the current recording session.

        Returns:
            The completed session, or None if no session was active
        """
        if not self._active_session:
            return None

        self._active_session.is_recording = False
        self._active_session.end_time = datetime.now()

        # Unsubscribe
        self._robot.bus.unsubscribe("telemetry.*", self._on_telemetry)
        self._robot.bus.unsubscribe("command.*", self._on_command)

        session = self._active_session
        self._active_session = None
        return session

    def _on_telemetry(self, topic: str, data: dict) -> None:
        """Handle telemetry event."""
        if self._active_session and self._active_session.is_recording:
            event = RecordingEvent(
                timestamp=(datetime.now() - self._active_session.start_time).total_seconds(),
                event_type=f"telemetry.{topic}",
                data=data,
            )
            self._active_session.events.append(event)

    def _on_command(self, topic: str, data: dict) -> None:
        """Handle command event."""
        if self._active_session and self._active_session.is_recording:
            event = RecordingEvent(
                timestamp=(datetime.now() - self._active_session.start_time).total_seconds(),
                event_type=f"command.{topic}",
                data=data,
            )
            self._active_session.events.append(event)

    async def replay(
        self,
        name: str,
        speed: float = 1.0,
        callback: Optional[Callable[[RecordingEvent], None]] = None,
    ) -> None:
        """
        Replay a recorded session.

        Args:
            name: Session name
            speed: Playback speed multiplier (1.0 = real-time)
            callback: Optional callback for each event
        """
        if name not in self._sessions:
            raise ValueError(f"Session '{name}' not found")

        session = self._sessions[name]
        import asyncio

        last_time = 0.0
        for event in session.events:
            # Wait for event time
            delay = (event.timestamp - last_time) / speed
            if delay > 0:
                await asyncio.sleep(delay)
            last_time = event.timestamp

            # Fire callback
            if callback:
                callback(event)

            # Re-execute commands
            if event.event_type.startswith("command."):
                cmd = event.event_type.replace("command.", "")
                await self._robot.client.send_reliable(cmd, event.data)

    async def export(self, name: str, filepath: str) -> Path:
        """
        Export session to JSONL file.

        Args:
            name: Session name
            filepath: Output file path

        Returns:
            Path to exported file
        """
        if name not in self._sessions:
            raise ValueError(f"Session '{name}' not found")

        session = self._sessions[name]
        path = Path(filepath)

        with open(path, "w") as f:
            # Header
            header = {
                "type": "session_header",
                "name": session.name,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "event_count": session.event_count,
            }
            f.write(json.dumps(header) + "\n")

            # Events
            for event in session.events:
                line = {
                    "type": "event",
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "data": event.data,
                }
                f.write(json.dumps(line) + "\n")

        return path

    async def load(self, filepath: str) -> RecordingSession:
        """
        Load session from JSONL file.

        Args:
            filepath: Input file path

        Returns:
            Loaded RecordingSession
        """
        path = Path(filepath)
        events = []
        header = None

        with open(path) as f:
            for line in f:
                obj = json.loads(line)
                if obj.get("type") == "session_header":
                    header = obj
                elif obj.get("type") == "event":
                    events.append(RecordingEvent(
                        timestamp=obj["timestamp"],
                        event_type=obj["event_type"],
                        data=obj["data"],
                    ))

        if not header:
            raise ValueError(f"Invalid session file: {filepath}")

        session = RecordingSession(
            name=header["name"],
            start_time=datetime.fromisoformat(header["start_time"]),
            end_time=datetime.fromisoformat(header["end_time"]) if header.get("end_time") else None,
            events=events,
            is_recording=False,
        )

        self._sessions[session.name] = session
        return session

    def list_sessions(self) -> List[str]:
        """List all session names."""
        return list(self._sessions.keys())

    def get_session(self, name: str) -> Optional[RecordingSession]:
        """Get session by name."""
        return self._sessions.get(name)

    def delete_session(self, name: str) -> bool:
        """Delete a session."""
        if name in self._sessions:
            del self._sessions[name]
            return True
        return False
