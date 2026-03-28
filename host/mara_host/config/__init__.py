# mara_host/config/__init__.py
"""
Configuration module for mara_host.

Main classes:
    RobotConfig - First-class configuration object for robot setup
"""

from .robot_config import (
    RobotConfig,
    TransportConfig,
    DriveConfig,
    FeaturesConfig,
    EncoderDefaults,
    SettingsConfig,
    SensorConfig,
    SensorDegradationConfig,
)

__all__ = [
    "RobotConfig",
    "TransportConfig",
    "DriveConfig",
    "FeaturesConfig",
    "EncoderDefaults",
    "SettingsConfig",
    "SensorConfig",
    "SensorDegradationConfig",
]
