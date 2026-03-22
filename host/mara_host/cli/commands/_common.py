# mara_host/cli/commands/_common.py
"""
Common utilities for CLI command modules.

Provides shared helpers to reduce duplication across command files.
"""

import argparse

from mara_host.cli.cli_config import get_serial_port


def add_connection_args(parser: argparse.ArgumentParser) -> None:
    """
    Add standard connection arguments to a parser.

    Adds:
        -p/--port: Serial port
        --tcp: TCP host
        --tcp-port: TCP port
        -q/--quiet: Suppress output

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "-p", "--port",
        default=get_serial_port(),
        help="Serial port (default: %(default)s)",
    )
    parser.add_argument(
        "--tcp",
        metavar="HOST",
        help="Use TCP transport instead of serial",
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=3333,
        help="TCP port (default: %(default)s)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress status messages",
    )


def add_port_arg(parser: argparse.ArgumentParser) -> None:
    """
    Add just the port argument to a parser.

    Use add_connection_args() for full connection options.

    Args:
        parser: Argument parser to add argument to
    """
    parser.add_argument(
        "-p", "--port",
        default=get_serial_port(),
        help="Serial port (default: %(default)s)",
    )


def cmd_help(parser: argparse.ArgumentParser) -> int:
    """
    Print help and return success.

    Standard handler for 'help' subcommand.

    Args:
        parser: Parser whose help to print

    Returns:
        0 (success)
    """
    parser.print_help()
    return 0
