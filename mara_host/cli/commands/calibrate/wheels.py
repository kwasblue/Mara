# mara_host/cli/commands/calibrate/wheels.py
"""Wheel calibration wizard."""

import argparse

from rich.prompt import FloatPrompt, Confirm

from mara_host.cli.console import (
    console,
    print_info,
)


def cmd_wheels(args: argparse.Namespace) -> int:
    """Calibrate wheel parameters."""
    console.print()
    console.print("[bold cyan]Wheel Calibration[/bold cyan]")
    console.print()
    console.print("This wizard will help you calibrate:")
    console.print("  1. Wheel diameter")
    console.print("  2. Wheel base (distance between wheels)")
    console.print()
    console.print("You will need:")
    console.print("  - A tape measure")
    console.print("  - Clear floor space (~2 meters)")
    console.print()

    if not Confirm.ask("Ready to begin?", default=True):
        return 0

    # Manual measurement approach
    console.print()
    console.print("[bold]Step 1: Measure wheel diameter[/bold]")
    diameter = FloatPrompt.ask("Enter wheel diameter in millimeters", default=65.0)
    diameter_m = diameter / 1000.0

    console.print()
    console.print("[bold]Step 2: Measure wheel base[/bold]")
    print_info("Measure the distance between the center of the two wheels")
    wheel_base = FloatPrompt.ask("Enter wheel base in millimeters", default=150.0)
    wheel_base_m = wheel_base / 1000.0

    # Summary
    console.print()
    console.print("[bold cyan]Calibration Results[/bold cyan]")
    console.print()
    console.print(f"  Wheel diameter: {diameter_m * 1000:.1f} mm ({diameter_m:.4f} m)")
    console.print(f"  Wheel base: {wheel_base_m * 1000:.1f} mm ({wheel_base_m:.4f} m)")
    console.print()

    print_info("Add to your robot configuration:")
    console.print(f"""
[dim]drive:
  wheel_diameter_m: {diameter_m}
  wheel_base_m: {wheel_base_m}[/dim]
""")

    return 0
