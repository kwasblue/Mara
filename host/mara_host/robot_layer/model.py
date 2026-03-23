# mara_host/robot_layer/model.py
"""
Robot model dataclasses.

Defines the structure for any robot configuration:
- Joints with actuator mappings
- Kinematic chains
- Semantic descriptions for LLM reasoning
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class JointType(Enum):
    """Type of joint motion."""
    REVOLUTE = "revolute"        # Rotates around axis (servo, motor)
    PRISMATIC = "prismatic"      # Slides along axis (linear actuator)
    CONTINUOUS = "continuous"    # Continuous rotation (wheel)


class ActuatorType(Enum):
    """Type of actuator driving the joint."""
    SERVO = "servo"
    DC_MOTOR = "dc_motor"
    STEPPER = "stepper"


@dataclass
class Joint:
    """
    A single joint in the robot.

    Maps a semantic name to hardware configuration.
    """
    name: str
    type: JointType
    actuator: ActuatorType
    actuator_id: int              # servo_id, motor_id, stepper_id
    pin: Optional[int] = None     # GPIO pin if needed for attach

    # Position limits
    min_angle: float = 0.0
    max_angle: float = 180.0
    home: float = 90.0

    # Velocity limit (degrees/second for revolute, units/second for prismatic)
    max_velocity: Optional[float] = None

    # Semantic descriptions for LLM reasoning
    zero_position: str = ""       # What min_angle means: "pointing down"
    max_position: str = ""        # What max_angle means: "pointing up"

    # Kinematic relationship
    parent: Optional[str] = None  # Parent joint name (None = base/root)

    def validate_angle(self, angle: float) -> tuple[bool, str]:
        """Check if angle is within limits."""
        if angle < self.min_angle:
            return False, f"{self.name}: {angle}° below min {self.min_angle}°"
        if angle > self.max_angle:
            return False, f"{self.name}: {angle}° above max {self.max_angle}°"
        return True, ""

    def clamp_angle(self, angle: float) -> float:
        """Clamp angle to joint limits."""
        return max(self.min_angle, min(self.max_angle, angle))


@dataclass
class RobotModel:
    """
    Complete robot model definition.

    Loaded from YAML config, provides semantic structure
    for LLM reasoning and hardware mapping.
    """
    name: str
    description: str
    type: str  # "arm", "mobile_base", "manipulator", "quadruped", etc.

    # Joint definitions by name
    joints: dict[str, Joint] = field(default_factory=dict)

    # Kinematic chains: named sequences from base to tip
    # e.g., {"arm": ["shoulder", "elbow", "wrist"], "gripper": ["gripper"]}
    chains: dict[str, list[str]] = field(default_factory=dict)

    # Joint groups for coordinated control
    # e.g., {"left_arm": ["l_shoulder", "l_elbow"], "wheels": ["left", "right"]}
    groups: dict[str, list[str]] = field(default_factory=dict)

    def get_joint(self, name: str) -> Joint:
        """Get joint by name, raises ValueError if not found."""
        if name not in self.joints:
            available = list(self.joints.keys())
            raise ValueError(f"Unknown joint: '{name}'. Available: {available}")
        return self.joints[name]

    def has_joint(self, name: str) -> bool:
        """Check if joint exists."""
        return name in self.joints

    def get_chain(self, name: str) -> list[Joint]:
        """Get joints in a kinematic chain."""
        if name not in self.chains:
            raise ValueError(f"Unknown chain: '{name}'")
        return [self.joints[j] for j in self.chains[name]]

    def get_group(self, name: str) -> list[Joint]:
        """Get joints in a group."""
        if name not in self.groups:
            raise ValueError(f"Unknown group: '{name}'")
        return [self.joints[j] for j in self.groups[name]]

    def get_joints_by_actuator(self, actuator_type: ActuatorType) -> list[Joint]:
        """Get all joints using a specific actuator type."""
        return [j for j in self.joints.values() if j.actuator == actuator_type]

    def get_root_joints(self) -> list[Joint]:
        """Get joints with no parent (base/root joints)."""
        return [j for j in self.joints.values() if j.parent is None]

    def get_children(self, joint_name: str) -> list[Joint]:
        """Get joints that have this joint as parent."""
        return [j for j in self.joints.values() if j.parent == joint_name]
