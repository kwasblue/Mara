# mara_host/services/recording/recording_service.py
"""
Recording and replay service.

Provides a clean interface for recording robot telemetry sessions
and replaying them for analysis.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, Iterator

from mara_host.core._generated_config import DEFAULT_BAUD_RATE


@dataclass
class RecordedEvent:
    """A recorded event from a session."""
    timestamp: float
    event_type: str
    topic: Optional[str] = None
    data: dict = field(default_factory=dict)


@dataclass
class SessionInfo:
    """Information about a recorded session."""
    name: str
    path: Path
    event_count: int = 0
    duration_s: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    topics: list[str] = field(default_factory=list)


@dataclass
class RecordingConfig:
    """Configuration for a recording session."""
    session_name: str
    log_dir: Path = Path("logs")
    console_output: bool = False
    duration_s: float = 0  # 0 = unlimited

    # Transport config
    serial_port: str = "/dev/ttyUSB0"
    baudrate: int = DEFAULT_BAUD_RATE
    tcp_host: Optional[str] = None
    tcp_port: int = 3333


class RecordingService:
    """
    Service for recording robot telemetry sessions.

    Example:
        config = RecordingConfig(session_name="my_session")

        async with RecordingService(config) as service:
            # Recording happens automatically
            await asyncio.sleep(10)

        # Session saved to logs/my_session/
    """

    def __init__(self, config: RecordingConfig):
        """
        Initialize recording service.

        Args:
            config: Recording configuration
        """
        self.config = config
        self._client = None
        self._bundle = None
        self._session_path: Optional[Path] = None
        self._event_count = 0
        self._start_time: Optional[float] = None

    async def start(self) -> Path:
        """
        Start recording session.

        Returns:
            Path to session directory
        """
        from mara_host.logger.logger import MaraLogBundle
        from mara_host.research.recording import RecordingEventBus, RecordingTransport
        from mara_host.command.client import MaraClient

        # Create session directory
        self._session_path = self.config.log_dir / self.config.session_name
        self._session_path.mkdir(parents=True, exist_ok=True)

        # Create log bundle
        self._bundle = MaraLogBundle(
            name=self.config.session_name,
            log_dir=str(self._session_path),
            console=self.config.console_output,
        )

        # Create transport
        if self.config.tcp_host:
            from mara_host.transport.tcp_transport import AsyncTcpTransport
            inner_transport = AsyncTcpTransport(
                host=self.config.tcp_host,
                port=self.config.tcp_port
            )
        else:
            from mara_host.transport.serial_transport import SerialTransport
            inner_transport = SerialTransport(
                self.config.serial_port,
                baudrate=self.config.baudrate
            )

        # Wrap transport for recording
        transport = RecordingTransport(inner_transport, self._bundle)

        # Create client
        self._client = MaraClient(transport)

        # Wrap event bus for recording with event counting
        recording_bus = RecordingEventBus(self._client.bus, self._bundle)

        # Patch publish to count events (wildcard subscribe doesn't work with exact-match EventBus)
        # NOTE: This monkey-patch captures original_publish by closure. If recording_bus.publish
        # is replaced again after this point, the outer reference becomes stale.
        # The _event_count increment is not strictly thread-safe, but CPython's GIL makes
        # int += atomic in practice. For stricter correctness, use threading.Lock or atomic.
        original_publish = recording_bus.publish
        def counting_publish(topic: str, data):
            self._event_count += 1
            return original_publish(topic, data)
        recording_bus.publish = counting_publish

        self._client.bus = recording_bus

        # Track events
        self._event_count = 0
        self._start_time = time.time()

        # Start client
        await self._client.start()

        return self._session_path

    async def stop(self) -> SessionInfo:
        """
        Stop recording and return session info.

        Returns:
            SessionInfo about the recorded session

        Raises:
            RuntimeError: If stop() is called before start()
        """
        if self._session_path is None:
            raise RuntimeError("Cannot stop recording: start() was never called")

        end_time = time.time()
        duration = end_time - self._start_time if self._start_time else 0

        if self._client:
            await self._client.stop()
            self._client = None

        if self._bundle:
            self._bundle.close()
            self._bundle = None

        return SessionInfo(
            name=self.config.session_name,
            path=self._session_path,
            event_count=self._event_count,
            duration_s=duration,
            start_time=self._start_time,
            end_time=end_time,
        )

    async def record_for_duration(self, duration_s: float) -> SessionInfo:
        """
        Record for a specific duration.

        Args:
            duration_s: Duration in seconds

        Returns:
            SessionInfo after recording
        """
        await self.start()
        try:
            await asyncio.sleep(duration_s)
        finally:
            result = await self.stop()
        return result

    async def __aenter__(self) -> "RecordingService":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    @property
    def client(self):
        """Get the underlying robot client (for sending commands during recording)."""
        return self._client

    @property
    def session_path(self) -> Optional[Path]:
        """Get the session directory path."""
        return self._session_path


class ReplayService:
    """
    Service for replaying recorded sessions.

    Example:
        service = ReplayService("my_session")

        # Iterate through events
        for event in service.events():
            print(f"{event.timestamp}: {event.topic} = {event.data}")

        # Or replay with timing
        await service.replay(speed=2.0, callback=my_handler)
    """

    def __init__(
        self,
        session_name: str,
        log_dir: Path = Path("logs")
    ):
        """
        Initialize replay service.

        Args:
            session_name: Name of the session to replay
            log_dir: Base log directory
        """
        self.session_name = session_name
        self.session_path = log_dir / session_name
        self._events_file = self.session_path / "events.jsonl"

    def get_session_info(self) -> Optional[SessionInfo]:
        """
        Get information about the session.

        Returns:
            SessionInfo or None if session doesn't exist
        """
        if not self._events_file.exists():
            return None

        events = list(self.events())
        if not events:
            return SessionInfo(
                name=self.session_name,
                path=self.session_path,
            )

        topics = set()
        for event in events:
            if event.topic:
                topics.add(event.topic)

        return SessionInfo(
            name=self.session_name,
            path=self.session_path,
            event_count=len(events),
            start_time=events[0].timestamp if events else None,
            end_time=events[-1].timestamp if events else None,
            duration_s=(events[-1].timestamp - events[0].timestamp) if len(events) > 1 else 0,
            topics=sorted(topics),
        )

    def events(self) -> Iterator[RecordedEvent]:
        """
        Iterate through all recorded events.

        Yields:
            RecordedEvent for each event in the session
        """
        if not self._events_file.exists():
            return

        with open(self._events_file) as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                    # Validate JSON is a dict before accessing .get()
                    if not isinstance(data, dict):
                        continue

                    # Handle timestamp formats from different writers:
                    # - JsonlLogger uses "ts_ns" (nanoseconds as int)
                    # - Other writers may use "ts" (seconds as float, or ISO string)
                    timestamp = 0.0
                    if "ts_ns" in data:
                        # Nanoseconds -> seconds
                        timestamp = data["ts_ns"] / 1e9
                    elif "ts" in data:
                        ts_val = data["ts"]
                        if isinstance(ts_val, (int, float)):
                            # If ts > 1e12, assume nanoseconds (dates after 2001)
                            # If ts < 1e12, assume seconds
                            if ts_val > 1e12:
                                timestamp = ts_val / 1e9
                            else:
                                timestamp = float(ts_val)
                        elif isinstance(ts_val, str):
                            # ISO format string - parse it
                            from datetime import datetime
                            try:
                                dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                                timestamp = dt.timestamp()
                            except ValueError:
                                timestamp = 0.0

                    yield RecordedEvent(
                        timestamp=timestamp,
                        event_type=data.get("event", "unknown"),
                        topic=data.get("topic"),
                        data=data.get("data", data),
                    )
                except (json.JSONDecodeError, TypeError, KeyError):
                    # Skip malformed JSON lines
                    continue

    async def replay(
        self,
        speed: float = 1.0,
        callback: Optional[Callable[[RecordedEvent], None]] = None,
        filter_topics: Optional[list[str]] = None,
    ) -> int:
        """
        Replay events with timing.

        Args:
            speed: Playback speed multiplier (1.0 = realtime, 2.0 = 2x speed).
                   Use speed <= 0 to replay as fast as possible without delays.
            callback: Optional callback for each event
            filter_topics: Only replay events with these topics

        Returns:
            Number of events replayed
        """
        last_ts = None
        count = 0

        for event in self.events():
            # Filter by topic if requested
            if filter_topics and event.topic not in filter_topics:
                continue

            # Apply timing (speed <= 0 means no delay / as fast as possible)
            if last_ts is not None and speed > 0:
                delay = (event.timestamp - last_ts) / speed
                if delay > 0:
                    await asyncio.sleep(delay)

            last_ts = event.timestamp

            # Call callback
            if callback:
                callback(event)

            count += 1

        return count

    def filter_events(
        self,
        topics: Optional[list[str]] = None,
        event_types: Optional[list[str]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Iterator[RecordedEvent]:
        """
        Filter events by criteria.

        Args:
            topics: Only include these topics
            event_types: Only include these event types
            start_time: Only include events after this time
            end_time: Only include events before this time

        Yields:
            Matching RecordedEvent objects
        """
        for event in self.events():
            if topics and event.topic not in topics:
                continue
            if event_types and event.event_type not in event_types:
                continue
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue

            yield event

    @staticmethod
    def list_sessions(log_dir: Path = Path("logs")) -> list[str]:
        """
        List available sessions.

        Args:
            log_dir: Base log directory

        Returns:
            List of session names
        """
        if not log_dir.exists():
            return []

        sessions = []
        for path in log_dir.iterdir():
            if path.is_dir() and (path / "events.jsonl").exists():
                sessions.append(path.name)

        return sorted(sessions)
