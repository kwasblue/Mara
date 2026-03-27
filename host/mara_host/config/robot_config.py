# mara_host/config/robot_config.py
"""
First-class configuration object for robot setup.

Example:
    from mara_host.config import RobotConfig

    # Load and validate
    config = RobotConfig.load("robots/my_robot.yaml")
    errors = config.validate()
    if errors:
        print(f"Config errors: {errors}")
        sys.exit(1)

    # Create robot
    async with config.create_robot() as robot:
        await robot.arm()

    # Load with profile override
    config = RobotConfig.load("robots/my_robot.yaml", profile="bench")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


@dataclass
class TransportConfig:
    """Transport layer configuration."""
    type: str = "serial"
    # Serial
    port: Optional[str] = None
    baudrate: int = 115200
    # TCP
    host: Optional[str] = None
    tcp_port: int = 3333
    # BLE
    ble_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransportConfig":
        transport_type = data.get("type", "serial")
        return cls(
            type=transport_type,
            port=data.get("port"),
            baudrate=data.get("baudrate", 115200),
            host=data.get("host"),
            tcp_port=data.get("port", 3333) if transport_type == "tcp" else data.get("tcp_port", 3333),
            ble_name=data.get("ble_name") or (data.get("port") if transport_type == "ble" else None),
        )


@dataclass
class DriveConfig:
    """Differential drive configuration."""
    type: str = "differential"
    wheel_radius: float = 0.05
    wheel_base: float = 0.2
    max_linear_vel: float = 1.0
    max_angular_vel: float = 3.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DriveConfig":
        return cls(
            type=data.get("type", "differential"),
            wheel_radius=data.get("wheel_radius", 0.05),
            wheel_base=data.get("wheel_base", 0.2),
            max_linear_vel=data.get("max_linear_vel", 1.0),
            max_angular_vel=data.get("max_angular_vel", 3.0),
        )


@dataclass
class FeaturesConfig:
    """Feature flags for optional modules."""
    telemetry: bool = True
    encoder: bool = False
    motion: bool = False
    modes: bool = False
    camera: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeaturesConfig":
        return cls(
            telemetry=data.get("telemetry", True),
            encoder=data.get("encoder", False),
            motion=data.get("motion", False),
            modes=data.get("modes", False),
            camera=data.get("camera", False),
        )


@dataclass
class EncoderDefaults:
    """Default encoder configuration."""
    encoder_id: int = 0
    pin_a: int = 32
    pin_b: int = 33
    counts_per_rev: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncoderDefaults":
        return cls(
            encoder_id=data.get("encoder_id", 0),
            pin_a=data.get("pin_a", 32),
            pin_b=data.get("pin_b", 33),
            counts_per_rev=data.get("counts_per_rev"),
        )


@dataclass
class SettingsConfig:
    """Runtime settings."""
    telemetry_interval_ms: int = 100
    pwm_freq_hz: float = 1000.0
    control_rate_hz: float = 50.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SettingsConfig":
        return cls(
            telemetry_interval_ms=data.get("telemetry_interval_ms", 100),
            pwm_freq_hz=data.get("pwm_freq_hz", 1000.0),
            control_rate_hz=data.get("control_rate_hz", 50.0),
        )


@dataclass
class RobotConfig:
    """
    First-class configuration object for robot setup.

    Provides:
    - YAML loading with profile support
    - Schema validation with clear error messages
    - Profile merging (base + profile overrides)
    - Robot instance creation

    Example:
        config = RobotConfig.load("robots/my_robot.yaml")
        errors = config.validate()
        if not errors:
            robot = await config.create_robot()
    """

    name: str = "robot"
    transport: TransportConfig = field(default_factory=TransportConfig)
    drive: Optional[DriveConfig] = None
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    encoder_defaults: EncoderDefaults = field(default_factory=EncoderDefaults)
    settings: SettingsConfig = field(default_factory=SettingsConfig)
    components: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    # --- Class Methods ---

    @classmethod
    def load(
        cls,
        path: Union[str, Path],
        profile: Optional[str] = None,
    ) -> "RobotConfig":
        """
        Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file
            profile: Optional profile name to apply (e.g., "bench", "field", "sim")
                     Looks for profiles/<profile>.yaml relative to config file

        Returns:
            RobotConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is malformed
        """
        path = Path(path)
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        # Apply profile overrides if specified
        if profile:
            profile_path = path.parent / "profiles" / f"{profile}.yaml"
            if profile_path.exists():
                with open(profile_path, "r") as f:
                    profile_data = yaml.safe_load(f) or {}
                data = cls._merge_dicts(data, profile_data)

        return cls._from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RobotConfig":
        """Create config from dictionary."""
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "RobotConfig":
        """Internal: create config from dictionary."""
        transport_data = data.get("transport", {})
        drive_data = data.get("drive")
        features_data = data.get("features", {})
        encoder_data = data.get("encoder_defaults", {})
        settings_data = data.get("settings", {})

        return cls(
            name=data.get("name", "robot"),
            transport=TransportConfig.from_dict(transport_data),
            drive=DriveConfig.from_dict(drive_data) if drive_data else None,
            features=FeaturesConfig.from_dict(features_data),
            encoder_defaults=EncoderDefaults.from_dict(encoder_data),
            settings=SettingsConfig.from_dict(settings_data),
            components=data.get("components", {}),
            raw=data,
        )

    @classmethod
    def _merge_dicts(cls, base: Dict, overlay: Dict) -> Dict:
        """Deep merge two dictionaries, overlay wins on conflicts."""
        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._merge_dicts(result[key], value)
            else:
                result[key] = value
        return result

    # --- Instance Methods ---

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.

        Returns:
            List of error messages (empty if valid)

        Example:
            errors = config.validate()
            if errors:
                for err in errors:
                    print(f"  - {err}")
                sys.exit(1)
        """
        errors = []

        # Transport validation
        if self.transport.type == "serial":
            if not self.transport.port:
                errors.append("transport.port is required for serial connection")
        elif self.transport.type == "tcp":
            if not self.transport.host:
                errors.append("transport.host is required for TCP connection")
        elif self.transport.type == "ble":
            if not self.transport.ble_name:
                errors.append("transport.ble_name is required for BLE connection")
        elif self.transport.type not in ("serial", "tcp", "ble"):
            errors.append(f"transport.type must be 'serial', 'tcp', or 'ble', got '{self.transport.type}'")

        # Drive validation
        if self.drive:
            if self.drive.wheel_radius <= 0:
                errors.append("drive.wheel_radius must be positive")
            if self.drive.wheel_base <= 0:
                errors.append("drive.wheel_base must be positive")
            if self.drive.max_linear_vel <= 0:
                errors.append("drive.max_linear_vel must be positive")
            if self.drive.max_angular_vel <= 0:
                errors.append("drive.max_angular_vel must be positive")

        # Settings validation
        if self.settings.telemetry_interval_ms < 10:
            errors.append("settings.telemetry_interval_ms should be >= 10ms")
        if self.settings.control_rate_hz <= 0:
            errors.append("settings.control_rate_hz must be positive")

        return errors

    def create_robot(self) -> "Robot":
        """
        Create a Robot instance from this configuration.

        Returns:
            Robot instance (not yet connected)

        Example:
            config = RobotConfig.load("my_robot.yaml")
            async with config.create_robot() as robot:
                await robot.arm()
        """
        from ..robot import Robot

        if self.transport.type == "serial":
            return Robot(
                port=self.transport.port,
                baudrate=self.transport.baudrate,
            )
        elif self.transport.type == "tcp":
            return Robot(
                host=self.transport.host,
                tcp_port=self.transport.tcp_port,
            )
        elif self.transport.type == "ble":
            return Robot(
                ble_name=self.transport.ble_name,
                baudrate=self.transport.baudrate,
            )
        else:
            raise ValueError(f"Unsupported transport type: {self.transport.type}")

    def __repr__(self) -> str:
        return f"RobotConfig(name={self.name!r}, transport={self.transport.type})"
