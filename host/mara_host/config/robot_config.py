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
from typing import Any, Dict, Iterator, List, Optional, Union

import yaml

from .robot_config_schema import (
    ROBOT_CONFIG_SCHEMA,
    ConfigValidationError,
    validate_config_with_context,
)


@dataclass
class ValidationReport:
    """Detailed validation output for robot configuration."""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


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
class SensorDegradationConfig:
    """How the system should behave when a sensor is absent or unhealthy."""
    required: bool = False
    allow_missing: bool = True
    stale_after_ms: Optional[int] = None
    fail_open: bool = True
    fallback: str = "none"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SensorDegradationConfig":
        return cls(
            required=bool(data.get("required", False)),
            allow_missing=bool(data.get("allow_missing", True)),
            stale_after_ms=data.get("stale_after_ms"),
            fail_open=bool(data.get("fail_open", True)),
            fallback=str(data.get("fallback", "none")),
        )


@dataclass
class SensorConfig:
    """Incremental sensor interface abstraction for Python-first usage."""
    name: str
    kind: str
    enabled: bool = True
    sensor_id: int = 0
    transport: str = "telemetry"
    topic: Optional[str] = None
    pins: Dict[str, int] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    degradation: SensorDegradationConfig = field(default_factory=SensorDegradationConfig)

    @classmethod
    def from_entry(cls, name: str, data: Any) -> "SensorConfig":
        if not isinstance(data, dict):
            data = {"value": data}
        kind = str(data.get("kind") or data.get("type") or name)
        pins = {
            str(k): v for k, v in data.items()
            if isinstance(v, int) and (str(k).lower().endswith("pin") or str(k).lower().endswith("_pin"))
        }
        topic = data.get("topic")
        if topic is None and data.get("transport", "telemetry") == "telemetry":
            topic = f"telemetry.{name}"
        config = {k: v for k, v in data.items() if k not in {"kind", "type", "enabled", "sensor_id", "transport", "topic", "degradation"}}
        return cls(
            name=name,
            kind=kind,
            enabled=bool(data.get("enabled", True)),
            sensor_id=int(data.get("sensor_id", 0)),
            transport=str(data.get("transport", "telemetry")),
            topic=str(topic) if topic is not None else None,
            pins=pins,
            config=config,
            degradation=SensorDegradationConfig.from_dict(data.get("degradation", {})),
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
    sensors: Dict[str, SensorConfig] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    # --- Class Methods ---

    @classmethod
    def load(
        cls,
        path: Union[str, Path],
        profile: Optional[str] = None,
        validate: bool = True,
    ) -> "RobotConfig":
        """
        Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file
            profile: Optional profile name to apply (e.g., "bench", "field", "sim")
                     Looks for profiles/<profile>.yaml relative to config file
            validate: Whether to perform JSON schema validation (default True)

        Returns:
            RobotConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is malformed
            ConfigValidationError: If config fails schema validation
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

        # Validate against JSON schema
        if validate:
            errors = validate_config_with_context(data)
            if errors:
                error_list = "\n  ".join(errors)
                raise ConfigValidationError(
                    f"Config validation failed for {path}:\n  {error_list}",
                    errors=errors,
                )

        return cls._from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], validate: bool = True) -> "RobotConfig":
        """
        Create config from dictionary.

        Args:
            data: Configuration dictionary
            validate: Whether to perform JSON schema validation (default True)

        Returns:
            RobotConfig instance

        Raises:
            ConfigValidationError: If config fails schema validation
        """
        if validate:
            errors = validate_config_with_context(data)
            if errors:
                error_list = "\n  ".join(errors)
                raise ConfigValidationError(
                    f"Config validation failed:\n  {error_list}",
                    errors=errors,
                )
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "RobotConfig":
        """Internal: create config from dictionary."""
        transport_data = data.get("transport", {})
        drive_data = data.get("drive")
        features_data = data.get("features", {})
        encoder_data = data.get("encoder_defaults", {})
        settings_data = data.get("settings", {})
        sensors_data = data.get("sensors", {})

        return cls(
            name=data.get("name", "robot"),
            transport=TransportConfig.from_dict(transport_data),
            drive=DriveConfig.from_dict(drive_data) if drive_data else None,
            features=FeaturesConfig.from_dict(features_data),
            encoder_defaults=EncoderDefaults.from_dict(encoder_data),
            settings=SettingsConfig.from_dict(settings_data),
            sensors={name: SensorConfig.from_entry(name, entry) for name, entry in sensors_data.items()},
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

    def validate_report(self) -> ValidationReport:
        """Validate configuration and return structured errors and warnings."""
        report = ValidationReport()

        # Transport validation
        if self.transport.type == "serial":
            if not self.transport.port:
                report.errors.append("transport.port is required for serial connection")
        elif self.transport.type == "tcp":
            if not self.transport.host:
                report.errors.append("transport.host is required for TCP connection")
            if self.transport.tcp_port <= 0 or self.transport.tcp_port > 65535:
                report.errors.append("transport.tcp_port must be between 1 and 65535")
        elif self.transport.type == "ble":
            if not self.transport.ble_name:
                report.errors.append("transport.ble_name is required for BLE connection")
        elif self.transport.type not in ("serial", "tcp", "ble"):
            report.errors.append(
                f"transport.type must be 'serial', 'tcp', or 'ble', got '{self.transport.type}'"
            )

        if self.transport.baudrate <= 0:
            report.errors.append("transport.baudrate must be positive")

        # Drive validation
        if self.drive:
            if self.drive.wheel_radius <= 0:
                report.errors.append("drive.wheel_radius must be positive")
            if self.drive.wheel_base <= 0:
                report.errors.append("drive.wheel_base must be positive")
            if self.drive.max_linear_vel <= 0:
                report.errors.append("drive.max_linear_vel must be positive")
            if self.drive.max_angular_vel <= 0:
                report.errors.append("drive.max_angular_vel must be positive")

        # Settings validation
        if self.settings.telemetry_interval_ms < 10:
            report.errors.append("settings.telemetry_interval_ms should be >= 10ms")
        if self.settings.control_rate_hz <= 0:
            report.errors.append("settings.control_rate_hz must be positive")
        if self.settings.pwm_freq_hz <= 0:
            report.errors.append("settings.pwm_freq_hz must be positive")

        # Feature coherence
        if self.features.motion and not self.drive:
            report.warnings.append("features.motion is enabled but no drive config is defined")
        if self.features.encoder and self.encoder_defaults.counts_per_rev is not None and self.encoder_defaults.counts_per_rev <= 0:
            report.errors.append("encoder_defaults.counts_per_rev must be positive when provided")

        # Best-effort boot-pin checks for host-managed component configs
        for path, pin in self._iter_config_pins(self.raw):
            if pin in {0, 2, 12, 15}:
                report.warnings.append(f"{path} uses boot-sensitive GPIO {pin}")
            if pin in {34, 35, 36, 39} and self._pin_path_is_outputish(path):
                report.errors.append(f"{path} uses input-only GPIO {pin} for an output-like field")

        # Sensor abstraction + graceful degradation checks
        for sensor in self.sensors.values():
            if sensor.transport not in {"telemetry", "command", "service"}:
                report.errors.append(f"sensors.{sensor.name}.transport must be telemetry, command, or service")
            if sensor.degradation.stale_after_ms is not None and sensor.degradation.stale_after_ms <= 0:
                report.errors.append(f"sensors.{sensor.name}.degradation.stale_after_ms must be positive")
            if sensor.degradation.required and sensor.degradation.allow_missing:
                report.warnings.append(
                    f"sensors.{sensor.name} is marked required but also allow_missing=true; treating it as degradable"
                )
            if sensor.enabled and sensor.transport == "telemetry" and not sensor.topic:
                report.errors.append(f"sensors.{sensor.name}.topic is required for telemetry-backed sensors")
            if sensor.enabled and not sensor.pins and sensor.kind in {"ultrasonic", "encoder", "gpio", "analog"}:
                report.warnings.append(f"sensors.{sensor.name} has no explicit pins; assuming firmware-managed defaults")
            if not sensor.enabled and sensor.degradation.required:
                report.warnings.append(f"sensors.{sensor.name} is disabled but marked required")

        return report

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
        return self.validate_report().errors

    @staticmethod
    def _pin_path_is_outputish(path: str) -> bool:
        lowered = path.lower()
        return any(token in lowered for token in ("pwm", "tx", "enable", "step", "dir", "trig", "relay", "motor", "servo", "led", "out"))

    @classmethod
    def _iter_config_pins(cls, value: Any, path: str = ""):
        if isinstance(value, dict):
            for key, item in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                lowered = str(key).lower()
                if lowered.endswith("pin") or lowered.endswith("_pin"):
                    if isinstance(item, int):
                        yield child_path, item
                    elif isinstance(item, list):
                        for idx, entry in enumerate(item):
                            if isinstance(entry, int):
                                yield f"{child_path}[{idx}]", entry
                yield from cls._iter_config_pins(item, child_path)
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                yield from cls._iter_config_pins(item, f"{path}[{idx}]")

    def iter_sensors(self, enabled_only: bool = True) -> Iterator[SensorConfig]:
        """Iterate configured sensors in a stable order."""
        for name in sorted(self.sensors):
            sensor = self.sensors[name]
            if enabled_only and not sensor.enabled:
                continue
            yield sensor

    def get_sensor(self, name: str) -> Optional[SensorConfig]:
        """Get a configured sensor by name."""
        return self.sensors.get(name)

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
            robot = Robot(
                port=self.transport.port,
                baudrate=self.transport.baudrate,
            )
        elif self.transport.type == "tcp":
            robot = Robot(
                host=self.transport.host,
                tcp_port=self.transport.tcp_port,
            )
        elif self.transport.type == "ble":
            robot = Robot(
                ble_name=self.transport.ble_name,
                baudrate=self.transport.baudrate,
            )
        else:
            raise ValueError(f"Unsupported transport type: {self.transport.type}")

        robot._config = self
        return robot

    def __repr__(self) -> str:
        return f"RobotConfig(name={self.name!r}, transport={self.transport.type})"
