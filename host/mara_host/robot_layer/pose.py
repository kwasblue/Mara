# mara_host/robot_layer/pose.py
"""
Pose tracking for robot joints.

Tracks joint positions by name with freshness indicators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Literal

from .model import RobotModel


Freshness = Literal["fresh", "recent", "stale", "unknown"]


@dataclass
class PoseSnapshot:
    """Snapshot of robot pose at a point in time."""
    angles: dict[str, float]
    timestamp: datetime
    source: str  # "commanded", "telemetry", "estimated"


class PoseTracker:
    """
    Track joint positions by name.

    Maintains commanded positions and optionally telemetry feedback.
    Provides freshness indicators for LLM context.
    """

    # Freshness thresholds
    FRESH_THRESHOLD = timedelta(seconds=1)
    RECENT_THRESHOLD = timedelta(seconds=5)

    def __init__(self, model: RobotModel):
        self.model = model

        # Commanded positions (what we told the robot to do)
        self._commanded: dict[str, float] = {}
        self._commanded_at: dict[str, datetime] = {}

        # Telemetry positions (what sensors report) - optional
        self._telemetry: dict[str, float] = {}
        self._telemetry_at: dict[str, datetime] = {}

        # History for debugging/replay
        self._history: list[PoseSnapshot] = []
        self._max_history = 100

    def record_command(self, joint: str, angle: float) -> None:
        """Record a commanded position."""
        now = datetime.now()
        self._commanded[joint] = angle
        self._commanded_at[joint] = now

        # Add to history
        self._add_snapshot("commanded")

    def update_telemetry(self, joint: str, angle: float) -> None:
        """Update from telemetry/sensor reading."""
        now = datetime.now()
        self._telemetry[joint] = angle
        self._telemetry_at[joint] = now

    def get_current(self) -> dict[str, float]:
        """
        Get best estimate of current pose.

        Priority: telemetry > commanded > home
        """
        pose = {}
        for name, joint in self.model.joints.items():
            if name in self._telemetry:
                pose[name] = self._telemetry[name]
            elif name in self._commanded:
                pose[name] = self._commanded[name]
            else:
                pose[name] = joint.home
        return pose

    def get_commanded(self) -> dict[str, float]:
        """Get last commanded positions only."""
        pose = {}
        for name, joint in self.model.joints.items():
            pose[name] = self._commanded.get(name, joint.home)
        return pose

    def get_age(self, joint: str) -> Optional[timedelta]:
        """Get age of joint data (commanded or telemetry)."""
        now = datetime.now()

        # Prefer telemetry age if available
        if joint in self._telemetry_at:
            return now - self._telemetry_at[joint]
        if joint in self._commanded_at:
            return now - self._commanded_at[joint]

        return None

    def get_freshness(self, joint: str) -> Freshness:
        """Get freshness indicator for joint."""
        age = self.get_age(joint)

        if age is None:
            return "unknown"
        if age < self.FRESH_THRESHOLD:
            return "fresh"
        if age < self.RECENT_THRESHOLD:
            return "recent"
        return "stale"

    def get_source(self, joint: str) -> str:
        """Get source of joint data."""
        if joint in self._telemetry:
            return "telemetry"
        if joint in self._commanded:
            return "commanded"
        return "home"

    def get_detailed(self) -> dict[str, dict]:
        """Get detailed pose info for each joint."""
        result = {}
        for name, joint in self.model.joints.items():
            angle = self.get_current().get(name, joint.home)
            result[name] = {
                "angle": angle,
                "freshness": self.get_freshness(name),
                "source": self.get_source(name),
                "age_ms": self._get_age_ms(name),
                "pct_of_range": self._angle_to_pct(name, angle),
            }
        return result

    def _get_age_ms(self, joint: str) -> Optional[int]:
        """Get age in milliseconds."""
        age = self.get_age(joint)
        if age:
            return int(age.total_seconds() * 1000)
        return None

    def _angle_to_pct(self, joint: str, angle: float) -> float:
        """Convert angle to percentage of range."""
        j = self.model.joints[joint]
        range_size = j.max_angle - j.min_angle
        if range_size == 0:
            return 50.0
        return (angle - j.min_angle) / range_size * 100

    def _add_snapshot(self, source: str) -> None:
        """Add current state to history."""
        self._history.append(PoseSnapshot(
            angles=dict(self._commanded),
            timestamp=datetime.now(),
            source=source,
        ))

        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(self, limit: int = 10) -> list[PoseSnapshot]:
        """Get recent pose history."""
        return self._history[-limit:]

    def clear(self) -> None:
        """Clear all tracked positions."""
        self._commanded.clear()
        self._commanded_at.clear()
        self._telemetry.clear()
        self._telemetry_at.clear()
        self._history.clear()
