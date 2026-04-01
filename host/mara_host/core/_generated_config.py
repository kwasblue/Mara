"""
_generated_config.py
=============================================================================
AUTO-GENERATED FILE - DO NOT EDIT
=============================================================================
Generated from: config/mara_build.yaml
Generated at:   2026-04-01T16:03:26.224110
Active profile: full

To regenerate, run:
  python -m mara_host.tools.generate_all
"""

from typing import Dict, Any

# =============================================================================
# Transport Settings
# =============================================================================
DEFAULT_BAUD_RATE: int = 921600
DEFAULT_TCP_PORT: int = 3333
DEFAULT_DEVICE_NAME: str = "ESP32-bot"

# =============================================================================
# Active Build Profile
# =============================================================================
BUILD_PROFILE: str = "full"

# =============================================================================
# Feature Flags
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


def has_feature(name: str) -> bool:
    """Check if a feature is enabled in the active build profile."""
    return FEATURES.get(name, False)


def get_enabled_features() -> list[str]:
    """Get list of all enabled features."""
    return [name for name, enabled in FEATURES.items() if enabled]
