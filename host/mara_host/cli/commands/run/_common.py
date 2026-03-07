# mara_host/cli/commands/run/_common.py
"""Common utilities for run commands."""

import argparse
import logging

from mara_host.cli.console import console

# Log level mapping
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def add_logging_args(parser: argparse.ArgumentParser) -> None:
    """Add common logging arguments to a parser."""
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="Log level (default: info)",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="Directory for log files (default: logs)",
    )


def get_log_params(args: argparse.Namespace) -> tuple[int, str]:
    """Extract log level and directory from args."""
    level = LOG_LEVELS.get(getattr(args, "log_level", "info"), logging.INFO)
    log_dir = getattr(args, "log_dir", "logs")
    return level, log_dir


def show_transports() -> int:
    """Show available transports."""
    console.print()
    console.print("[bold cyan]Available Transports[/bold cyan]")
    console.print()
    console.print("  [green]serial[/green]  Connect via USB serial port")
    console.print("  [green]tcp[/green]     Connect via TCP/WiFi")
    console.print("  [green]can[/green]     Connect via CAN bus")
    console.print("  [green]mqtt[/green]    Connect via MQTT broker")
    console.print()
    console.print("[dim]Usage: mara run <transport> [options][/dim]")
    return 0
