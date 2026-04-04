#!/usr/bin/env python3
"""
Generate build configuration from mara_build.yaml.

This generator creates:
  - firmware/mcu/include/config/GeneratedBuildConfig.h (C++ defines)
  - host/mara_host/core/_generated_config.py (Python constants)

Uses mara_host.core.build_profiles as the single source of truth.

Usage:
    python gen_build_config.py
"""

from pathlib import Path
from datetime import datetime

from mara_host.core.build_profiles import (
    get_config,
    get_transport_settings,
    get_active_profile,
    get_profile,
    get_all_profiles,
    get_feature_categories,
    get_feature_dependencies,
    get_limits,
    feature_to_macro,
    LIMIT_TO_MACRO,
    CONFIG_PATH,
    # Platform settings
    get_platform_settings,
    get_platform_target,
    platform_to_macro,
    PLATFORM_TO_MACRO,
    VALID_TARGETS,
    VALID_SDKS,
)


# Output paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FIRMWARE_OUT = REPO_ROOT / "firmware" / "mcu" / "include" / "config" / "GeneratedBuildConfig.h"
FIRMWARE_LIMITS_OUT = REPO_ROOT / "firmware" / "mcu" / "include" / "config" / "GeneratedLimits.h"
HOST_OUT = REPO_ROOT / "host" / "mara_host" / "core" / "_generated_config.py"


def generate_cpp_header(profile_name: str | None = None) -> str:
    """Generate the C++ header file content.

    Args:
        profile_name: Profile to use (default: active_profile from config)
    """
    transport = get_transport_settings()
    platform = get_platform_settings()
    categories = get_feature_categories()
    active_profile = profile_name or get_active_profile()
    features = get_profile(active_profile)

    # Get platform target and macro
    target = platform.get("target", "esp32")
    target_macro = platform_to_macro(target)

    lines = [
        "// GeneratedBuildConfig.h",
        "// =============================================================================",
        "// AUTO-GENERATED FILE - DO NOT EDIT",
        "// =============================================================================",
        f"// Generated from: config/mara_build.yaml",
        f"// Generated at:   {datetime.now().isoformat()}",
        f"// Active profile: {active_profile}",
        f"// Target platform: {target}",
        "//",
        "// To regenerate, run:",
        "//   mara generate all",
        "//",
        "// Note: PLATFORM_* and HAS_* macros use #ifndef guards to allow",
        "// command-line overrides (e.g., -DPLATFORM_NATIVE=1 for unit tests).",
        "// =============================================================================",
        "",
        "#pragma once",
        "",
        "// =============================================================================",
        "// Target Platform",
        "// =============================================================================",
        "// Only one PLATFORM_* should be 1, all others should be 0.",
        "// This controls HAL selection via hal/PlatformHal.h",
        "//",
        "// For native/unit test builds, PLATFORM_NATIVE should be set via build flags",
        "// which take precedence over these generated defaults.",
    ]

    # Generate platform defines with guards (allow command-line override)
    for platform_name, macro in PLATFORM_TO_MACRO.items():
        value = 1 if platform_name == target else 0
        lines.append(f"#ifndef {macro}")
        lines.append(f"#define {macro} {value}")
        lines.append("#endif")

    # Add platform metadata
    lines.extend([
        "",
        f"#define MARA_PLATFORM_TARGET \"{target}\"",
        f"#define MARA_PLATFORM_BOARD \"{platform.get('board', 'esp32dev')}\"",
        f"#define MARA_PLATFORM_SDK \"{platform.get('sdk', 'arduino')}\"",
        f"#define MARA_PLATFORM_VARIANT \"{platform.get('variant', '')}\"",
        "",
        "// =============================================================================",
        "// Transport Settings",
        "// =============================================================================",
        f"#define MARA_BAUD_RATE {transport.get('baud_rate', 921600)}",
        f"#define MARA_UPLOAD_BAUD_RATE {transport.get('upload_baud_rate', 460800)}",
        f"#define MARA_TCP_PORT {transport.get('tcp_port', 3333)}",
        f"#define MARA_DEVICE_NAME \"{transport.get('device_name', 'ESP32-bot')}\"",
        "",
        "// =============================================================================",
        f"// Feature Flags (profile: {active_profile})",
        "// =============================================================================",
    ])

    # Group features by category
    # These are the authoritative values from mara_build.yaml
    # Using #ifndef guards to allow command-line overrides for test builds
    for category, feature_names in categories.items():
        lines.append(f"// {category}")
        for name in feature_names:
            if name in features:
                value = 1 if features[name] else 0
                define_name = feature_to_macro(name)
                lines.append(f"#ifndef {define_name}")
                lines.append(f"#define {define_name} {value}")
                lines.append("#endif")
        lines.append("")

    # Add profile name as a string define
    lines.append("// Active profile name")
    lines.append(f"#define MARA_BUILD_PROFILE \"{active_profile}\"")
    lines.append("")

    # Add resource limits
    limits = get_limits()
    lines.append("// =============================================================================")
    lines.append("// Resource Limits")
    lines.append("// =============================================================================")
    for name, value in sorted(limits.items()):
        macro = LIMIT_TO_MACRO.get(name, f"MARA_{name.upper()}")
        lines.append(f"#define {macro} {value}")
    lines.append("")

    return "\n".join(lines)


def generate_limits_header() -> str:
    """Generate a separate header with only resource limits.

    This header is safe to include from any file without pulling in feature flags,
    which allows native tests to override feature flags via command-line while
    still using the configured limits.
    """
    limits = get_limits()

    lines = [
        "// GeneratedLimits.h",
        "// =============================================================================",
        "// AUTO-GENERATED FILE - DO NOT EDIT",
        "// =============================================================================",
        f"// Generated from: config/mara_build.yaml",
        f"// Generated at:   {datetime.now().isoformat()}",
        "//",
        "// Resource limits only - safe to include without affecting feature flags.",
        "// For feature flags, include GeneratedBuildConfig.h instead.",
        "//",
        "// To regenerate, run:",
        "//   mara generate all",
        "// =============================================================================",
        "",
        "#pragma once",
        "",
        "// =============================================================================",
        "// Resource Limits",
        "// =============================================================================",
    ]

    for name, value in sorted(limits.items()):
        macro = LIMIT_TO_MACRO.get(name, f"MARA_{name.upper()}")
        lines.append(f"#define {macro} {value}")

    lines.append("")
    return "\n".join(lines)


def generate_python_module(profile_name: str | None = None) -> str:
    """Generate the Python module content.

    Args:
        profile_name: Profile to use (default: active_profile from config)
    """
    transport = get_transport_settings()
    platform = get_platform_settings()
    categories = get_feature_categories()
    dependencies = get_feature_dependencies()
    all_profiles = get_all_profiles()
    active_profile = profile_name or get_active_profile()
    features = get_profile(active_profile)
    limits = get_limits()

    lines = [
        '"""',
        "_generated_config.py",
        "=============================================================================",
        "AUTO-GENERATED FILE - DO NOT EDIT",
        "=============================================================================",
        f"Generated from: config/mara_build.yaml",
        f"Generated at:   {datetime.now().isoformat()}",
        f"Active profile: {active_profile}",
        f"Target platform: {platform.get('target', 'esp32')}",
        "",
        "To regenerate, run:",
        "  mara generate all",
        "",
        "This is the SINGLE SOURCE OF TRUTH for all build configuration.",
        "Import from here, do not hardcode values elsewhere.",
        '"""',
        "",
        "from typing import Dict, List, Any",
        "",
        "# =============================================================================",
        "# Target Platform",
        "# =============================================================================",
        f"PLATFORM_TARGET: str = \"{platform.get('target', 'esp32')}\"",
        f"PLATFORM_BOARD: str = \"{platform.get('board', 'esp32dev')}\"",
        f"PLATFORM_SDK: str = \"{platform.get('sdk', 'arduino')}\"",
        f"PLATFORM_VARIANT: str = \"{platform.get('variant', '')}\"",
        "",
        f"VALID_TARGETS: List[str] = {list(VALID_TARGETS)}",
        f"VALID_SDKS: List[str] = {list(VALID_SDKS)}",
        "",
        "# =============================================================================",
        "# Transport Settings",
        "# =============================================================================",
        f"DEFAULT_BAUD_RATE: int = {transport.get('baud_rate', 921600)}",
        f"DEFAULT_UPLOAD_BAUD_RATE: int = {transport.get('upload_baud_rate', 460800)}",
        f"DEFAULT_TCP_PORT: int = {transport.get('tcp_port', 3333)}",
        f"DEFAULT_DEVICE_NAME: str = \"{transport.get('device_name', 'ESP32-bot')}\"",
        "",
        "# Aliases for backwards compatibility",
        "DEFAULT_BAUDRATE = DEFAULT_BAUD_RATE",
        "",
        "# =============================================================================",
        "# Active Build Profile",
        "# =============================================================================",
        f"BUILD_PROFILE: str = \"{active_profile}\"",
        "",
        "# =============================================================================",
        "# Feature Flags (active profile)",
        "# =============================================================================",
        "FEATURES: Dict[str, bool] = {",
    ]

    # Add features for active profile
    for name, enabled in sorted(features.items()):
        lines.append(f"    \"{name}\": {enabled},")
    lines.append("}")
    lines.append("")

    # Add all profiles
    lines.append("# =============================================================================")
    lines.append("# All Profiles")
    lines.append("# =============================================================================")
    lines.append("PROFILES: Dict[str, Dict[str, bool]] = {")
    for profile_name, profile_features in all_profiles.items():
        lines.append(f"    \"{profile_name}\": {{")
        for name, enabled in sorted(profile_features.items()):
            lines.append(f"        \"{name}\": {enabled},")
        lines.append("    },")
    lines.append("}")
    lines.append("")

    # Add feature categories
    lines.append("# =============================================================================")
    lines.append("# Feature Categories")
    lines.append("# =============================================================================")
    lines.append("FEATURE_CATEGORIES: Dict[str, List[str]] = {")
    for category, feature_list in categories.items():
        lines.append(f"    \"{category}\": {feature_list},")
    lines.append("}")
    lines.append("")

    # Add feature dependencies
    lines.append("# =============================================================================")
    lines.append("# Feature Dependencies")
    lines.append("# =============================================================================")
    lines.append("FEATURE_DEPENDENCIES: Dict[str, List[str]] = {")
    for feature, required in dependencies.items():
        lines.append(f"    \"{feature}\": {required},")
    lines.append("}")
    lines.append("")

    # Add resource limits
    lines.append("# =============================================================================")
    lines.append("# Resource Limits")
    lines.append("# =============================================================================")
    lines.append("LIMITS: Dict[str, int] = {")
    for name, value in sorted(limits.items()):
        lines.append(f"    \"{name}\": {value},")
    lines.append("}")
    lines.append("")

    # Add convenience functions
    lines.extend([
        "",
        "# =============================================================================",
        "# Convenience Functions",
        "# =============================================================================",
        "",
        "def has_feature(name: str) -> bool:",
        '    """Check if a feature is enabled in the active build profile."""',
        "    return FEATURES.get(name, False)",
        "",
        "",
        "def get_enabled_features() -> List[str]:",
        '    """Get list of all enabled features."""',
        "    return [name for name, enabled in FEATURES.items() if enabled]",
        "",
        "",
        "def get_profile(name: str) -> Dict[str, bool]:",
        '    """Get a profile by name."""',
        "    if name not in PROFILES:",
        "        raise KeyError(f\"Unknown profile '{name}'. Available: {list(PROFILES.keys())}\")",
        "    return PROFILES[name]",
        "",
        "",
        "def get_profile_names() -> List[str]:",
        '    """Get list of available profile names."""',
        "    return list(PROFILES.keys())",
        "",
        "",
        "def validate_dependencies(features: Dict[str, bool]) -> List[str]:",
        '    """Validate feature dependencies.',
        "",
        "    Args:",
        "        features: Dict mapping feature name to enabled state",
        "",
        "    Returns:",
        "        List of validation error messages (empty if valid)",
        '    """',
        "    errors = []",
        "    for feature, required in FEATURE_DEPENDENCIES.items():",
        "        if features.get(feature, False):",
        "            for req in required:",
        "                if not features.get(req, False):",
        "                    errors.append(f\"{feature} requires {req}\")",
        "    return errors",
        "",
        "",
        "def get_limit(name: str) -> int:",
        '    """Get a specific resource limit."""',
        "    return LIMITS.get(name, 0)",
        "",
    ])

    return "\n".join(lines)


def main(profile: str | None = None):
    """Generate build config files.

    Args:
        profile: Profile to use (default: active_profile from config)
    """
    from mara_host.core.build_profiles import reload_config

    # Reload config in case it was modified
    reload_config()

    print("Generating build configuration...")
    print(f"  Config: {CONFIG_PATH}")

    active_profile = profile or get_active_profile()
    print(f"  Active profile: {active_profile}")

    # Generate C++ header (feature flags + limits)
    cpp_content = generate_cpp_header(active_profile)
    FIRMWARE_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(FIRMWARE_OUT, "w") as f:
        f.write(cpp_content)
    print(f"  Generated: {FIRMWARE_OUT}")

    # Generate C++ limits-only header (safe to include without affecting feature flags)
    limits_content = generate_limits_header()
    FIRMWARE_LIMITS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(FIRMWARE_LIMITS_OUT, "w") as f:
        f.write(limits_content)
    print(f"  Generated: {FIRMWARE_LIMITS_OUT}")

    # Generate Python module
    py_content = generate_python_module(active_profile)
    HOST_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(HOST_OUT, "w") as f:
        f.write(py_content)
    print(f"  Generated: {HOST_OUT}")

    # Print summary
    transport = get_transport_settings()
    print(f"  Baud rate: {transport.get('baud_rate', 921600)}")
    print(f"  Upload baud: {transport.get('upload_baud_rate', 460800)}")

    features = get_profile(active_profile)
    enabled = [k for k, v in features.items() if v]
    print(f"  Enabled features ({len(enabled)}): {', '.join(enabled[:5])}...")

    print("Build config generation complete!")


if __name__ == "__main__":
    main()
