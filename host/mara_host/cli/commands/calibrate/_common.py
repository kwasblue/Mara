# mara_host/cli/commands/calibrate/_common.py
"""Common utilities for calibration commands."""

import argparse
from typing import TYPE_CHECKING

from mara_host.cli.console import console
from mara_host.cli.cli_config import get_serial_port as _get_port

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


def add_transport_args(p: argparse.ArgumentParser) -> None:
    """Add common transport arguments."""
    p.add_argument("-p", "--port", default=_get_port())
    p.add_argument("--tcp", metavar="HOST", help="Use TCP instead of serial")


def create_client_from_args(args) -> "MaraClient":
    """Create client from args using factory."""
    from mara_host.command.factory import create_client_from_args as factory_create
    return factory_create(args)


def show_calibrations() -> int:
    """Show available calibrations."""
    console.print()
    console.print("[bold cyan]Available Calibrations[/bold cyan]")
    console.print()
    console.print("  [green]motor[/green]    Calibrate DC motor (dead zone, max speed)")
    console.print("  [green]encoder[/green]  Calibrate encoder (ticks per revolution)")
    console.print("  [green]imu[/green]      Calibrate IMU (gyro/accel offsets)")
    console.print("  [green]servo[/green]    Calibrate servo range (min/max angles)")
    console.print("  [green]wheels[/green]   Calibrate wheel diameter and base width")
    console.print("  [green]pid[/green]      Test and tune PID controller")
    console.print()
    console.print("[dim]Usage: mara calibrate <component> [options][/dim]")
    return 0
