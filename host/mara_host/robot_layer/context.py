# mara_host/robot_layer/context.py
"""
Robot state context provider for LLM consumption.

Formats robot state into human/LLM-readable summaries.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .model import RobotModel
from .pose import PoseTracker

if TYPE_CHECKING:
    from mara_host.services.control.state_service import StateService


class RobotStateContext:
    """
    Provides formatted state information for LLM consumption.

    Aggregates data from robot model, pose tracker, and services
    into coherent, readable summaries.
    """

    def __init__(
        self,
        model: RobotModel,
        pose_tracker: PoseTracker,
        state_service: Optional['StateService'] = None,
        telemetry_service=None,
    ):
        self.model = model
        self._pose = pose_tracker
        self._state = state_service
        self._telemetry = telemetry_service

    def get_state_summary(self) -> str:
        """
        Get complete state summary for LLM.

        Includes safety status, current pose, and relevant warnings.
        """
        lines = ["# Robot State", ""]

        # Safety/arm status
        lines.extend(self._format_safety_status())

        # Current pose
        lines.append("\n## Pose")
        lines.extend(self._format_pose())

        # Freshness legend
        lines.append("\n● fresh (<1s)  ○ recent (<5s)  ⚠ stale (>5s)")

        return "\n".join(lines)

    def _format_safety_status(self) -> list[str]:
        """Format safety/arm status."""
        lines = []

        if self._state:
            # Get state from StateService
            state = getattr(self._state, 'current_state', None)
            if state:
                state_name = state.name if hasattr(state, 'name') else str(state)
            else:
                state_name = "UNKNOWN"

            # Status icon
            icons = {
                "ARMED": "🟢",
                "ACTIVE": "🟢",
                "IDLE": "🟡",
                "ESTOP": "🔴",
                "ERROR": "🔴",
                "UNKNOWN": "⚪",
            }
            icon = icons.get(state_name, "⚪")

            lines.append(f"## Status: {icon} {state_name}")

            # Contextual hints
            if state_name == "IDLE":
                lines.append("- Robot is idle. Call mara_arm to enable motion.")
            elif state_name == "ESTOP":
                lines.append("- ESTOP active! Clear estop before moving.")
            elif state_name in ("ARMED", "ACTIVE"):
                lines.append("- Ready for motion commands.")
        else:
            lines.append("## Status: ⚪ UNKNOWN")
            lines.append("- State service not available")

        return lines

    def _format_pose(self) -> list[str]:
        """Format current pose."""
        lines = []
        pose = self._pose.get_current()

        for name, angle in pose.items():
            joint = self.model.joints.get(name)
            freshness = self._pose.get_freshness(name)

            # Freshness icon
            icon = {"fresh": "●", "recent": "○", "stale": "⚠", "unknown": "?"}.get(
                freshness, "?"
            )

            # Percentage of range
            if joint:
                range_size = joint.max_angle - joint.min_angle
                if range_size > 0:
                    pct = (angle - joint.min_angle) / range_size * 100
                    lines.append(f"- {name}: {angle:.1f}° ({pct:.0f}%) {icon}")
                else:
                    lines.append(f"- {name}: {angle:.1f}° {icon}")
            else:
                lines.append(f"- {name}: {angle:.1f}° {icon}")

        if not pose:
            lines.append("- No pose data (move joints to track)")

        return lines

    def format_pose(self) -> str:
        """Format just the pose (for robot_pose tool)."""
        lines = ["Current pose:"]

        detailed = self._pose.get_detailed()
        for name, info in detailed.items():
            joint = self.model.joints.get(name)
            angle = info["angle"]
            pct = info["pct_of_range"]
            freshness = info["freshness"]

            icon = {"fresh": "●", "recent": "○", "stale": "⚠", "unknown": "?"}.get(
                freshness, "?"
            )

            lines.append(f"  {name}: {angle:.1f}° ({pct:.0f}% of range) {icon}")

        if not detailed:
            lines.append("  No pose data available")

        return "\n".join(lines)

    def format_sensors(self) -> str:
        """Format sensor readings (for robot_sensors tool)."""
        if not self._telemetry:
            return "No telemetry service available."

        lines = ["Sensor readings:"]

        # IMU data
        imu = getattr(self._telemetry, 'imu', None)
        if imu and imu.value:
            data = imu.value
            freshness = imu.freshness if hasattr(imu, 'freshness') else "unknown"
            icon = {"fresh": "●", "aging": "○", "stale": "⚠"}.get(freshness, "?")

            if isinstance(data, dict):
                ax, ay, az = data.get('ax', 0), data.get('ay', 0), data.get('az', 0)
                gx, gy, gz = data.get('gx', 0), data.get('gy', 0), data.get('gz', 0)
                lines.append(f"  {icon} IMU accel: ({ax:.2f}, {ay:.2f}, {az:.2f}) m/s²")
                lines.append(f"  {icon} IMU gyro: ({gx:.2f}, {gy:.2f}, {gz:.2f}) rad/s")

        # Encoder data
        encoders = getattr(self._telemetry, 'encoders', {})
        for enc_id, enc in encoders.items():
            if enc and enc.value:
                freshness = enc.freshness if hasattr(enc, 'freshness') else "unknown"
                icon = {"fresh": "●", "aging": "○", "stale": "⚠"}.get(freshness, "?")
                data = enc.value
                if isinstance(data, dict):
                    ticks = data.get('ticks', 0)
                    lines.append(f"  {icon} Encoder {enc_id}: {ticks} ticks")

        if len(lines) == 1:
            lines.append("  No sensor data available")

        lines.append("")
        lines.append("● fresh  ○ aging  ⚠ stale")

        return "\n".join(lines)

    def get_system_context(self) -> str:
        """
        Get static robot description for system prompt.

        This is the context that doesn't change during a session -
        robot structure, joint descriptions, capabilities.
        """
        lines = [
            f"# Robot: {self.model.name}",
            f"Type: {self.model.type}",
        ]

        if self.model.description:
            lines.append(f"Description: {self.model.description}")

        lines.append("")
        lines.append("## Structure")
        lines.extend(self._format_structure())

        lines.append("")
        lines.append("## Joints")
        for name, joint in self.model.joints.items():
            lines.append(f"\n### {name}")
            lines.append(f"- Range: {joint.min_angle}° to {joint.max_angle}°")
            lines.append(f"- Home: {joint.home}°")
            if joint.zero_position:
                lines.append(f"- At {joint.min_angle}°: {joint.zero_position}")
            if joint.max_position:
                lines.append(f"- At {joint.max_angle}°: {joint.max_position}")

        lines.append("")
        lines.append("## Control")
        lines.append("- Use robot_move to move joints by name")
        lines.append("- Use robot_pose to check current positions")
        lines.append("- Use robot_state for full status")
        lines.append("- Safety limits are enforced automatically")

        return "\n".join(lines)

    def _format_structure(self) -> list[str]:
        """Format kinematic structure as tree."""
        lines = []

        # Find root joints (no parent)
        roots = [j for j in self.model.joints.values() if j.parent is None]

        def format_joint(joint, indent=0):
            prefix = "  " * indent + ("└── " if indent > 0 else "")
            lines.append(f"{prefix}{joint.name} ({joint.actuator.value})")

            # Find children
            children = [
                j for j in self.model.joints.values()
                if j.parent == joint.name
            ]
            for child in children:
                format_joint(child, indent + 1)

        for root in roots:
            format_joint(root)

        return lines
