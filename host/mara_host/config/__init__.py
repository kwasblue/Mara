# mara_host/config/__init__.py
"""
Configuration module for mara_host.

Main classes:
    RobotConfig - First-class configuration object for robot setup
    ConfigValidationError - Raised when config fails schema validation
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
    PersistenceConfig,
    PersistencePolicy,
)
from .robot_config_schema import (
    ConfigValidationError,
    ROBOT_CONFIG_SCHEMA,
    validate_config_with_context,
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
    "PersistenceConfig",
    "PersistencePolicy",
    "ConfigValidationError",
    "ROBOT_CONFIG_SCHEMA",
    "validate_config_with_context",
]
