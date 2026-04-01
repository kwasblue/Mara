# mara_host/config/feature_flags.py
"""
Feature flags for runtime configuration.

This module provides runtime feature flag validation and dependency checking.
Profile definitions are loaded from the generated config (sourced from mara_build.yaml).

DO NOT hardcode profiles here - they come from config/mara_build.yaml via generation.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

# Import from generated config - single source of truth
from mara_host.core._generated_config import (
    PROFILES,
    FEATURE_DEPENDENCIES,
    validate_dependencies,
)


def _env_bool(key: str, default: bool) -> bool:
    """Read a boolean from environment variable."""
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


@dataclass
class FeatureFlags:
    """
    Feature flags for configuring mara_host capabilities.
    Mirrors the ESP32 FeatureFlags.h for consistency.

    Usage:
        flags = FeatureFlags.from_env()  # Load from environment
        flags = FeatureFlags.from_profile("motors")  # Load from profile
        flags = FeatureFlags(has_wifi=True, has_dc_motor=True)  # Manual config
    """

    # ==========================================================================
    # TRANSPORT FLAGS
    # ==========================================================================
    has_wifi: bool = False
    has_ble: bool = False
    has_uart_transport: bool = True  # Default: always have UART
    has_mqtt_transport: bool = False

    # ==========================================================================
    # MOTOR FLAGS
    # ==========================================================================
    has_dc_motor: bool = False
    has_servo: bool = False
    has_stepper: bool = False
    has_encoder: bool = False
    has_motion_controller: bool = False

    # ==========================================================================
    # SENSOR FLAGS
    # ==========================================================================
    has_imu: bool = False
    has_lidar: bool = False
    has_ultrasonic: bool = False

    # ==========================================================================
    # CONTROL FLAGS
    # ==========================================================================
    has_signal_bus: bool = False
    has_control_kernel: bool = False
    has_observer: bool = False
    has_pid_controller: bool = False
    has_state_space: bool = False
    has_control_module: bool = False

    # ==========================================================================
    # AUDIO FLAGS
    # ==========================================================================
    has_audio: bool = False

    # ==========================================================================
    # SYSTEM FLAGS
    # ==========================================================================
    has_ota: bool = False
    has_telemetry: bool = True
    has_heartbeat: bool = True
    has_logging: bool = True
    has_identity: bool = False
    has_benchmark: bool = False

    def __post_init__(self):
        """Validate dependencies between flags."""
        # Convert to dict for validation
        features = self.to_dict()
        errors = validate_dependencies(features)
        if errors:
            raise ValueError("; ".join(errors))

    def to_dict(self) -> dict[str, bool]:
        """Convert to feature dict (without has_ prefix)."""
        return {
            "wifi": self.has_wifi,
            "ble": self.has_ble,
            "uart_transport": self.has_uart_transport,
            "mqtt_transport": self.has_mqtt_transport,
            "dc_motor": self.has_dc_motor,
            "servo": self.has_servo,
            "stepper": self.has_stepper,
            "encoder": self.has_encoder,
            "motion_controller": self.has_motion_controller,
            "imu": self.has_imu,
            "lidar": self.has_lidar,
            "ultrasonic": self.has_ultrasonic,
            "signal_bus": self.has_signal_bus,
            "control_kernel": self.has_control_kernel,
            "observer": self.has_observer,
            "pid_controller": self.has_pid_controller,
            "state_space": self.has_state_space,
            "control_module": self.has_control_module,
            "audio": self.has_audio,
            "ota": self.has_ota,
            "telemetry": self.has_telemetry,
            "heartbeat": self.has_heartbeat,
            "logging": self.has_logging,
            "identity": self.has_identity,
            "benchmark": self.has_benchmark,
        }

    @classmethod
    def from_dict(cls, features: dict[str, bool]) -> "FeatureFlags":
        """Create from feature dict."""
        return cls(
            has_wifi=features.get("wifi", False),
            has_ble=features.get("ble", False),
            has_uart_transport=features.get("uart_transport", True),
            has_mqtt_transport=features.get("mqtt_transport", False),
            has_dc_motor=features.get("dc_motor", False),
            has_servo=features.get("servo", False),
            has_stepper=features.get("stepper", False),
            has_encoder=features.get("encoder", False),
            has_motion_controller=features.get("motion_controller", False),
            has_imu=features.get("imu", False),
            has_lidar=features.get("lidar", False),
            has_ultrasonic=features.get("ultrasonic", False),
            has_signal_bus=features.get("signal_bus", False),
            has_control_kernel=features.get("control_kernel", False),
            has_observer=features.get("observer", False),
            has_pid_controller=features.get("pid_controller", False),
            has_state_space=features.get("state_space", False),
            has_control_module=features.get("control_module", False),
            has_audio=features.get("audio", False),
            has_ota=features.get("ota", False),
            has_telemetry=features.get("telemetry", True),
            has_heartbeat=features.get("heartbeat", True),
            has_logging=features.get("logging", True),
            has_identity=features.get("identity", False),
            has_benchmark=features.get("benchmark", False),
        )

    @classmethod
    def from_env(cls) -> "FeatureFlags":
        """Load feature flags from environment variables."""
        return cls(
            # Transport
            has_wifi=_env_bool("HAS_WIFI", False),
            has_ble=_env_bool("HAS_BLE", False),
            has_uart_transport=_env_bool("HAS_UART_TRANSPORT", True),
            has_mqtt_transport=_env_bool("HAS_MQTT_TRANSPORT", False),
            # Motor
            has_dc_motor=_env_bool("HAS_DC_MOTOR", False),
            has_servo=_env_bool("HAS_SERVO", False),
            has_stepper=_env_bool("HAS_STEPPER", False),
            has_encoder=_env_bool("HAS_ENCODER", False),
            has_motion_controller=_env_bool("HAS_MOTION_CONTROLLER", False),
            # Sensor
            has_imu=_env_bool("HAS_IMU", False),
            has_lidar=_env_bool("HAS_LIDAR", False),
            has_ultrasonic=_env_bool("HAS_ULTRASONIC", False),
            # Control
            has_signal_bus=_env_bool("HAS_SIGNAL_BUS", False),
            has_control_kernel=_env_bool("HAS_CONTROL_KERNEL", False),
            has_observer=_env_bool("HAS_OBSERVER", False),
            has_pid_controller=_env_bool("HAS_PID_CONTROLLER", False),
            has_state_space=_env_bool("HAS_STATE_SPACE", False),
            has_control_module=_env_bool("HAS_CONTROL_MODULE", False),
            # Audio
            has_audio=_env_bool("HAS_AUDIO", False),
            # System
            has_ota=_env_bool("HAS_OTA", False),
            has_telemetry=_env_bool("HAS_TELEMETRY", True),
            has_heartbeat=_env_bool("HAS_HEARTBEAT", True),
            has_logging=_env_bool("HAS_LOGGING", True),
            has_identity=_env_bool("HAS_IDENTITY", False),
            has_benchmark=_env_bool("HAS_BENCHMARK", False),
        )

    @classmethod
    def from_profile(cls, profile_name: str) -> "FeatureFlags":
        """Load feature flags from a profile defined in mara_build.yaml.

        Args:
            profile_name: One of: minimal, motors, sensors, control, full
        """
        if profile_name not in PROFILES:
            available = ", ".join(PROFILES.keys())
            raise ValueError(f"Unknown profile '{profile_name}'. Available: {available}")

        return cls.from_dict(PROFILES[profile_name])

    # Profile factory methods - delegate to from_profile for single source of truth
    @classmethod
    def minimal(cls) -> "FeatureFlags":
        """Minimal configuration from mara_build.yaml."""
        return cls.from_profile("minimal")

    @classmethod
    def motors(cls) -> "FeatureFlags":
        """Motor-focused configuration from mara_build.yaml."""
        return cls.from_profile("motors")

    @classmethod
    def sensors(cls) -> "FeatureFlags":
        """Sensor-focused configuration from mara_build.yaml."""
        return cls.from_profile("sensors")

    @classmethod
    def control(cls) -> "FeatureFlags":
        """Control system configuration from mara_build.yaml."""
        return cls.from_profile("control")

    @classmethod
    def full(cls) -> "FeatureFlags":
        """Full configuration from mara_build.yaml."""
        return cls.from_profile("full")

    # ==========================================================================
    # DERIVED FLAGS (convenience properties)
    # ==========================================================================
    @property
    def has_any_motor(self) -> bool:
        return self.has_dc_motor or self.has_servo or self.has_stepper

    @property
    def has_any_sensor(self) -> bool:
        return self.has_imu or self.has_lidar or self.has_ultrasonic or self.has_encoder

    @property
    def has_any_transport(self) -> bool:
        return self.has_wifi or self.has_ble or self.has_uart_transport

    @property
    def has_any_control(self) -> bool:
        return self.has_control_kernel or self.has_observer or self.has_signal_bus

    def summary(self) -> str:
        """Return a summary of enabled features."""
        lines = [
            "=== Feature Flags ===",
            f"Transport: WIFI={int(self.has_wifi)} BLE={int(self.has_ble)} UART={int(self.has_uart_transport)}",
            f"Motor: DC={int(self.has_dc_motor)} SERVO={int(self.has_servo)} STEPPER={int(self.has_stepper)} ENCODER={int(self.has_encoder)} MOTION={int(self.has_motion_controller)}",
            f"Sensor: IMU={int(self.has_imu)} LIDAR={int(self.has_lidar)} ULTRASONIC={int(self.has_ultrasonic)}",
            f"Control: SIGNAL_BUS={int(self.has_signal_bus)} KERNEL={int(self.has_control_kernel)} OBSERVER={int(self.has_observer)}",
            f"System: TELEM={int(self.has_telemetry)} HEARTBEAT={int(self.has_heartbeat)} LOG={int(self.has_logging)}",
        ]
        return "\n".join(lines)


# Default global instance - can be overridden at runtime
_default_flags: Optional[FeatureFlags] = None


def get_flags() -> FeatureFlags:
    """Get the global feature flags instance."""
    global _default_flags
    if _default_flags is None:
        _default_flags = FeatureFlags.from_env()
    return _default_flags


def set_flags(flags: FeatureFlags) -> None:
    """Set the global feature flags instance."""
    global _default_flags
    _default_flags = flags
