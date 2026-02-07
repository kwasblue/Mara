# robot_host/research/config_loader.py
"""
Robot configuration loader.

Load robot configurations from YAML files and instantiate simulation objects.

Example:
    robot = load_robot("configs/my_robot.yaml")
    robot.set_velocity(0.5, 0.1)
    state = robot.step(0.01)
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

import yaml

from .simulation import (
    DCMotor,
    DCMotorConfig,
    DelayConfig,
    DelaySimulator,
    DiffDriveConfig,
    DiffDriveRobot,
    EncoderNoiseModel,
    GaussianNoise,
    IMUNoiseModel,
    SimulationRunner,
    UltrasonicNoiseModel,
)
from .sysid import DCMotorParams, DifferentialDriveParams


T = TypeVar("T")


# =============================================================================
# Configuration Loading
# =============================================================================

def load_yaml(path: Union[str, Path]) -> Dict[str, Any]:
    """Load a YAML configuration file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_json(path: Union[str, Path]) -> Dict[str, Any]:
    """Load a JSON configuration file."""
    with open(path, "r") as f:
        return json.load(f)


def load_config(path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file."""
    path = Path(path)
    if path.suffix in (".yaml", ".yml"):
        return load_yaml(path)
    elif path.suffix == ".json":
        return load_json(path)
    else:
        # Try YAML first, then JSON
        try:
            return load_yaml(path)
        except Exception:
            return load_json(path)


def save_yaml(data: Dict[str, Any], path: Union[str, Path]):
    """Save configuration to YAML file."""
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def save_json(data: Dict[str, Any], path: Union[str, Path], indent: int = 2):
    """Save configuration to JSON file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=indent)


# =============================================================================
# Dataclass Helpers
# =============================================================================

def dict_to_dataclass(cls: Type[T], data: Dict[str, Any]) -> T:
    """
    Convert a dictionary to a dataclass, handling nested dataclasses.
    """
    if data is None:
        return cls()

    field_types = {f.name: f.type for f in fields(cls)}
    kwargs = {}

    for key, value in data.items():
        if key not in field_types:
            continue

        field_type = field_types[key]

        # Handle nested dataclasses
        if isinstance(value, dict):
            # Check if field type is a dataclass
            if hasattr(field_type, "__dataclass_fields__"):
                value = dict_to_dataclass(field_type, value)

        kwargs[key] = value

    return cls(**kwargs)


def dataclass_to_dict(obj) -> Dict[str, Any]:
    """Convert a dataclass to a dictionary."""
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    return obj


# =============================================================================
# Robot Configuration
# =============================================================================

def load_motor_config(data: Dict[str, Any]) -> DCMotorConfig:
    """Load DC motor configuration from dictionary."""
    return dict_to_dataclass(DCMotorConfig, data)


def load_noise_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """Load noise model configurations."""
    result = {}

    if "imu" in data:
        imu_data = data["imu"]
        result["imu"] = IMUNoiseModel(
            accel_noise=GaussianNoise(
                mean=imu_data.get("accel_mean", 0),
                std=imu_data.get("accel_std", 0.01),
            ),
            gyro_noise=GaussianNoise(
                mean=imu_data.get("gyro_mean", 0),
                std=imu_data.get("gyro_std", 0.001),
            ),
            gyro_drift_rate=imu_data.get("gyro_drift_rate", 1e-5),
        )

    if "encoder" in data:
        enc_data = data["encoder"]
        result["encoder"] = EncoderNoiseModel(
            counts_per_rev=enc_data.get("counts_per_rev", 1000),
            missed_count_prob=enc_data.get("missed_count_prob", 0.0),
        )

    if "ultrasonic" in data:
        us_data = data["ultrasonic"]
        result["ultrasonic"] = UltrasonicNoiseModel(
            noise=GaussianNoise(std=us_data.get("noise_std", 0.02)),
            min_range=us_data.get("min_range", 0.02),
            max_range=us_data.get("max_range", 4.0),
            multipath_prob=us_data.get("multipath_prob", 0.01),
        )

    return result


def load_diff_drive_config(data: Dict[str, Any]) -> DiffDriveConfig:
    """Load differential drive configuration from dictionary."""
    motor_data = data.get("motor", {})
    motor_config = load_motor_config(motor_data)

    return DiffDriveConfig(
        wheel_radius=data.get("wheel_radius", 0.05),
        wheel_base=data.get("wheel_base", 0.2),
        robot_mass=data.get("robot_mass", 2.0),
        wheel_inertia=data.get("wheel_inertia", 0.001),
        motor_config=motor_config,
        max_linear_vel=data.get("max_linear_vel", 1.0),
        max_angular_vel=data.get("max_angular_vel", 3.0),
        max_linear_accel=data.get("max_linear_accel", 2.0),
        max_angular_accel=data.get("max_angular_accel", 6.0),
    )


def load_delay_config(data: Dict[str, Any]) -> Optional[DelayConfig]:
    """Load communication delay configuration."""
    if not data:
        return None

    return DelayConfig(
        mean_delay_ms=data.get("mean_delay_ms", 5.0),
        std_delay_ms=data.get("std_delay_ms", 2.0),
        jitter_ms=data.get("jitter_ms", 1.0),
        packet_loss_prob=data.get("packet_loss_prob", 0.0),
        max_delay_ms=data.get("max_delay_ms", 100.0),
    )


# =============================================================================
# Robot Factory
# =============================================================================

class SimulationConfig:
    """
    Complete simulation robot configuration loaded from file.

    This is for simulation/research use. For real robot configuration,
    use robot_host.config.RobotConfig instead.

    Attributes:
        name: Robot name
        description: Robot description
        type: Robot type (e.g., "diff_drive")
        drive_config: Drive configuration
        noise_config: Noise model configuration
        delay_config: Communication delay configuration
        metadata: Additional metadata
    """

    def __init__(self, config_path: Union[str, Path]):
        self.path = Path(config_path)
        self.data = load_config(config_path)

        self.name = self.data.get("name", self.path.stem)
        self.description = self.data.get("description", "")
        self.type = self.data.get("type", "diff_drive")
        self.metadata = self.data.get("metadata", {})

        # Load sub-configurations
        self.drive_config = load_diff_drive_config(self.data.get("drive", {}))
        self.noise_models = load_noise_config(self.data.get("noise", {}))
        self.delay_config = load_delay_config(self.data.get("delay", {}))
        self.simulation = self.data.get("simulation", {})

    def create_robot(self) -> DiffDriveRobot:
        """Create a robot instance from this configuration."""
        return DiffDriveRobot(
            config=self.drive_config,
            imu_noise=self.noise_models.get("imu"),
            encoder_noise=self.noise_models.get("encoder"),
        )

    def create_simulation_runner(self, controller=None) -> SimulationRunner:
        """Create a simulation runner with this robot configuration."""
        robot = self.create_robot()
        dt = self.simulation.get("dt", 0.01)

        return SimulationRunner(
            robot=robot,
            controller=controller,
            dt=dt,
            delay_config=self.delay_config,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return self.data

    def save(self, path: Union[str, Path]):
        """Save configuration to file."""
        path = Path(path)
        if path.suffix == ".json":
            save_json(self.data, path)
        else:
            save_yaml(self.data, path)


def load_robot(config_path: Union[str, Path]) -> DiffDriveRobot:
    """
    Load a robot from a configuration file.

    Args:
        config_path: Path to YAML or JSON configuration file

    Returns:
        Configured DiffDriveRobot instance

    Example:
        robot = load_robot("configs/my_robot.yaml")
        robot.set_velocity(0.5, 0.1)
        state = robot.step(0.01)
    """
    config = SimulationConfig(config_path)
    return config.create_robot()


def load_simulation(
    config_path: Union[str, Path],
    controller=None,
) -> SimulationRunner:
    """
    Load a complete simulation from configuration file.

    Args:
        config_path: Path to configuration file
        controller: Optional controller function(state) -> (vx, omega)

    Returns:
        Configured SimulationRunner
    """
    config = SimulationConfig(config_path)
    return config.create_simulation_runner(controller)


# =============================================================================
# Config Templates
# =============================================================================

def create_default_config(name: str = "my_robot") -> Dict[str, Any]:
    """Create a default robot configuration template."""
    return {
        "name": name,
        "description": "A differential drive robot",
        "type": "diff_drive",
        "drive": {
            "wheel_radius": 0.05,
            "wheel_base": 0.2,
            "robot_mass": 2.0,
            "wheel_inertia": 0.001,
            "max_linear_vel": 1.0,
            "max_angular_vel": 3.0,
            "max_linear_accel": 2.0,
            "max_angular_accel": 6.0,
            "motor": {
                "R": 2.0,
                "L": 0.001,
                "Kv": 0.01,
                "Kt": 0.01,
                "J": 0.001,
                "b": 0.0001,
                "Kf": 0.0,
                "max_voltage": 12.0,
                "max_current": 10.0,
                "max_velocity": 100.0,
            },
        },
        "noise": {
            "imu": {
                "accel_std": 0.01,
                "gyro_std": 0.001,
                "gyro_drift_rate": 1e-5,
            },
            "encoder": {
                "counts_per_rev": 1000,
                "missed_count_prob": 0.0,
            },
            "ultrasonic": {
                "noise_std": 0.02,
                "min_range": 0.02,
                "max_range": 4.0,
                "multipath_prob": 0.01,
            },
        },
        "delay": {
            "mean_delay_ms": 5.0,
            "std_delay_ms": 2.0,
            "jitter_ms": 1.0,
            "packet_loss_prob": 0.0,
        },
        "simulation": {
            "dt": 0.01,
        },
        "metadata": {
            "author": "",
            "version": "1.0",
            "created": "",
        },
    }


def generate_config_template(output_path: Union[str, Path]):
    """Generate a template configuration file."""
    config = create_default_config()
    output_path = Path(output_path)

    if output_path.suffix == ".json":
        save_json(config, output_path)
    else:
        save_yaml(config, output_path)

    return config


# =============================================================================
# Config Discovery
# =============================================================================

def find_configs(
    directory: Union[str, Path] = ".",
    recursive: bool = True,
) -> list[Path]:
    """
    Find all robot configuration files in a directory.

    Args:
        directory: Directory to search
        recursive: Search subdirectories

    Returns:
        List of config file paths
    """
    directory = Path(directory)
    patterns = ["*.yaml", "*.yml", "*.json"]

    configs = []
    for pattern in patterns:
        if recursive:
            configs.extend(directory.rglob(pattern))
        else:
            configs.extend(directory.glob(pattern))

    # Filter to only robot configs (check for 'type' key)
    robot_configs = []
    for path in configs:
        try:
            data = load_config(path)
            if "type" in data or "drive" in data:
                robot_configs.append(path)
        except Exception:
            continue

    return robot_configs


def list_available_robots(config_dir: Union[str, Path] = None) -> Dict[str, Path]:
    """
    List all available robot configurations.

    Returns:
        Dictionary mapping robot names to config file paths
    """
    if config_dir is None:
        # Default to package configs directory
        config_dir = Path(__file__).parent / "configs"

    if not config_dir.exists():
        return {}

    configs = find_configs(config_dir, recursive=False)

    return {
        load_config(p).get("name", p.stem): p
        for p in configs
    }
