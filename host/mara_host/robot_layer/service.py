# mara_host/robot_layer/service.py
"""
Robot service - semantic control layer.

Maps joint names to hardware IDs and coordinates multi-joint movements.
Delegates to existing host services for actual hardware control.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, TYPE_CHECKING

from .model import RobotModel, ActuatorType
from .pose import PoseTracker

if TYPE_CHECKING:
    from mara_host.services.control.servo_service import ServoService
    from mara_host.services.control.motor_service import MotorService
    from mara_host.services.control.stepper_service import StepperService
    from mara_host.core.result import ServiceResult


@dataclass
class Waypoint:
    """A single point in a trajectory."""
    joints: dict[str, float]  # joint_name -> angle
    duration_ms: int = 50     # Time to reach this waypoint


@dataclass
class Trajectory:
    """A sequence of waypoints to execute."""
    waypoints: list[Waypoint]
    loop: bool = False        # Whether to loop the trajectory

    @classmethod
    def from_dicts(
        cls,
        waypoints: list[dict[str, float]],
        duration_ms: int = 50,
    ) -> 'Trajectory':
        """Create trajectory from list of joint dicts."""
        return cls(
            waypoints=[
                Waypoint(joints=wp, duration_ms=duration_ms)
                for wp in waypoints
            ]
        )

    @classmethod
    def from_json(cls, data: str | list, duration_ms: int = 50) -> 'Trajectory':
        """Create trajectory from JSON string or list."""
        if isinstance(data, str):
            data = json.loads(data)
        return cls.from_dicts(data, duration_ms)


@dataclass
class TrajectoryExecution:
    """Handle for a running trajectory execution."""
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    _complete_event: asyncio.Event = field(default_factory=asyncio.Event)
    _current_index: int = 0
    _total_waypoints: int = 0
    _error: Optional[str] = None

    @property
    def progress(self) -> float:
        """Progress as 0.0 to 1.0."""
        if self._total_waypoints == 0:
            return 0.0
        return self._current_index / self._total_waypoints

    @property
    def is_complete(self) -> bool:
        return self._complete_event.is_set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    @property
    def error(self) -> Optional[str]:
        return self._error

    def cancel(self) -> None:
        """Request cancellation of the trajectory."""
        self._cancel_event.set()

    async def wait(self) -> None:
        """Wait for trajectory to complete."""
        await self._complete_event.wait()


class RobotService:
    """
    High-level robot control with semantic joint names.

    Maps joint names to actuator IDs and coordinates movements.
    Delegates to existing services (ServoService, MotorService, etc.)
    for actual hardware control.

    Example:
        robot = RobotService(model, servo_service)

        # Move single joint by name
        await robot.move_joint("shoulder", 45)

        # Move multiple joints simultaneously
        await robot.move_joints([
            {"joint": "shoulder", "angle": 60},
            {"joint": "elbow", "angle": 45},
        ])

        # Home all joints
        await robot.home()

        # Execute trajectory (for diffusion policies, motion planning)
        await robot.execute_trajectory([
            {"shoulder": 45, "elbow": 90},
            {"shoulder": 60, "elbow": 75},
        ], frequency_hz=20)

        # Background trajectory with cancellation
        execution = robot.start_trajectory(waypoints)
        execution.cancel()  # If needed
        await execution.wait()
    """

    def __init__(
        self,
        model: RobotModel,
        servo_service: Optional['ServoService'] = None,
        motor_service: Optional['MotorService'] = None,
        stepper_service: Optional['StepperService'] = None,
    ):
        self.model = model
        self._servo = servo_service
        self._motor = motor_service
        self._stepper = stepper_service
        self.pose = PoseTracker(model)

    async def move_joint(
        self,
        joint: str,
        angle: float,
        duration_ms: int = 300,
    ) -> 'ServiceResult':
        """
        Move a single joint by name.

        Args:
            joint: Joint name (e.g., "shoulder")
            angle: Target angle in degrees
            duration_ms: Movement duration in milliseconds

        Returns:
            ServiceResult with success/failure
        """
        return await self.move_joints(
            [{"joint": joint, "angle": angle}],
            duration_ms=duration_ms,
        )

    async def move_joints(
        self,
        moves: list[dict] | str,
        duration_ms: int = 300,
    ) -> 'ServiceResult':
        """
        Move multiple joints simultaneously.

        Args:
            moves: List of moves [{"joint": "name", "angle": degrees}, ...]
                   or JSON string with same format
            duration_ms: Movement duration in milliseconds

        Returns:
            ServiceResult with moved joints or error
        """
        from mara_host.core.result import ServiceResult

        # Parse JSON if string (from MCP tool)
        if isinstance(moves, str):
            try:
                moves = json.loads(moves)
            except json.JSONDecodeError as e:
                return ServiceResult.failure(f"Invalid JSON: {e}")

        if not moves:
            return ServiceResult.failure("No moves specified")

        # Validate all joints exist
        for move in moves:
            joint_name = move.get("joint")
            if not joint_name:
                return ServiceResult.failure("Move missing 'joint' field")
            if not self.model.has_joint(joint_name):
                available = list(self.model.joints.keys())
                return ServiceResult.failure(
                    f"Unknown joint: '{joint_name}'. Available: {available}"
                )

        # Group moves by actuator type for parallel execution
        servo_moves = []
        motor_moves = []
        stepper_moves = []

        for move in moves:
            joint_name = move["joint"]
            angle = move["angle"]
            joint = self.model.get_joint(joint_name)

            if joint.actuator == ActuatorType.SERVO:
                servo_moves.append((joint_name, joint, angle))
            elif joint.actuator == ActuatorType.DC_MOTOR:
                motor_moves.append((joint_name, joint, angle))
            elif joint.actuator == ActuatorType.STEPPER:
                stepper_moves.append((joint_name, joint, angle))

        # Execute all moves in parallel
        tasks = []
        task_info = []  # Track which task is for which joint

        # Servo moves
        if servo_moves:
            if not self._servo:
                return ServiceResult.failure("No servo service configured")
            for joint_name, joint, angle in servo_moves:
                task = self._servo.set_angle(
                    joint.actuator_id,
                    angle,
                    duration_ms=duration_ms,
                )
                tasks.append(task)
                task_info.append((joint_name, angle, "servo"))

        # Motor moves (interpret angle as speed -1 to 1)
        if motor_moves:
            if not self._motor:
                return ServiceResult.failure("No motor service configured")
            for joint_name, joint, angle in motor_moves:
                # For DC motors, map angle to speed
                # Could be customized per joint
                speed = angle / 180.0  # Simple mapping: 0-180 -> 0-1
                task = self._motor.set_speed(joint.actuator_id, speed)
                tasks.append(task)
                task_info.append((joint_name, angle, "motor"))

        # Stepper moves (interpret angle as steps or position)
        if stepper_moves:
            if not self._stepper:
                return ServiceResult.failure("No stepper service configured")
            for joint_name, joint, angle in stepper_moves:
                # For steppers, could be absolute position or relative steps
                task = self._stepper.move_to(joint.actuator_id, int(angle))
                tasks.append(task)
                task_info.append((joint_name, angle, "stepper"))

        # Await all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        moved = []
        errors = []

        for (joint_name, angle, actuator_type), result in zip(task_info, results):
            if isinstance(result, Exception):
                errors.append(f"{joint_name}: {result}")
            elif hasattr(result, 'ok'):
                if result.ok:
                    moved.append(joint_name)
                    self.pose.record_command(joint_name, angle)
                else:
                    errors.append(f"{joint_name}: {result.error}")
            else:
                # Assume success if no error
                moved.append(joint_name)
                self.pose.record_command(joint_name, angle)

        if errors:
            return ServiceResult.failure(
                f"Some moves failed: {'; '.join(errors)}",
                data={"moved": moved, "errors": errors},
            )

        return ServiceResult.success({"moved": moved})

    async def home(
        self,
        joints: Optional[list[str] | str] = None,
        duration_ms: int = 500,
    ) -> 'ServiceResult':
        """
        Move joints to their home positions.

        Args:
            joints: List of joint names to home, or None for all joints.
                    Can also be JSON string array.
            duration_ms: Movement duration

        Returns:
            ServiceResult
        """
        # Parse joints argument
        if joints is None:
            joint_names = list(self.model.joints.keys())
        elif isinstance(joints, str):
            try:
                joint_names = json.loads(joints)
                if not isinstance(joint_names, list):
                    joint_names = [joints]
            except json.JSONDecodeError:
                joint_names = [joints]  # Single joint name
        else:
            joint_names = joints

        # Build moves to home positions
        moves = []
        for name in joint_names:
            if name in self.model.joints:
                moves.append({
                    "joint": name,
                    "angle": self.model.joints[name].home,
                })

        if not moves:
            from mara_host.core.result import ServiceResult
            return ServiceResult.failure("No valid joints to home")

        return await self.move_joints(moves, duration_ms=duration_ms)

    async def execute_trajectory(
        self,
        trajectory: Trajectory | list[dict[str, float]] | str,
        frequency_hz: float = 20.0,
        interpolate: bool = True,
        on_waypoint: Optional[Callable[[int, Waypoint], None]] = None,
    ) -> 'ServiceResult':
        """
        Execute a trajectory of waypoints.

        Args:
            trajectory: Trajectory object, list of joint dicts, or JSON string
            frequency_hz: Execution frequency (waypoints per second)
            interpolate: If True, interpolate between waypoints for smooth motion
            on_waypoint: Optional callback called at each waypoint (index, waypoint)

        Returns:
            ServiceResult with execution summary

        Example:
            # From list of dicts
            await robot.execute_trajectory([
                {"shoulder": 45, "elbow": 90},
                {"shoulder": 60, "elbow": 75},
                {"shoulder": 90, "elbow": 60},
            ], frequency_hz=10)

            # From Trajectory object
            traj = Trajectory.from_dicts(waypoints, duration_ms=100)
            await robot.execute_trajectory(traj)
        """
        from mara_host.core.result import ServiceResult

        # Normalize input to Trajectory
        if isinstance(trajectory, str):
            try:
                trajectory = Trajectory.from_json(trajectory)
            except json.JSONDecodeError as e:
                return ServiceResult.failure(f"Invalid trajectory JSON: {e}")
        elif isinstance(trajectory, list):
            trajectory = Trajectory.from_dicts(trajectory)

        if not trajectory.waypoints:
            return ServiceResult.failure("Empty trajectory")

        # Validate all joints in trajectory exist
        all_joints = set()
        for wp in trajectory.waypoints:
            all_joints.update(wp.joints.keys())

        for joint_name in all_joints:
            if not self.model.has_joint(joint_name):
                available = list(self.model.joints.keys())
                return ServiceResult.failure(
                    f"Unknown joint in trajectory: '{joint_name}'. Available: {available}"
                )

        # Execute waypoints
        period = 1.0 / frequency_hz
        executed = 0
        errors = []

        for i, waypoint in enumerate(trajectory.waypoints):
            start_time = time.monotonic()

            # Optionally interpolate from current pose
            if interpolate and i > 0:
                moves = self._interpolate_to_waypoint(waypoint)
            else:
                moves = [
                    {"joint": j, "angle": a}
                    for j, a in waypoint.joints.items()
                ]

            # Execute the waypoint
            result = await self.move_joints(moves, duration_ms=waypoint.duration_ms)

            if result.ok:
                executed += 1
            else:
                errors.append(f"Waypoint {i}: {result.error}")
                # Continue despite errors (best effort)

            # Callback
            if on_waypoint:
                on_waypoint(i, waypoint)

            # Maintain frequency
            elapsed = time.monotonic() - start_time
            sleep_time = period - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        if errors:
            return ServiceResult.failure(
                f"Trajectory completed with errors",
                data={"executed": executed, "total": len(trajectory.waypoints), "errors": errors},
            )

        return ServiceResult.success({
            "executed": executed,
            "total": len(trajectory.waypoints),
        })

    def start_trajectory(
        self,
        trajectory: Trajectory | list[dict[str, float]] | str,
        frequency_hz: float = 20.0,
        interpolate: bool = True,
        on_waypoint: Optional[Callable[[int, Waypoint], None]] = None,
    ) -> TrajectoryExecution:
        """
        Start trajectory execution in the background.

        Returns a TrajectoryExecution handle for monitoring and cancellation.

        Example:
            execution = robot.start_trajectory(waypoints)

            # Check progress
            print(f"Progress: {execution.progress:.0%}")

            # Cancel if needed
            execution.cancel()

            # Wait for completion
            await execution.wait()
        """
        # Normalize input
        if isinstance(trajectory, str):
            trajectory = Trajectory.from_json(trajectory)
        elif isinstance(trajectory, list):
            trajectory = Trajectory.from_dicts(trajectory)

        execution = TrajectoryExecution()
        execution._total_waypoints = len(trajectory.waypoints)

        async def run():
            try:
                period = 1.0 / frequency_hz

                for i, waypoint in enumerate(trajectory.waypoints):
                    # Check for cancellation
                    if execution._cancel_event.is_set():
                        break

                    execution._current_index = i
                    start_time = time.monotonic()

                    # Build moves
                    if interpolate and i > 0:
                        moves = self._interpolate_to_waypoint(waypoint)
                    else:
                        moves = [
                            {"joint": j, "angle": a}
                            for j, a in waypoint.joints.items()
                        ]

                    # Execute
                    result = await self.move_joints(moves, duration_ms=waypoint.duration_ms)

                    if not result.ok:
                        execution._error = result.error
                        # Continue best-effort

                    if on_waypoint:
                        on_waypoint(i, waypoint)

                    # Maintain frequency
                    elapsed = time.monotonic() - start_time
                    sleep_time = period - elapsed
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

                execution._current_index = len(trajectory.waypoints)
            finally:
                execution._complete_event.set()

        # Start background task
        asyncio.create_task(run())
        return execution

    def _interpolate_to_waypoint(self, waypoint: Waypoint) -> list[dict]:
        """
        Create moves that interpolate from current pose to waypoint.

        For now, this just returns direct moves. Could be enhanced to
        generate intermediate points for smoother motion.
        """
        # Get current pose
        current = self.pose.get_current()

        # For each joint in waypoint, create a move
        moves = []
        for joint_name, target_angle in waypoint.joints.items():
            # Could add intermediate interpolation here
            # For now, just move directly (servo handles smoothing)
            moves.append({"joint": joint_name, "angle": target_angle})

        return moves

    def get_pose(self) -> dict[str, float]:
        """Get current joint positions by name."""
        return self.pose.get_current()

    def describe(self) -> str:
        """
        Generate LLM-readable robot description.

        Returns structured text describing the robot's joints,
        their limits, relationships, and current state.
        """
        lines = [
            f"# Robot: {self.model.name}",
            f"Type: {self.model.type}",
        ]

        if self.model.description:
            lines.append(f"Description: {self.model.description}")

        lines.append("")
        lines.append("## Joints")

        for name, joint in self.model.joints.items():
            parent_info = f" (attached to {joint.parent})" if joint.parent else " (base)"
            lines.append(f"\n### {name}{parent_info}")
            lines.append(f"- Range: {joint.min_angle}° to {joint.max_angle}°")
            lines.append(f"- Home: {joint.home}°")

            if joint.zero_position:
                lines.append(f"- At {joint.min_angle}°: {joint.zero_position}")
            if joint.max_position:
                lines.append(f"- At {joint.max_angle}°: {joint.max_position}")

        # Current pose
        lines.append("\n## Current Pose")
        pose = self.get_pose()
        for name, angle in pose.items():
            freshness = self.pose.get_freshness(name)
            icon = {"fresh": "●", "recent": "○", "stale": "⚠", "unknown": "?"}.get(
                freshness, "?"
            )
            lines.append(f"- {name}: {angle:.1f}° {icon}")

        lines.append("\n● fresh (<1s)  ○ recent (<5s)  ⚠ stale (>5s)  ? unknown")

        return "\n".join(lines)
