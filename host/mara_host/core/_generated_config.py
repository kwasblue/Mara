"""
_generated_config.py
=============================================================================
AUTO-GENERATED FILE - DO NOT EDIT
=============================================================================
Generated from: config/mara_build.yaml
Generated at:   2026-04-04T09:20:06.935212
Active profile: full

To regenerate, run:
  mara generate all

This is the SINGLE SOURCE OF TRUTH for all build configuration.
Import from here, do not hardcode values elsewhere.
"""

from typing import Dict, List, Any

# =============================================================================
# Transport Settings
# =============================================================================
DEFAULT_BAUD_RATE: int = 921600
DEFAULT_UPLOAD_BAUD_RATE: int = 460800
DEFAULT_TCP_PORT: int = 3333
DEFAULT_DEVICE_NAME: str = "ESP32-bot"

# Aliases for backwards compatibility
DEFAULT_BAUDRATE = DEFAULT_BAUD_RATE

# =============================================================================
# Active Build Profile
# =============================================================================
BUILD_PROFILE: str = "full"

# =============================================================================
# Feature Flags (active profile)
# =============================================================================
FEATURES: Dict[str, bool] = {
    "audio": False,
    "benchmark": True,
    "ble": True,
    "control_kernel": True,
    "control_module": True,
    "dc_motor": True,
    "encoder": True,
    "heartbeat": True,
    "identity": True,
    "imu": True,
    "lidar": True,
    "logging": True,
    "motion_controller": True,
    "mqtt_transport": True,
    "observer": True,
    "ota": True,
    "pid_controller": True,
    "servo": True,
    "signal_bus": True,
    "state_space": True,
    "stepper": True,
    "telemetry": True,
    "uart_transport": True,
    "ultrasonic": True,
    "wifi": True,
}

# =============================================================================
# All Profiles
# =============================================================================
PROFILES: Dict[str, Dict[str, bool]] = {
    "minimal": {
        "audio": False,
        "benchmark": False,
        "ble": False,
        "control_kernel": False,
        "control_module": False,
        "dc_motor": False,
        "encoder": False,
        "heartbeat": True,
        "identity": False,
        "imu": False,
        "lidar": False,
        "logging": False,
        "motion_controller": False,
        "mqtt_transport": False,
        "observer": False,
        "ota": False,
        "pid_controller": False,
        "servo": False,
        "signal_bus": False,
        "state_space": False,
        "stepper": False,
        "telemetry": True,
        "uart_transport": True,
        "ultrasonic": False,
        "wifi": False,
    },
    "motors": {
        "audio": False,
        "benchmark": False,
        "ble": False,
        "control_kernel": False,
        "control_module": False,
        "dc_motor": True,
        "encoder": True,
        "heartbeat": True,
        "identity": False,
        "imu": False,
        "lidar": False,
        "logging": True,
        "motion_controller": True,
        "mqtt_transport": False,
        "observer": False,
        "ota": False,
        "pid_controller": False,
        "servo": True,
        "signal_bus": False,
        "state_space": False,
        "stepper": True,
        "telemetry": True,
        "uart_transport": True,
        "ultrasonic": False,
        "wifi": False,
    },
    "sensors": {
        "audio": False,
        "benchmark": False,
        "ble": False,
        "control_kernel": False,
        "control_module": False,
        "dc_motor": False,
        "encoder": False,
        "heartbeat": True,
        "identity": True,
        "imu": True,
        "lidar": True,
        "logging": True,
        "motion_controller": False,
        "mqtt_transport": False,
        "observer": False,
        "ota": True,
        "pid_controller": False,
        "servo": False,
        "signal_bus": False,
        "state_space": False,
        "stepper": False,
        "telemetry": True,
        "uart_transport": True,
        "ultrasonic": True,
        "wifi": True,
    },
    "control": {
        "audio": False,
        "benchmark": True,
        "ble": False,
        "control_kernel": True,
        "control_module": True,
        "dc_motor": True,
        "encoder": True,
        "heartbeat": True,
        "identity": True,
        "imu": True,
        "lidar": False,
        "logging": True,
        "motion_controller": True,
        "mqtt_transport": False,
        "observer": True,
        "ota": True,
        "pid_controller": True,
        "servo": True,
        "signal_bus": True,
        "state_space": True,
        "stepper": True,
        "telemetry": True,
        "uart_transport": True,
        "ultrasonic": False,
        "wifi": True,
    },
    "full": {
        "audio": False,
        "benchmark": True,
        "ble": True,
        "control_kernel": True,
        "control_module": True,
        "dc_motor": True,
        "encoder": True,
        "heartbeat": True,
        "identity": True,
        "imu": True,
        "lidar": True,
        "logging": True,
        "motion_controller": True,
        "mqtt_transport": True,
        "observer": True,
        "ota": True,
        "pid_controller": True,
        "servo": True,
        "signal_bus": True,
        "state_space": True,
        "stepper": True,
        "telemetry": True,
        "uart_transport": True,
        "ultrasonic": True,
        "wifi": True,
    },
}

# =============================================================================
# Feature Categories
# =============================================================================
FEATURE_CATEGORIES: Dict[str, List[str]] = {
    "Transport": ['wifi', 'ble', 'uart_transport', 'mqtt_transport'],
    "Motors": ['servo', 'stepper', 'dc_motor', 'encoder', 'motion_controller'],
    "Sensors": ['ultrasonic', 'imu', 'lidar'],
    "Control": ['signal_bus', 'control_kernel', 'pid_controller', 'state_space', 'observer', 'control_module'],
    "System": ['ota', 'telemetry', 'heartbeat', 'logging', 'identity'],
    "Audio": ['audio'],
    "Debug": ['benchmark'],
}

# =============================================================================
# Feature Dependencies
# =============================================================================
FEATURE_DEPENDENCIES: Dict[str, List[str]] = {
    "mqtt_transport": ['wifi'],
    "control_kernel": ['signal_bus'],
    "observer": ['signal_bus'],
    "control_module": ['control_kernel'],
    "state_space": ['control_kernel'],
}

# =============================================================================
# Resource Limits
# =============================================================================
LIMITS: Dict[str, int] = {
    "max_control_slots": 8,
    "max_graph_slots": 8,
    "max_inputs": 2,
    "max_observers": 4,
    "max_outputs": 4,
    "max_signals": 128,
    "max_states": 6,
}


# =============================================================================
# Convenience Functions
# =============================================================================

def has_feature(name: str) -> bool:
    """Check if a feature is enabled in the active build profile."""
    return FEATURES.get(name, False)


def get_enabled_features() -> List[str]:
    """Get list of all enabled features."""
    return [name for name, enabled in FEATURES.items() if enabled]


def get_profile(name: str) -> Dict[str, bool]:
    """Get a profile by name."""
    if name not in PROFILES:
        raise KeyError(f"Unknown profile '{name}'. Available: {list(PROFILES.keys())}")
    return PROFILES[name]


def get_profile_names() -> List[str]:
    """Get list of available profile names."""
    return list(PROFILES.keys())


def validate_dependencies(features: Dict[str, bool]) -> List[str]:
    """Validate feature dependencies.

    Args:
        features: Dict mapping feature name to enabled state

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    for feature, required in FEATURE_DEPENDENCIES.items():
        if features.get(feature, False):
            for req in required:
                if not features.get(req, False):
                    errors.append(f"{feature} requires {req}")
    return errors


def get_limit(name: str) -> int:
    """Get a specific resource limit."""
    return LIMITS.get(name, 0)
