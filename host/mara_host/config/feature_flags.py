# mara_host/config/feature_flags.py
# Central feature flag definitions - mirrors ESP32 include/config/FeatureFlags.h
# These flags can be overridden via environment variables or runtime configuration

import os
from dataclasses import dataclass
from typing import Optional


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
        flags = FeatureFlags(has_wifi=True, has_dc_motor=True)  # Manual config
    """

    # ==========================================================================
    # TRANSPORT FLAGS
    # ==========================================================================
    has_wifi: bool = False
    has_ble: bool = False
    has_uart_transport: bool = True  # Default: always have UART
    has_mqtt_transport: bool = False
    has_tcp_transport: bool = False

    # ==========================================================================
    # MOTOR FLAGS
    # ==========================================================================
    has_dc_motor: bool = False
    has_servo: bool = False
    has_stepper: bool = False
    has_encoder: bool = False
    has_dc_velocity_pid: bool = False
    has_motion_controller: bool = False

    # ==========================================================================
    # SENSOR FLAGS
    # ==========================================================================
    has_imu: bool = False
    has_lidar: bool = False
    has_ultrasonic: bool = False
    has_limit_switch: bool = False
    has_camera: bool = False

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
    has_dsp_chain: bool = False
    has_mic: bool = False

    # ==========================================================================
    # SYSTEM FLAGS
    # ==========================================================================
    has_telemetry: bool = True
    has_heartbeat: bool = True
    has_logging: bool = True
    has_identity: bool = False
    has_binary_commands: bool = True
    has_safety_manager: bool = True

    # ==========================================================================
    # ML/VISION FLAGS (Python Host specific)
    # ==========================================================================
    has_object_detection: bool = False
    has_yolo: bool = False

    def __post_init__(self):
        """Validate dependencies between flags."""
        # MQTT requires WiFi
        if self.has_mqtt_transport and not self.has_wifi:
            raise ValueError("has_mqtt_transport requires has_wifi=True")

        # DC velocity PID requires DC motor and encoder
        if self.has_dc_velocity_pid and not (self.has_dc_motor and self.has_encoder):
            raise ValueError("has_dc_velocity_pid requires has_dc_motor=True and has_encoder=True")

        # Control kernel requires signal bus
        if self.has_control_kernel and not self.has_signal_bus:
            raise ValueError("has_control_kernel requires has_signal_bus=True")

        # Observer requires signal bus
        if self.has_observer and not self.has_signal_bus:
            raise ValueError("has_observer requires has_signal_bus=True")

        # Control module requires control kernel
        if self.has_control_module and not self.has_control_kernel:
            raise ValueError("has_control_module requires has_control_kernel=True")

    @classmethod
    def from_env(cls) -> "FeatureFlags":
        """Load feature flags from environment variables."""
        return cls(
            # Transport
            has_wifi=_env_bool("HAS_WIFI", False),
            has_ble=_env_bool("HAS_BLE", False),
            has_uart_transport=_env_bool("HAS_UART_TRANSPORT", True),
            has_mqtt_transport=_env_bool("HAS_MQTT_TRANSPORT", False),
            has_tcp_transport=_env_bool("HAS_TCP_TRANSPORT", False),
            # Motor
            has_dc_motor=_env_bool("HAS_DC_MOTOR", False),
            has_servo=_env_bool("HAS_SERVO", False),
            has_stepper=_env_bool("HAS_STEPPER", False),
            has_encoder=_env_bool("HAS_ENCODER", False),
            has_dc_velocity_pid=_env_bool("HAS_DC_VELOCITY_PID", False),
            has_motion_controller=_env_bool("HAS_MOTION_CONTROLLER", False),
            # Sensor
            has_imu=_env_bool("HAS_IMU", False),
            has_lidar=_env_bool("HAS_LIDAR", False),
            has_ultrasonic=_env_bool("HAS_ULTRASONIC", False),
            has_limit_switch=_env_bool("HAS_LIMIT_SWITCH", False),
            has_camera=_env_bool("HAS_CAMERA", False),
            # Control
            has_signal_bus=_env_bool("HAS_SIGNAL_BUS", False),
            has_control_kernel=_env_bool("HAS_CONTROL_KERNEL", False),
            has_observer=_env_bool("HAS_OBSERVER", False),
            has_pid_controller=_env_bool("HAS_PID_CONTROLLER", False),
            has_state_space=_env_bool("HAS_STATE_SPACE", False),
            has_control_module=_env_bool("HAS_CONTROL_MODULE", False),
            # Audio
            has_audio=_env_bool("HAS_AUDIO", False),
            has_dsp_chain=_env_bool("HAS_DSP_CHAIN", False),
            has_mic=_env_bool("HAS_MIC", False),
            # System
            has_telemetry=_env_bool("HAS_TELEMETRY", True),
            has_heartbeat=_env_bool("HAS_HEARTBEAT", True),
            has_logging=_env_bool("HAS_LOGGING", True),
            has_identity=_env_bool("HAS_IDENTITY", False),
            has_binary_commands=_env_bool("HAS_BINARY_COMMANDS", True),
            has_safety_manager=_env_bool("HAS_SAFETY_MANAGER", True),
            # ML/Vision
            has_object_detection=_env_bool("HAS_OBJECT_DETECTION", False),
            has_yolo=_env_bool("HAS_YOLO", False),
        )

    @classmethod
    def minimal(cls) -> "FeatureFlags":
        """Minimal configuration: UART only."""
        return cls(
            has_uart_transport=True,
            has_telemetry=True,
            has_heartbeat=True,
            has_logging=True,
        )

    @classmethod
    def motors(cls) -> "FeatureFlags":
        """Motor-focused configuration."""
        return cls(
            has_uart_transport=True,
            has_dc_motor=True,
            has_servo=True,
            has_stepper=True,
            has_encoder=True,
            has_motion_controller=True,
            has_telemetry=True,
            has_heartbeat=True,
            has_logging=True,
        )

    @classmethod
    def sensors(cls) -> "FeatureFlags":
        """Sensor-focused configuration."""
        return cls(
            has_wifi=True,
            has_tcp_transport=True,
            has_uart_transport=True,
            has_imu=True,
            has_ultrasonic=True,
            has_encoder=True,
            has_camera=True,
            has_telemetry=True,
            has_heartbeat=True,
            has_logging=True,
        )

    @classmethod
    def control(cls) -> "FeatureFlags":
        """Control system configuration."""
        return cls(
            has_uart_transport=True,
            has_dc_motor=True,
            has_encoder=True,
            has_dc_velocity_pid=True,
            has_motion_controller=True,
            has_signal_bus=True,
            has_control_kernel=True,
            has_observer=True,
            has_pid_controller=True,
            has_telemetry=True,
            has_heartbeat=True,
            has_logging=True,
        )

    @classmethod
    def full(cls) -> "FeatureFlags":
        """Full configuration: everything enabled."""
        return cls(
            # Transport
            has_wifi=True,
            has_ble=True,
            has_uart_transport=True,
            has_tcp_transport=True,
            # Motor
            has_dc_motor=True,
            has_servo=True,
            has_stepper=True,
            has_encoder=True,
            has_dc_velocity_pid=True,
            has_motion_controller=True,
            # Sensor
            has_imu=True,
            has_ultrasonic=True,
            has_camera=True,
            # Control
            has_signal_bus=True,
            has_control_kernel=True,
            has_observer=True,
            has_pid_controller=True,
            # System
            has_telemetry=True,
            has_heartbeat=True,
            has_logging=True,
            has_identity=True,
            has_binary_commands=True,
            has_safety_manager=True,
            # ML
            has_object_detection=True,
            has_yolo=True,
        )

    # ==========================================================================
    # DERIVED FLAGS (convenience properties)
    # ==========================================================================
    @property
    def has_any_motor(self) -> bool:
        return self.has_dc_motor or self.has_servo or self.has_stepper

    @property
    def has_any_sensor(self) -> bool:
        return self.has_imu or self.has_lidar or self.has_ultrasonic or self.has_encoder or self.has_camera

    @property
    def has_any_transport(self) -> bool:
        return self.has_wifi or self.has_ble or self.has_uart_transport or self.has_tcp_transport

    @property
    def has_any_control(self) -> bool:
        return self.has_control_kernel or self.has_observer or self.has_signal_bus

    def summary(self) -> str:
        """Return a summary of enabled features."""
        lines = [
            "=== Feature Flags ===",
            f"Transport: WIFI={int(self.has_wifi)} BLE={int(self.has_ble)} UART={int(self.has_uart_transport)} TCP={int(self.has_tcp_transport)}",
            f"Motor: DC={int(self.has_dc_motor)} SERVO={int(self.has_servo)} STEPPER={int(self.has_stepper)} ENCODER={int(self.has_encoder)} MOTION={int(self.has_motion_controller)}",
            f"Sensor: IMU={int(self.has_imu)} LIDAR={int(self.has_lidar)} ULTRASONIC={int(self.has_ultrasonic)} CAMERA={int(self.has_camera)}",
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
