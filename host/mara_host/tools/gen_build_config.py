#!/usr/bin/env python3
"""
Generate build configuration from mara_build.yaml.

This generator creates:
  - firmware/mcu/include/config/GeneratedBuildConfig.h (C++ defines)
  - host/mara_host/core/_generated_config.py (Python constants)

Usage:
    python gen_build_config.py
"""

from pathlib import Path
from datetime import datetime
from typing import Any, Dict

import yaml


# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "mara_build.yaml"
FIRMWARE_OUT = REPO_ROOT / "firmware" / "mcu" / "include" / "config" / "GeneratedBuildConfig.h"
HOST_OUT = REPO_ROOT / "host" / "mara_host" / "core" / "_generated_config.py"


def load_config() -> Dict[str, Any]:
    """Load the mara_build.yaml config file."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def feature_to_define(name: str) -> str:
    """Convert feature name to C++ define name."""
    # e.g., "wifi" -> "HAS_WIFI", "dc_motor" -> "HAS_DC_MOTOR"
    return f"HAS_{name.upper()}"


def generate_cpp_header(config: Dict[str, Any]) -> str:
    """Generate the C++ header file content."""
    transport = config.get("transport", {})
    profiles = config.get("profiles", {})
    active_profile = config.get("active_profile", "full")

    # Get the active profile's features
    features = profiles.get(active_profile, {})

    lines = [
        "// GeneratedBuildConfig.h",
        "// =============================================================================",
        "// AUTO-GENERATED FILE - DO NOT EDIT",
        "// =============================================================================",
        f"// Generated from: config/mara_build.yaml",
        f"// Generated at:   {datetime.now().isoformat()}",
        f"// Active profile: {active_profile}",
        "//",
        "// To regenerate, run:",
        "//   python -m mara_host.tools.generate_all",
        "// =============================================================================",
        "",
        "#pragma once",
        "",
        "// =============================================================================",
        "// Transport Settings",
        "// =============================================================================",
        f"#define MARA_BAUD_RATE {transport.get('baud_rate', 921600)}",
        f"#define MARA_TCP_PORT {transport.get('tcp_port', 3333)}",
        f"#define MARA_DEVICE_NAME \"{transport.get('device_name', 'ESP32-bot')}\"",
        "",
        "// =============================================================================",
        f"// Feature Flags (profile: {active_profile})",
        "// =============================================================================",
    ]

    # Group features by category
    categories = {
        "Transport": ["wifi", "ble", "uart_transport", "mqtt_transport"],
        "Motors": ["servo", "stepper", "dc_motor", "encoder", "motion_controller"],
        "Sensors": ["ultrasonic", "imu", "lidar"],
        "Control": ["signal_bus", "control_kernel", "pid_controller", "state_space", "observer", "control_module"],
        "System": ["ota", "telemetry", "heartbeat", "logging", "identity"],
        "Audio": ["audio"],
        "Debug": ["benchmark"],
    }

    for category, feature_names in categories.items():
        lines.append(f"// {category}")
        for name in feature_names:
            if name in features:
                value = 1 if features[name] else 0
                define_name = feature_to_define(name)
                lines.append(f"#define {define_name} {value}")
        lines.append("")

    # Add profile name as a string define
    lines.append("// Active profile name")
    lines.append(f"#define MARA_BUILD_PROFILE \"{active_profile}\"")
    lines.append("")

    return "\n".join(lines)


def generate_python_module(config: Dict[str, Any]) -> str:
    """Generate the Python module content."""
    transport = config.get("transport", {})
    profiles = config.get("profiles", {})
    active_profile = config.get("active_profile", "full")

    # Get the active profile's features
    features = profiles.get(active_profile, {})

    lines = [
        '"""',
        "_generated_config.py",
        "=============================================================================",
        "AUTO-GENERATED FILE - DO NOT EDIT",
        "=============================================================================",
        f"Generated from: config/mara_build.yaml",
        f"Generated at:   {datetime.now().isoformat()}",
        f"Active profile: {active_profile}",
        "",
        "To regenerate, run:",
        "  python -m mara_host.tools.generate_all",
        '"""',
        "",
        "from typing import Dict, Any",
        "",
        "# =============================================================================",
        "# Transport Settings",
        "# =============================================================================",
        f"DEFAULT_BAUD_RATE: int = {transport.get('baud_rate', 921600)}",
        f"DEFAULT_TCP_PORT: int = {transport.get('tcp_port', 3333)}",
        f"DEFAULT_DEVICE_NAME: str = \"{transport.get('device_name', 'ESP32-bot')}\"",
        "",
        "# =============================================================================",
        "# Active Build Profile",
        "# =============================================================================",
        f"BUILD_PROFILE: str = \"{active_profile}\"",
        "",
        "# =============================================================================",
        "# Feature Flags",
        "# =============================================================================",
        "FEATURES: Dict[str, bool] = {",
    ]

    # Add all features
    for name, enabled in sorted(features.items()):
        lines.append(f"    \"{name}\": {enabled},")

    lines.append("}")
    lines.append("")

    # Add convenience functions
    lines.extend([
        "",
        "def has_feature(name: str) -> bool:",
        '    """Check if a feature is enabled in the active build profile."""',
        "    return FEATURES.get(name, False)",
        "",
        "",
        "def get_enabled_features() -> list[str]:",
        '    """Get list of all enabled features."""',
        "    return [name for name, enabled in FEATURES.items() if enabled]",
        "",
    ])

    return "\n".join(lines)


def main():
    """Generate build config files."""
    print("Generating build configuration...")
    print(f"  Config: {CONFIG_PATH}")

    # Load config
    config = load_config()
    active_profile = config.get("active_profile", "full")
    print(f"  Active profile: {active_profile}")

    # Generate C++ header
    cpp_content = generate_cpp_header(config)
    FIRMWARE_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(FIRMWARE_OUT, "w") as f:
        f.write(cpp_content)
    print(f"  Generated: {FIRMWARE_OUT}")

    # Generate Python module
    py_content = generate_python_module(config)
    HOST_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(HOST_OUT, "w") as f:
        f.write(py_content)
    print(f"  Generated: {HOST_OUT}")

    # Print summary
    transport = config.get("transport", {})
    print(f"  Baud rate: {transport.get('baud_rate', 921600)}")

    profiles = config.get("profiles", {})
    features = profiles.get(active_profile, {})
    enabled = [k for k, v in features.items() if v]
    print(f"  Enabled features ({len(enabled)}): {', '.join(enabled[:5])}...")

    print("Build config generation complete!")


if __name__ == "__main__":
    main()
