# tests/test_robot_layer.py
"""
Tests for the robot abstraction layer.
"""

import asyncio

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from mara_host.robot_layer import (
    load_robot_model,
    validate_robot_model,
    RobotConfigError,
    RobotModel,
    Joint,
    JointType,
    ActuatorType,
    PoseTracker,
    RobotService,
    RobotStateContext,
    Waypoint,
    Trajectory,
    TrajectoryExecution,
)
from mara_host.core.result import ServiceResult


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_model():
    """Create a sample robot model for testing."""
    return RobotModel(
        name="test_robot",
        description="Test robot for unit tests",
        type="manipulator",
        joints={
            "joint_a": Joint(
                name="joint_a",
                type=JointType.REVOLUTE,
                actuator=ActuatorType.SERVO,
                actuator_id=0,
                min_angle=0,
                max_angle=180,
                home=90,
                zero_position="down",
                max_position="up",
            ),
            "joint_b": Joint(
                name="joint_b",
                type=JointType.REVOLUTE,
                actuator=ActuatorType.SERVO,
                actuator_id=1,
                min_angle=30,
                max_angle=150,
                home=90,
                parent="joint_a",
            ),
        },
        chains={"arm": ["joint_a", "joint_b"]},
    )


@pytest.fixture
def mock_servo_service():
    """Create a mock servo service."""
    service = MagicMock()
    service.set_angle = AsyncMock(return_value=ServiceResult.success({"angle": 45}))
    return service


@pytest.fixture
def config_path():
    """Path to example config."""
    return Path(__file__).parent.parent / "mara_host" / "robots" / "arm_3dof.yaml"


# =============================================================================
# Model Tests
# =============================================================================

class TestRobotModel:
    """Tests for RobotModel."""

    def test_get_joint(self, sample_model):
        """Test getting joint by name."""
        joint = sample_model.get_joint("joint_a")
        assert joint.name == "joint_a"
        assert joint.actuator_id == 0

    def test_get_joint_unknown(self, sample_model):
        """Test getting unknown joint raises error."""
        with pytest.raises(ValueError, match="Unknown joint"):
            sample_model.get_joint("nonexistent")

    def test_has_joint(self, sample_model):
        """Test has_joint method."""
        assert sample_model.has_joint("joint_a")
        assert not sample_model.has_joint("nonexistent")

    def test_get_root_joints(self, sample_model):
        """Test getting root joints."""
        roots = sample_model.get_root_joints()
        assert len(roots) == 1
        assert roots[0].name == "joint_a"

    def test_get_children(self, sample_model):
        """Test getting child joints."""
        children = sample_model.get_children("joint_a")
        assert len(children) == 1
        assert children[0].name == "joint_b"

    def test_get_joints_by_actuator(self, sample_model):
        """Test filtering joints by actuator type."""
        servos = sample_model.get_joints_by_actuator(ActuatorType.SERVO)
        assert len(servos) == 2


class TestJoint:
    """Tests for Joint."""

    def test_validate_angle_valid(self, sample_model):
        """Test angle validation with valid angle."""
        joint = sample_model.get_joint("joint_a")
        valid, error = joint.validate_angle(90)
        assert valid
        assert error == ""

    def test_validate_angle_below_min(self, sample_model):
        """Test angle validation below minimum."""
        joint = sample_model.get_joint("joint_a")
        valid, error = joint.validate_angle(-10)
        assert not valid
        assert "below min" in error

    def test_validate_angle_above_max(self, sample_model):
        """Test angle validation above maximum."""
        joint = sample_model.get_joint("joint_a")
        valid, error = joint.validate_angle(200)
        assert not valid
        assert "above max" in error

    def test_clamp_angle(self, sample_model):
        """Test angle clamping."""
        joint = sample_model.get_joint("joint_a")
        assert joint.clamp_angle(-10) == 0
        assert joint.clamp_angle(200) == 180
        assert joint.clamp_angle(90) == 90


# =============================================================================
# Loader Tests
# =============================================================================

class TestLoader:
    """Tests for YAML loader."""

    def test_load_example_config(self, config_path):
        """Test loading the example configuration."""
        if not config_path.exists():
            pytest.skip("Example config not found")

        model = load_robot_model(config_path)
        assert model.name == "arm_3dof"
        assert "shoulder" in model.joints
        assert "elbow" in model.joints
        assert "gripper" in model.joints

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_robot_model("/nonexistent/path.yaml")

    def test_validate_model(self, config_path):
        """Test model validation."""
        if not config_path.exists():
            pytest.skip("Example config not found")

        model = load_robot_model(config_path)
        warnings = validate_robot_model(model)
        assert warnings == []  # Example config should be valid


# =============================================================================
# Pose Tracker Tests
# =============================================================================

class TestPoseTracker:
    """Tests for PoseTracker."""

    def test_initial_pose_is_home(self, sample_model):
        """Test that initial pose uses home positions."""
        tracker = PoseTracker(sample_model)
        pose = tracker.get_current()
        assert pose["joint_a"] == 90  # home
        assert pose["joint_b"] == 90  # home

    def test_record_command(self, sample_model):
        """Test recording commanded position."""
        tracker = PoseTracker(sample_model)
        tracker.record_command("joint_a", 45)
        pose = tracker.get_current()
        assert pose["joint_a"] == 45

    def test_freshness_after_command(self, sample_model):
        """Test freshness is fresh after command."""
        tracker = PoseTracker(sample_model)
        tracker.record_command("joint_a", 45)
        assert tracker.get_freshness("joint_a") == "fresh"

    def test_freshness_unknown_without_command(self, sample_model):
        """Test freshness is unknown without command."""
        tracker = PoseTracker(sample_model)
        assert tracker.get_freshness("joint_a") == "unknown"

    def test_get_source(self, sample_model):
        """Test source tracking."""
        tracker = PoseTracker(sample_model)
        assert tracker.get_source("joint_a") == "home"
        tracker.record_command("joint_a", 45)
        assert tracker.get_source("joint_a") == "commanded"


# =============================================================================
# Robot Service Tests
# =============================================================================

class TestRobotService:
    """Tests for RobotService."""

    @pytest.mark.asyncio
    async def test_move_joint_success(self, sample_model, mock_servo_service):
        """Test successful single joint move."""
        robot = RobotService(sample_model, servo_service=mock_servo_service)
        result = await robot.move_joint("joint_a", 45)

        assert result.ok
        mock_servo_service.set_angle.assert_called_once()
        assert robot.get_pose()["joint_a"] == 45

    @pytest.mark.asyncio
    async def test_move_joint_unknown(self, sample_model, mock_servo_service):
        """Test moving unknown joint returns error."""
        robot = RobotService(sample_model, servo_service=mock_servo_service)
        result = await robot.move_joint("nonexistent", 45)

        assert not result.ok
        assert "Unknown joint" in result.error

    @pytest.mark.asyncio
    async def test_move_joints_multiple(self, sample_model, mock_servo_service):
        """Test moving multiple joints."""
        robot = RobotService(sample_model, servo_service=mock_servo_service)
        result = await robot.move_joints([
            {"joint": "joint_a", "angle": 45},
            {"joint": "joint_b", "angle": 60},
        ])

        assert result.ok
        assert mock_servo_service.set_angle.call_count == 2

    @pytest.mark.asyncio
    async def test_move_joints_from_json(self, sample_model, mock_servo_service):
        """Test moving joints from JSON string."""
        robot = RobotService(sample_model, servo_service=mock_servo_service)
        result = await robot.move_joints('[{"joint": "joint_a", "angle": 45}]')

        assert result.ok

    @pytest.mark.asyncio
    async def test_home(self, sample_model, mock_servo_service):
        """Test homing joints."""
        robot = RobotService(sample_model, servo_service=mock_servo_service)
        result = await robot.home()

        assert result.ok
        # Should have called set_angle for each joint
        assert mock_servo_service.set_angle.call_count == 2

    def test_describe(self, sample_model):
        """Test describe output."""
        robot = RobotService(sample_model, servo_service=None)
        desc = robot.describe()

        assert "test_robot" in desc
        assert "joint_a" in desc
        assert "joint_b" in desc
        assert "Range:" in desc


# =============================================================================
# Context Tests
# =============================================================================

class TestRobotStateContext:
    """Tests for RobotStateContext."""

    def test_get_state_summary(self, sample_model):
        """Test state summary generation."""
        tracker = PoseTracker(sample_model)
        ctx = RobotStateContext(sample_model, tracker)

        summary = ctx.get_state_summary()
        assert "Robot State" in summary
        assert "Pose" in summary

    def test_format_pose(self, sample_model):
        """Test pose formatting."""
        tracker = PoseTracker(sample_model)
        tracker.record_command("joint_a", 45)
        ctx = RobotStateContext(sample_model, tracker)

        pose = ctx.format_pose()
        assert "joint_a" in pose
        assert "45.0" in pose

    def test_get_system_context(self, sample_model):
        """Test system context for LLM."""
        tracker = PoseTracker(sample_model)
        ctx = RobotStateContext(sample_model, tracker)

        context = ctx.get_system_context()
        assert "Robot:" in context
        assert "Joints" in context
        assert "Control" in context


# =============================================================================
# Trajectory Tests
# =============================================================================

class TestTrajectory:
    """Tests for Trajectory and Waypoint."""

    def test_waypoint_creation(self):
        """Test creating a waypoint."""
        wp = Waypoint(joints={"shoulder": 45, "elbow": 90}, duration_ms=100)
        assert wp.joints["shoulder"] == 45
        assert wp.joints["elbow"] == 90
        assert wp.duration_ms == 100

    def test_trajectory_from_dicts(self):
        """Test creating trajectory from list of dicts."""
        waypoints = [
            {"shoulder": 45, "elbow": 90},
            {"shoulder": 60, "elbow": 75},
            {"shoulder": 90, "elbow": 60},
        ]
        traj = Trajectory.from_dicts(waypoints, duration_ms=50)

        assert len(traj.waypoints) == 3
        assert traj.waypoints[0].joints["shoulder"] == 45
        assert traj.waypoints[1].joints["shoulder"] == 60
        assert traj.waypoints[2].joints["shoulder"] == 90
        assert all(wp.duration_ms == 50 for wp in traj.waypoints)

    def test_trajectory_from_json(self):
        """Test creating trajectory from JSON string."""
        json_str = '[{"shoulder": 45}, {"shoulder": 90}]'
        traj = Trajectory.from_json(json_str)

        assert len(traj.waypoints) == 2
        assert traj.waypoints[0].joints["shoulder"] == 45
        assert traj.waypoints[1].joints["shoulder"] == 90


class TestTrajectoryExecution:
    """Tests for trajectory execution."""

    @pytest.fixture
    def mock_servo_for_trajectory(self):
        """Create a mock servo service for trajectory tests."""
        service = MagicMock()
        service.set_angle = AsyncMock(return_value=ServiceResult.success({"angle": 45}))
        return service

    @pytest.mark.asyncio
    async def test_execute_trajectory_from_list(self, sample_model, mock_servo_for_trajectory):
        """Test executing trajectory from list of dicts."""
        robot = RobotService(sample_model, servo_service=mock_servo_for_trajectory)

        waypoints = [
            {"joint_a": 45, "joint_b": 90},
            {"joint_a": 60, "joint_b": 75},
        ]
        result = await robot.execute_trajectory(waypoints, frequency_hz=100)

        assert result.ok
        assert result.data["executed"] == 2
        assert result.data["total"] == 2

    @pytest.mark.asyncio
    async def test_execute_trajectory_from_json(self, sample_model, mock_servo_for_trajectory):
        """Test executing trajectory from JSON string."""
        robot = RobotService(sample_model, servo_service=mock_servo_for_trajectory)

        json_str = '[{"joint_a": 45}, {"joint_a": 90}]'
        result = await robot.execute_trajectory(json_str, frequency_hz=100)

        assert result.ok
        assert result.data["executed"] == 2

    @pytest.mark.asyncio
    async def test_execute_trajectory_object(self, sample_model, mock_servo_for_trajectory):
        """Test executing Trajectory object."""
        robot = RobotService(sample_model, servo_service=mock_servo_for_trajectory)

        traj = Trajectory(waypoints=[
            Waypoint(joints={"joint_a": 45}, duration_ms=50),
            Waypoint(joints={"joint_a": 90}, duration_ms=50),
        ])
        result = await robot.execute_trajectory(traj, frequency_hz=100)

        assert result.ok

    @pytest.mark.asyncio
    async def test_execute_trajectory_invalid_joint(self, sample_model, mock_servo_for_trajectory):
        """Test trajectory with invalid joint name."""
        robot = RobotService(sample_model, servo_service=mock_servo_for_trajectory)

        waypoints = [{"invalid_joint": 45}]
        result = await robot.execute_trajectory(waypoints)

        assert not result.ok
        assert "Unknown joint" in result.error

    @pytest.mark.asyncio
    async def test_execute_trajectory_empty(self, sample_model, mock_servo_for_trajectory):
        """Test executing empty trajectory."""
        robot = RobotService(sample_model, servo_service=mock_servo_for_trajectory)

        result = await robot.execute_trajectory([])

        assert not result.ok
        assert "Empty trajectory" in result.error

    @pytest.mark.asyncio
    async def test_execute_trajectory_with_callback(self, sample_model, mock_servo_for_trajectory):
        """Test trajectory with waypoint callback."""
        robot = RobotService(sample_model, servo_service=mock_servo_for_trajectory)

        callback_calls = []
        def on_waypoint(index, waypoint):
            callback_calls.append((index, waypoint))

        waypoints = [
            {"joint_a": 45},
            {"joint_a": 60},
            {"joint_a": 90},
        ]
        result = await robot.execute_trajectory(
            waypoints,
            frequency_hz=100,
            on_waypoint=on_waypoint,
        )

        assert result.ok
        assert len(callback_calls) == 3
        assert callback_calls[0][0] == 0
        assert callback_calls[1][0] == 1
        assert callback_calls[2][0] == 2

    @pytest.mark.asyncio
    async def test_start_trajectory_background(self, sample_model, mock_servo_for_trajectory):
        """Test starting trajectory in background."""
        robot = RobotService(sample_model, servo_service=mock_servo_for_trajectory)

        waypoints = [
            {"joint_a": 45},
            {"joint_a": 90},
        ]
        execution = robot.start_trajectory(waypoints, frequency_hz=100)

        assert isinstance(execution, TrajectoryExecution)
        assert not execution.is_complete

        # Wait for completion
        await execution.wait()

        assert execution.is_complete
        assert execution.progress == 1.0

    @pytest.mark.asyncio
    async def test_trajectory_cancellation(self, sample_model):
        """Test cancelling a running trajectory."""
        # Track how many waypoints were executed
        executed_count = 0
        cancel_after = 3

        slow_servo = MagicMock()
        async def slow_set_angle(*args, **kwargs):
            nonlocal executed_count
            executed_count += 1
            await asyncio.sleep(0.02)  # Simulate servo movement
            return ServiceResult.success({"angle": 45})
        slow_servo.set_angle = slow_set_angle

        robot = RobotService(sample_model, servo_service=slow_servo)

        # Create trajectory with many waypoints
        waypoints = [{"joint_a": i} for i in range(0, 180, 5)]  # 36 waypoints
        execution = robot.start_trajectory(waypoints, frequency_hz=20)

        # Wait for a few waypoints to execute, then cancel
        while executed_count < cancel_after:
            await asyncio.sleep(0.01)

        execution.cancel()
        await execution.wait()

        assert execution.is_complete
        assert execution.is_cancelled
        # Should have stopped before completing all waypoints
        # (allow some slack since cancellation is checked between waypoints)
        assert executed_count < len(waypoints)
