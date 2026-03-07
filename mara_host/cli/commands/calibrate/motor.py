# mara_host/cli/commands/calibrate/motor.py
"""DC motor calibration wizard."""

import argparse
import asyncio

from rich.prompt import Confirm

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from ._common import create_client_from_args


def cmd_motor(args: argparse.Namespace) -> int:
    """Calibrate DC motor."""
    motor_id = args.motor_id

    console.print()
    console.print(f"[bold cyan]Motor {motor_id} Calibration[/bold cyan]")
    console.print()
    console.print("This wizard will help you find:")
    console.print("  1. Dead zone (minimum PWM to start moving)")
    console.print("  2. Maximum usable speed")
    console.print("  3. Direction verification")
    console.print()

    if not Confirm.ask("Ready to begin?", default=True):
        return 0

    return asyncio.run(_calibrate_motor(args))


async def _calibrate_motor(args: argparse.Namespace) -> int:
    """Run motor calibration."""
    client = create_client_from_args(args)

    try:
        await client.start()
        print_success("Connected")
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    motor_id = args.motor_id

    try:
        # Arm and set active
        await client.cmd_arm()
        await client.cmd_set_mode("ACTIVE")

        console.print()
        console.print("[bold]Step 1: Finding dead zone[/bold]")
        console.print("[dim]The motor will slowly increase speed until it moves[/dim]")
        console.print()

        dead_zone = 0.0
        for pwm in range(5, 100, 5):
            speed = pwm / 100.0
            await client.cmd_dc_motor_set_speed(motor_id, speed)
            console.print(f"  PWM: {pwm}%", end="\r")
            await asyncio.sleep(0.5)

            if Confirm.ask(f"  PWM {pwm}%: Is the motor moving?", default=False):
                dead_zone = speed
                break

        await client.cmd_dc_motor_set_speed(motor_id, 0)
        print_success(f"Dead zone: {dead_zone * 100:.0f}%")

        console.print()
        console.print("[bold]Step 2: Direction check[/bold]")
        print_info("Motor will run forward briefly")

        await client.cmd_dc_motor_set_speed(motor_id, 0.3)
        await asyncio.sleep(1)
        await client.cmd_dc_motor_set_speed(motor_id, 0)

        inverted = not Confirm.ask("Did the motor spin in the expected direction?", default=True)

        console.print()
        console.print("[bold]Step 3: Maximum speed test[/bold]")
        print_info("Motor will run at full speed briefly")

        if Confirm.ask("Ready for full speed test?", default=True):
            await client.cmd_dc_motor_set_speed(motor_id, 1.0 if not inverted else -1.0)
            await asyncio.sleep(2)
            await client.cmd_dc_motor_set_speed(motor_id, 0)

        # Summary
        console.print()
        console.print("[bold cyan]Calibration Results[/bold cyan]")
        console.print()
        console.print(f"  Motor ID: {motor_id}")
        console.print(f"  Dead zone: {dead_zone * 100:.0f}%")
        console.print(f"  Inverted: {inverted}")
        console.print()

        print_info("Add these to your robot configuration:")
        console.print(f"""
[dim]motors:
  motor_{motor_id}:
    dead_zone: {dead_zone}
    inverted: {str(inverted).lower()}[/dim]
""")

    finally:
        await client.cmd_dc_motor_set_speed(motor_id, 0)
        await client.cmd_disarm()
        await client.stop()

    return 0
