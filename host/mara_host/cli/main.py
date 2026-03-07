#!/usr/bin/env python3
# mara_host/cli/main.py
"""MARA CLI - Modular Asynchronous Robotics Architecture.

Unified command-line interface for mara_host tools.
"""

import argparse
import sys
from typing import Callable

from rich.console import Console

from mara_host.cli.console import print_header, console


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="mara",
        description="MARA - Modular Asynchronous Robotics Architecture CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mara pins pinout            # Show visual board diagram
  mara pins list              # List all pins with status
  mara build compile          # Build firmware
  mara generate all           # Run all code generators
  mara run serial             # Connect via serial
  mara version                # Show version info

For more help on a specific command:
  mara <command> --help
""",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="<command>",
    )

    # Register all command groups
    from mara_host.cli.commands import pins
    from mara_host.cli.commands import build
    from mara_host.cli.commands import generate
    from mara_host.cli.commands import run
    from mara_host.cli.commands import record
    from mara_host.cli.commands import config
    from mara_host.cli.commands import dashboard
    from mara_host.cli.commands import flash
    from mara_host.cli.commands import monitor
    from mara_host.cli.commands import calibrate
    from mara_host.cli.commands import test
    from mara_host.cli.commands import logs
    from mara_host.cli.commands import sim
    from mara_host.cli import completions

    pins.register(subparsers)
    build.register(subparsers)
    generate.register(subparsers)
    run.register(subparsers)
    record.register(subparsers)
    config.register(subparsers)
    dashboard.register(subparsers)
    flash.register(subparsers)
    monitor.register(subparsers)
    calibrate.register(subparsers)
    test.register(subparsers)
    logs.register(subparsers)
    sim.register(subparsers)
    completions.register(subparsers)

    # Version command
    version_parser = subparsers.add_parser(
        "version",
        help="Show version information",
    )
    version_parser.set_defaults(func=cmd_version)

    return parser


def cmd_version(args: argparse.Namespace) -> int:
    """Show version information."""
    from mara_host import __version__

    console.print(f"[bold cyan]MARA CLI[/bold cyan] version [green]{__version__}[/green]")
    console.print("[dim]Modular Asynchronous Robotics Architecture[/dim]")
    console.print()
    console.print("[dim]Python platform for controlling robots with ESP32 MCU firmware[/dim]")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # No command specified - show help
    if not args.command:
        parser.print_help()
        return 0

    # Execute the command function
    if hasattr(args, "func"):
        try:
            return args.func(args)
        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted[/dim]")
            return 130
        except Exception as e:
            if args.verbose:
                console.print_exception()
            else:
                console.print(f"[error]Error:[/error] {e}")
            return 1
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
