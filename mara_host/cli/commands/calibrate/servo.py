# mara_host/cli/commands/calibrate/servo.py
"""Servo calibration wizard."""

import argparse
import asyncio

from rich.prompt import Prompt, Confirm

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from ._common import create_client_from_args


def cmd_servo(args: argparse.Namespace) -> int:
    """Calibrate servo range."""
    servo_id = args.servo_id

    console.print()
    console.print(f"[bold cyan]Servo {servo_id} Calibration[/bold cyan]")
    console.print()
    console.print("This wizard will help you find the safe operating range.")
    console.print()

    if not Confirm.ask("Ready to begin?", default=True):
        return 0

    return asyncio.run(_calibrate_servo(args))


async def _calibrate_servo(args: argparse.Namespace) -> int:
    """Run servo calibration."""
    client = create_client_from_args(args)

    try:
        await client.start()
        print_success("Connected")
        await client.cmd_arm()
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    servo_id = args.servo_id

    try:
        # Center servo first
        console.print()
        print_info("Moving servo to center (90 degrees)...")
        await client.cmd_servo_set_angle(servo_id, 90, 500)
        await asyncio.sleep(1)

        # Find minimum
        console.print()
        console.print("[bold]Step 1: Find minimum angle[/bold]")
        print_info("Use arrow keys or enter angles to find minimum safe position")

        min_angle = 0
        current = 90

        while True:
            angle_input = Prompt.ask(f"  Current: {current}. Enter new angle (or 'done')", default="done")
            if angle_input.lower() == "done":
                min_angle = current
                break
            try:
                current = int(angle_input)
                await client.cmd_servo_set_angle(servo_id, current, 200)
                await asyncio.sleep(0.3)
            except ValueError:
                print_error("Enter a number or 'done'")

        # Find maximum
        console.print()
        console.print("[bold]Step 2: Find maximum angle[/bold]")
        await client.cmd_servo_set_angle(servo_id, 90, 500)
        await asyncio.sleep(0.5)

        max_angle = 180
        current = 90

        while True:
            angle_input = Prompt.ask(f"  Current: {current}. Enter new angle (or 'done')", default="done")
            if angle_input.lower() == "done":
                max_angle = current
                break
            try:
                current = int(angle_input)
                await client.cmd_servo_set_angle(servo_id, current, 200)
                await asyncio.sleep(0.3)
            except ValueError:
                print_error("Enter a number or 'done'")

        # Return to center
        await client.cmd_servo_set_angle(servo_id, (min_angle + max_angle) // 2, 500)

        console.print()
        console.print("[bold cyan]Calibration Results[/bold cyan]")
        console.print()
        console.print(f"  Servo ID: {servo_id}")
        console.print(f"  [green]Min angle: {min_angle}[/green]")
        console.print(f"  [green]Max angle: {max_angle}[/green]")
        console.print(f"  Center: {(min_angle + max_angle) // 2}")
        console.print()

        print_info("Add to your robot configuration:")
        console.print(f"""
[dim]servos:
  servo_{servo_id}:
    min_angle: {min_angle}
    max_angle: {max_angle}
    center_angle: {(min_angle + max_angle) // 2}[/dim]
""")

    finally:
        await client.cmd_disarm()
        await client.stop()

    return 0
