# mara_host/workflows/recording/record.py
"""
Recording workflow.

Records robot events for later replay or analysis.
"""

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from mara_host.workflows.base import BaseWorkflow, WorkflowResult, WorkflowState


@dataclass
class RecordedEvent:
    """A single recorded event."""
    timestamp: float
    topic: str
    data: dict[str, Any]


@dataclass
class RecordingStats:
    """Recording statistics."""
    event_count: int = 0
    duration_s: float = 0.0
    start_time: float = 0.0
    topics: set[str] = field(default_factory=set)


class RecordingWorkflow(BaseWorkflow):
    """
    Recording workflow.

    Records robot events (telemetry, commands, etc.) to a session
    file for later replay or analysis.

    Usage:
        workflow = RecordingWorkflow(client)
        workflow.on_progress = lambda p, s: print(f"{p}%: {s}")

        # Start recording (returns immediately)
        result = await workflow.run(
            session_name="my_session",
            duration_s=60,  # 0 for unlimited
        )

        # Events are recorded automatically
        # Call workflow.stop() to end recording
    """

    def __init__(self, client):
        super().__init__(client)
        self._events: list[RecordedEvent] = []
        self._stats = RecordingStats()
        self._recording = False
        self._session_name = ""
        self._output_path: Optional[Path] = None

    @property
    def name(self) -> str:
        return "Recording"

    @property
    def event_count(self) -> int:
        """Get current event count."""
        return self._stats.event_count

    @property
    def duration_s(self) -> float:
        """Get current recording duration."""
        if self._stats.start_time > 0:
            return time.time() - self._stats.start_time
        return 0.0

    async def run(
        self,
        session_name: str = "",
        duration_s: float = 0,
        log_dir: str = "logs",
        on_event: Optional[Callable[[RecordedEvent], None]] = None,
    ) -> WorkflowResult:
        """
        Start recording.

        Args:
            session_name: Name for the session (auto-generated if empty)
            duration_s: Recording duration (0 for unlimited)
            log_dir: Directory to save recordings
            on_event: Callback for each event

        Returns:
            WorkflowResult with recording stats
        """
        self.reset()
        self._set_state(WorkflowState.RUNNING)

        # Generate session name if needed
        if not session_name:
            session_name = f"session_{int(time.time())}"

        self._session_name = session_name
        self._events = []
        self._stats = RecordingStats(start_time=time.time())
        self._recording = True

        # Create output path
        output_dir = Path(log_dir) / session_name
        output_dir.mkdir(parents=True, exist_ok=True)
        self._output_path = output_dir / "events.jsonl"

        self._emit_progress(0, f"Recording: {session_name}")

        try:
            # If duration specified, wait for it
            if duration_s > 0:
                start = time.time()
                while time.time() - start < duration_s:
                    if self._check_cancelled():
                        break

                    elapsed = time.time() - start
                    progress = int((elapsed / duration_s) * 100)
                    self._emit_progress(
                        progress,
                        f"Recording... {int(elapsed)}s / {int(duration_s)}s"
                    )

                    await asyncio.sleep(0.1)
            else:
                # Unlimited - wait for cancel
                while not self._check_cancelled():
                    elapsed = time.time() - self._stats.start_time
                    self._emit_progress(
                        50,  # Indeterminate
                        f"Recording... {int(elapsed)}s"
                    )
                    await asyncio.sleep(0.5)

            # Stop recording
            self._recording = False
            self._stats.duration_s = time.time() - self._stats.start_time

            # Save to file
            self._emit_progress(90, "Saving recording")
            await self._save_events()

            self._emit_progress(100, f"Saved {self._stats.event_count} events")

            return WorkflowResult.success({
                "session_name": self._session_name,
                "path": str(self._output_path),
                "event_count": self._stats.event_count,
                "duration_s": self._stats.duration_s,
                "topics": list(self._stats.topics),
            })

        except Exception as e:
            self._recording = False
            return WorkflowResult.failure(str(e))

    def record_event(self, topic: str, data: dict[str, Any]) -> None:
        """
        Record an event.

        Called by the consumer to add events during recording.

        Args:
            topic: Event topic (e.g., "telemetry", "command")
            data: Event data
        """
        if not self._recording:
            return

        event = RecordedEvent(
            timestamp=time.time(),
            topic=topic,
            data=data,
        )

        self._events.append(event)
        self._stats.event_count += 1
        self._stats.topics.add(topic)

    async def _save_events(self) -> None:
        """Save events to file."""
        import json

        if not self._output_path:
            return

        with open(self._output_path, "w") as f:
            for event in self._events:
                line = json.dumps({
                    "timestamp": event.timestamp,
                    "topic": event.topic,
                    "data": event.data,
                })
                f.write(line + "\n")

        # Save metadata
        meta_path = self._output_path.parent / "meta.json"
        import json
        with open(meta_path, "w") as f:
            json.dump({
                "session_name": self._session_name,
                "event_count": self._stats.event_count,
                "duration_s": self._stats.duration_s,
                "start_time": self._stats.start_time,
                "topics": list(self._stats.topics),
            }, f, indent=2)
