# cli/commands/build/_registry.py
"""Build command registration."""

import argparse

from mara_host.tools.build_firmware import ENVIRONMENTS, PRESETS

from ._common import add_common_args, add_feature_args
from .compile import cmd_compile
from .upload import cmd_upload
from .clean import cmd_clean
from .test import cmd_test
from .features import cmd_features
from .size import cmd_size
from .watch import cmd_watch


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register build commands."""
    build_parser = subparsers.add_parser(
        "build",
        help="Firmware build operations",
        description="Build, upload, and test ESP32 firmware",
    )

    build_sub = build_parser.add_subparsers(
        dest="build_cmd",
        title="build commands",
        metavar="<subcommand>",
    )

    # compile
    compile_p = build_sub.add_parser(
        "compile",
        help="Compile firmware",
    )
    add_common_args(compile_p)
    add_feature_args(compile_p)
    compile_p.set_defaults(func=cmd_compile)

    # upload
    upload_p = build_sub.add_parser(
        "upload",
        help="Compile and flash firmware to ESP32",
    )
    add_common_args(upload_p)
    add_feature_args(upload_p)
    upload_p.set_defaults(func=cmd_upload)

    # clean
    clean_p = build_sub.add_parser(
        "clean",
        help="Clean build artifacts",
    )
    clean_p.add_argument(
        "-e", "--env",
        default=None,
        help="Environment to clean (default: all)",
    )
    clean_p.set_defaults(func=cmd_clean)

    # test
    test_p = build_sub.add_parser(
        "test",
        help="Run firmware unit tests",
    )
    test_p.add_argument(
        "--native",
        action="store_true",
        default=True,
        help="Run native tests (default)",
    )
    test_p.add_argument(
        "--device",
        action="store_true",
        help="Run tests on device",
    )
    test_p.add_argument(
        "-f", "--filter",
        dest="filter_pattern",
        help="Filter tests by pattern",
    )
    test_p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    test_p.set_defaults(func=cmd_test)

    # features
    features_p = build_sub.add_parser(
        "features",
        help="List available features and presets",
    )
    features_p.set_defaults(func=cmd_features)

    # size
    size_p = build_sub.add_parser(
        "size",
        help="Show firmware size information",
    )
    size_p.add_argument(
        "-e", "--env",
        default="esp32_usb",
        choices=sorted(ENVIRONMENTS),
        help="Environment to check (default: esp32_usb)",
    )
    size_p.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed section breakdown",
    )
    size_p.set_defaults(func=cmd_size)

    # watch
    watch_p = build_sub.add_parser(
        "watch",
        help="Watch for changes and rebuild automatically",
    )
    add_common_args(watch_p)
    add_feature_args(watch_p)
    watch_p.set_defaults(func=cmd_watch)

    # Default handler
    build_parser.set_defaults(
        func=lambda args: cmd_compile(args) if hasattr(args, 'env') else cmd_features(args)
    )
