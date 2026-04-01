# mara_host/core/build_profiles.py
"""
Build profile configuration - Single source of truth.

Loads ALL configuration from config/mara_build.yaml and provides it to:
- gen_build_config.py (code generation)
- build_firmware.py (compile-time flags)
- CLI commands (--profile option)
- feature_flags.py (runtime validation)
- All transport defaults

This ensures configuration is defined in ONE place (YAML) and used everywhere.
"""

from pathlib import Path
from typing import Any

import yaml


# Path to the config file
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = _REPO_ROOT / "config" / "mara_build.yaml"

# Cached config
_config: dict[str, Any] | None = None


def _load_config() -> dict[str, Any]:
    """Load and cache the mara_build.yaml config."""
    global _config
    if _config is None:
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"Build config not found: {CONFIG_PATH}")
        with open(CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def get_config() -> dict[str, Any]:
    """Get the full config dict."""
    return _load_config()


# =============================================================================
# Transport Settings
# =============================================================================

def get_transport_settings() -> dict[str, Any]:
    """Get transport settings (baud_rate, tcp_port, device_name, etc.)."""
    return _load_config().get("transport", {})


def get_baud_rate() -> int:
    """Get runtime serial baud rate."""
    return get_transport_settings().get("baud_rate", 921600)


def get_upload_baud_rate() -> int:
    """Get firmware upload/flashing baud rate."""
    return get_transport_settings().get("upload_baud_rate", 460800)


def get_tcp_port() -> int:
    """Get default TCP port."""
    return get_transport_settings().get("tcp_port", 3333)


def get_device_name() -> str:
    """Get default device name."""
    return get_transport_settings().get("device_name", "ESP32-bot")


# =============================================================================
# Feature Categories
# =============================================================================

def get_feature_categories() -> dict[str, list[str]]:
    """Get feature categories for display and organization."""
    return _load_config().get("categories", {})


def get_all_feature_names() -> list[str]:
    """Get all known feature names from categories."""
    features = []
    for category_features in get_feature_categories().values():
        features.extend(category_features)
    return features


# =============================================================================
# Feature Dependencies
# =============================================================================

def get_feature_dependencies() -> dict[str, list[str]]:
    """Get feature dependency rules.

    Returns:
        Dict mapping feature -> list of required features
    """
    return _load_config().get("dependencies", {})


def validate_feature_dependencies(features: dict[str, bool]) -> list[str]:
    """Validate feature dependencies.

    Args:
        features: Dict mapping feature name to enabled state

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    dependencies = get_feature_dependencies()

    for feature, required in dependencies.items():
        if features.get(feature, False):
            for req in required:
                if not features.get(req, False):
                    errors.append(f"{feature} requires {req}")

    return errors


# =============================================================================
# Profiles
# =============================================================================

def get_active_profile() -> str:
    """Get the active profile name."""
    return _load_config().get("active_profile", "full")


def get_profile_names() -> list[str]:
    """Get list of available profile names."""
    return list(_load_config().get("profiles", {}).keys())


def get_profile(name: str) -> dict[str, bool]:
    """Get a specific profile's feature flags.

    Args:
        name: Profile name (minimal, motors, sensors, control, full)

    Returns:
        Dict mapping feature names to enabled state

    Raises:
        KeyError: If profile doesn't exist
    """
    profiles = _load_config().get("profiles", {})
    if name not in profiles:
        available = ", ".join(profiles.keys())
        raise KeyError(f"Unknown profile '{name}'. Available: {available}")
    return profiles[name]


def get_all_profiles() -> dict[str, dict[str, bool]]:
    """Get all profiles."""
    return _load_config().get("profiles", {})


def get_active_profile_features() -> dict[str, bool]:
    """Get the active profile's feature flags."""
    return get_profile(get_active_profile())


# =============================================================================
# Feature to Macro Mapping
# =============================================================================

# Maps YAML feature names to C++ preprocessor defines
FEATURE_TO_MACRO: dict[str, str] = {
    # Transport
    "wifi": "HAS_WIFI",
    "ble": "HAS_BLE",
    "uart_transport": "HAS_UART_TRANSPORT",
    "mqtt_transport": "HAS_MQTT_TRANSPORT",
    # Motors
    "servo": "HAS_SERVO",
    "stepper": "HAS_STEPPER",
    "dc_motor": "HAS_DC_MOTOR",
    "encoder": "HAS_ENCODER",
    "motion_controller": "HAS_MOTION_CONTROLLER",
    # Sensors
    "ultrasonic": "HAS_ULTRASONIC",
    "imu": "HAS_IMU",
    "lidar": "HAS_LIDAR",
    # Control
    "signal_bus": "HAS_SIGNAL_BUS",
    "control_kernel": "HAS_CONTROL_KERNEL",
    "pid_controller": "HAS_PID_CONTROLLER",
    "state_space": "HAS_STATE_SPACE",
    "observer": "HAS_OBSERVER",
    "control_module": "HAS_CONTROL_MODULE",
    # System
    "ota": "HAS_OTA",
    "telemetry": "HAS_TELEMETRY",
    "heartbeat": "HAS_HEARTBEAT",
    "logging": "HAS_LOGGING",
    "identity": "HAS_IDENTITY",
    # Audio
    "audio": "HAS_AUDIO",
    # Debug
    "benchmark": "HAS_BENCHMARK",
}

# Short aliases for CLI convenience (maps alias -> canonical name)
FEATURE_ALIASES: dict[str, str] = {
    "uart": "uart_transport",
    "mqtt": "mqtt_transport",
    "motion": "motion_controller",
    "pid": "pid_controller",
}


def feature_to_macro(name: str) -> str:
    """Convert feature name to C++ macro name.

    Args:
        name: Feature name (e.g., "wifi", "dc_motor")

    Returns:
        Macro name (e.g., "HAS_WIFI", "HAS_DC_MOTOR")
    """
    # Resolve alias if needed
    canonical = FEATURE_ALIASES.get(name, name)
    if canonical in FEATURE_TO_MACRO:
        return FEATURE_TO_MACRO[canonical]
    # Fallback: generate macro name
    return f"HAS_{canonical.upper()}"


def profile_to_build_flags(profile_name: str) -> dict[str, bool]:
    """Convert a profile to build flags (macro -> enabled).

    Args:
        profile_name: Profile name

    Returns:
        Dict mapping macro names to enabled state
    """
    profile = get_profile(profile_name)
    result = {}
    for feature, enabled in profile.items():
        macro = feature_to_macro(feature)
        result[macro] = enabled
    return result


# =============================================================================
# CLI Parsing
# =============================================================================

def parse_features(
    features_str: str | None,
    no_features_str: str | None = None,
) -> dict[str, bool] | None:
    """Parse feature flags from comma-separated strings.

    Args:
        features_str: Comma-separated features or preset name
        no_features_str: Comma-separated features to disable

    Returns:
        Dict of {macro: enabled} or None if no features specified
    """
    if not features_str and not no_features_str:
        return None

    # Start with all features disabled
    result = {macro: False for macro in FEATURE_TO_MACRO.values()}

    if features_str:
        for feat in features_str.split(","):
            feat = feat.strip().lower()
            if not feat:
                continue

            # Check if it's a profile/preset name
            if feat in get_profile_names():
                flags = profile_to_build_flags(feat)
                result.update(flags)
            # Check if it's a known feature
            elif feat in FEATURE_TO_MACRO:
                result[FEATURE_TO_MACRO[feat]] = True
            # Check if it's an alias
            elif feat in FEATURE_ALIASES:
                canonical = FEATURE_ALIASES[feat]
                result[FEATURE_TO_MACRO[canonical]] = True
            else:
                print(f"[build] Warning: Unknown feature '{feat}'")
                print(f"[build] Available features: {', '.join(sorted(FEATURE_TO_MACRO.keys()))}")
                print(f"[build] Available profiles: {', '.join(get_profile_names())}")

    # Explicitly disable features
    if no_features_str:
        for feat in no_features_str.split(","):
            feat = feat.strip().lower()
            canonical = FEATURE_ALIASES.get(feat, feat)
            if canonical in FEATURE_TO_MACRO:
                result[FEATURE_TO_MACRO[canonical]] = False

    return result


def features_to_build_flags(features: dict[str, bool] | None) -> list[str]:
    """Convert feature dict to compiler flags.

    Args:
        features: Dict of {macro: enabled}

    Returns:
        List of -D flags (e.g., ["-DHAS_WIFI=1", "-DHAS_BLE=0"])
    """
    if features is None:
        return []

    return [f"-D{macro}={int(enabled)}" for macro, enabled in features.items()]


def reload_config() -> None:
    """Force reload of config from disk."""
    global _config
    _config = None
