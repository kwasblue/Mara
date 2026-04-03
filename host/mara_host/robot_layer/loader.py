# mara_host/robot_layer/loader.py
"""
Robot model YAML loader.

Loads robot configuration from YAML files and validates structure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union
import yaml

from .model import RobotModel, Joint, JointType, ActuatorType


class RobotConfigError(Exception):
    """Error loading or validating robot configuration."""
    pass


def load_robot_model(path: Union[Path, str]) -> RobotModel:
    """
    Load robot model from YAML config file.

    Args:
        path: Path to YAML configuration file

    Returns:
        RobotModel instance

    Raises:
        RobotConfigError: If config is invalid
        FileNotFoundError: If file doesn't exist
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Robot config not found: {path}")

    with open(path) as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise RobotConfigError(f"Invalid YAML: {e}")

    if not config:
        raise RobotConfigError("Empty configuration file")

    return _parse_config(config, path)


def _parse_config(config: dict, source_path: Path) -> RobotModel:
    """Parse configuration dict into RobotModel."""

    # Required fields
    name = config.get("name")
    if not name:
        raise RobotConfigError("Missing required field: 'name'")

    # Optional fields with defaults
    description = config.get("description", "")
    robot_type = config.get("type", "robot")

    # Parse joints
    joints_config = config.get("joints", {})
    if not joints_config:
        raise RobotConfigError("No joints defined in configuration")

    joints = {}
    for joint_name, jconf in joints_config.items():
        try:
            joints[joint_name] = _parse_joint(joint_name, jconf)
        except (ValueError, KeyError) as e:
            raise RobotConfigError(f"Invalid joint '{joint_name}': {e}")

    # Validate parent references
    for joint in joints.values():
        if joint.parent and joint.parent not in joints:
            raise RobotConfigError(
                f"Joint '{joint.name}' references unknown parent '{joint.parent}'"
            )

    # Parse chains
    chains = config.get("chains", {})
    for chain_name, chain_joints in chains.items():
        for joint_name in chain_joints:
            if joint_name not in joints:
                raise RobotConfigError(
                    f"Chain '{chain_name}' references unknown joint '{joint_name}'"
                )

    # Parse groups
    groups = config.get("groups", {})
    for group_name, group_joints in groups.items():
        for joint_name in group_joints:
            if joint_name not in joints:
                raise RobotConfigError(
                    f"Group '{group_name}' references unknown joint '{joint_name}'"
                )

    return RobotModel(
        name=name,
        description=description,
        type=robot_type,
        joints=joints,
        chains=chains,
        groups=groups,
    )


def _parse_joint(name: str, config: dict) -> Joint:
    """Parse joint configuration."""

    # Joint type (default: revolute)
    type_str = config.get("type", "revolute")
    try:
        joint_type = JointType(type_str)
    except ValueError:
        valid = [t.value for t in JointType]
        raise ValueError(f"Invalid joint type '{type_str}'. Valid: {valid}")

    # Actuator type (required)
    actuator_str = config.get("actuator")
    if not actuator_str:
        raise ValueError("Missing required field: 'actuator'")
    try:
        actuator_type = ActuatorType(actuator_str)
    except ValueError:
        valid = [a.value for a in ActuatorType]
        raise ValueError(f"Invalid actuator type '{actuator_str}'. Valid: {valid}")

    # Actuator ID (required)
    actuator_id = config.get("actuator_id")
    if actuator_id is None:
        raise ValueError("Missing required field: 'actuator_id'")

    # Validate max_velocity if provided
    max_velocity = config.get("max_velocity")
    if max_velocity is not None:
        try:
            max_velocity = float(max_velocity)
            if max_velocity <= 0:
                raise ValueError(f"max_velocity must be positive, got {max_velocity}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid max_velocity: {e}")

    return Joint(
        name=name,
        type=joint_type,
        actuator=actuator_type,
        actuator_id=int(actuator_id),
        pin=config.get("pin"),
        min_angle=float(config.get("min_angle", 0)),
        max_angle=float(config.get("max_angle", 180)),
        home=float(config.get("home", 90)),
        max_velocity=max_velocity,
        zero_position=config.get("zero_position", ""),
        max_position=config.get("max_position", ""),
        parent=config.get("parent"),
    )


def validate_robot_model(model: RobotModel) -> list[str]:
    """
    Validate robot model for potential issues.

    Returns list of warning messages (empty if valid).
    """
    warnings = []

    # Check for circular parent references
    for joint in model.joints.values():
        visited = set()
        current = joint
        while current.parent:
            if current.parent in visited:
                warnings.append(
                    f"Circular parent reference detected at joint '{current.name}'"
                )
                break
            visited.add(current.name)
            if current.parent not in model.joints:
                break
            current = model.joints[current.parent]

    # Check for duplicate actuator IDs within same type
    by_actuator: dict[ActuatorType, dict[int, list[str]]] = {}
    for joint in model.joints.values():
        if joint.actuator not in by_actuator:
            by_actuator[joint.actuator] = {}
        if joint.actuator_id not in by_actuator[joint.actuator]:
            by_actuator[joint.actuator][joint.actuator_id] = []
        by_actuator[joint.actuator][joint.actuator_id].append(joint.name)

    for actuator_type, id_map in by_actuator.items():
        for actuator_id, joint_names in id_map.items():
            if len(joint_names) > 1:
                warnings.append(
                    f"Multiple joints share {actuator_type.value} ID {actuator_id}: "
                    f"{joint_names}"
                )

    # Check for home position outside limits
    for joint in model.joints.values():
        if not (joint.min_angle <= joint.home <= joint.max_angle):
            warnings.append(
                f"Joint '{joint.name}' home position {joint.home}° "
                f"is outside limits [{joint.min_angle}°, {joint.max_angle}°]"
            )

    return warnings
