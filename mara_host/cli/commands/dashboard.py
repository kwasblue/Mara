# mara_host/cli/commands/dashboard.py
"""Dashboard commands for MARA CLI (stub for future implementation)."""

import argparse

from mara_host.cli.console import (
    console,
    print_info,
    print_warning,
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register dashboard command."""
    dash_parser = subparsers.add_parser(
        "dashboard",
        help="Launch web dashboard (coming soon)",
        description="Launch the MARA web dashboard for robot monitoring and control",
    )
    dash_parser.add_argument(
        "-p", "--port",
        type=int,
        default=8080,
        help="Web server port (default: 8080)",
    )
    dash_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Web server host (default: 127.0.0.1)",
    )
    dash_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically",
    )
    dash_parser.set_defaults(func=cmd_dashboard)


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Launch web dashboard."""
    port = args.port
    host = args.host

    console.print()
    console.print("[bold cyan]MARA Dashboard[/bold cyan]")
    console.print()

    print_warning("The web dashboard is not yet implemented")
    console.print()
    print_info("Planned features:")
    console.print("  - Real-time telemetry visualization")
    console.print("  - Motor control interface")
    console.print("  - Sensor readings display")
    console.print("  - Configuration editor")
    console.print("  - Session recording/playback")
    console.print()
    print_info("For now, use the CLI commands:")
    console.print("  mara run serial      # Connect to robot")
    console.print("  mara pins pinout     # View pin assignments")
    console.print("  mara record <name>   # Record telemetry")

    return 0
