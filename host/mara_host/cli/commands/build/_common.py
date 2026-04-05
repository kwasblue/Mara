# cli/commands/build/_common.py
"""Common utilities for build commands."""

import argparse
from typing import Optional

from mara_host.tools.build_firmware import ENVIRONMENTS
from mara_host.core.build_profiles import (
    get_profile_names,
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
    profiles = get_profile_names()

    parser.add_argument(
        "--features",
        metavar="LIST",
        help="Comma-separated features to enable (e.g., wifi,ota,dc_motor) "
             f"or profile name ({', '.join(profiles)})",
    )
    parser.add_argument(
        "--no-features",
        metavar="LIST",
        help="Comma-separated features to disable (use with profiles)",
    )
    parser.add_argument(
        "--profile",
        choices=profiles,
        help="Use a build profile from mara_build.yaml",
    )
    # Keep --preset as alias for backwards compatibility
    parser.add_argument(
        "--preset",
        choices=profiles,
        dest="profile",
        help=argparse.SUPPRESS,  # Hidden, use --profile instead
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be built without building",
    )


def get_features(args: argparse.Namespace) -> Optional[dict[str, bool]]:
    """Get feature configuration from args."""
    features_str = getattr(args, 'features', None)
    profile = getattr(args, 'profile', None)
    no_features = getattr(args, 'no_features', None)

    if profile:
        features_str = profile if not features_str else f"{profile},{features_str}"

    return parse_features(features_str, no_features)


def resolve_env(args: argparse.Namespace) -> str:
    """Resolve the build environment, auto-mapping linux profiles to linux envs."""
    env = getattr(args, 'env', 'esp32_usb')
    profile = getattr(args, 'profile', None)
    # If env wasn't explicitly set but profile is a linux profile, use the profile as env
    if env == 'esp32_usb' and profile and profile.startswith('linux'):
        return profile
    return env
