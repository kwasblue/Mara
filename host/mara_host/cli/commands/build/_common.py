# cli/commands/build/_common.py
"""Common utilities for build commands."""

import argparse
from typing import Optional

from mara_host.tools.build_firmware import (
    ENVIRONMENTS,
    PRESETS,
    parse_features,
)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common build arguments."""
    parser.add_argument(
        "-e", "--env",
        default="esp32_usb",
        choices=sorted(ENVIRONMENTS),
        help="Build environment (default: esp32_usb)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "-g", "--generate",
        action="store_true",
        help="Run code generators first",
    )
    parser.add_argument(
        "--build-backend",
        default="platformio",
        help="Build backend to use (default: platformio)",
    )


def add_feature_args(parser: argparse.ArgumentParser) -> None:
    """Add feature-related arguments."""
    parser.add_argument(
        "--features",
        metavar="LIST",
        help="Comma-separated features to enable (e.g., wifi,ota,dc_motor) "
             "or preset name (minimal, motors, sensors, control, full)",
    )
    parser.add_argument(
        "--no-features",
        metavar="LIST",
        help="Comma-separated features to disable (use with presets)",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS.keys()),
        help="Use a feature preset",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be built without building",
    )


def get_features(args: argparse.Namespace) -> Optional[dict[str, bool]]:
    """Get feature configuration from args."""
    features_str = getattr(args, 'features', None)
    preset = getattr(args, 'preset', None)
    no_features = getattr(args, 'no_features', None)

    if preset:
        features_str = preset if not features_str else f"{preset},{features_str}"

    return parse_features(features_str, no_features)
