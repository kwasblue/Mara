# mara_host/robot_layer/__init__.py
"""
Robot Abstraction Layer.

Provides semantic control of robots through joint names and coordinated movements.
Maps high-level commands to underlying hardware services.

Example:
    from mara_host.robot_layer import load_robot_model, RobotService

    # Load robot definition
    model = load_robot_model("robots/my_robot.yaml")

    # Create service (with existing hardware services)
    robot = RobotService(model, servo_service, motor_service)

    # Control by name
    await robot.move_joint("shoulder", 45)
    await robot.move_joints([
        {"joint": "shoulder", "angle": 60},
        {"joint": "elbow", "angle": 45},
    ])
"""

from .model import (
    RobotModel,
    Joint,
    JointType,
    ActuatorType,
)
from .loader import (
    load_robot_model,
    validate_robot_model,
    RobotConfigError,
)
from .pose import (
    PoseTracker,
    PoseSnapshot,
)
from .service import (
    RobotService,
    Waypoint,
    Trajectory,
    TrajectoryExecution,
)
from .context import RobotStateContext

__all__ = [
    # Model
    "RobotModel",
    "Joint",
    "JointType",
    "ActuatorType",
    # Loader
    "load_robot_model",
    "validate_robot_model",
    "RobotConfigError",
    # Pose
    "PoseTracker",
    "PoseSnapshot",
    # Service
    "RobotService",
    # Trajectory
    "Waypoint",
    "Trajectory",
    "TrajectoryExecution",
    # Context
    "RobotStateContext",
]
