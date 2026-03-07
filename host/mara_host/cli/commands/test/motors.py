# mara_host/cli/commands/test/motors.py
"""Motor test command."""

import argparse
import asyncio

from rich.prompt import Confirm

from mara_host.cli.console import (
    console,
    print_warning,
)
from ._common import TestResult, print_results, create_client_from_args


def cmd_motors(args: argparse.Namespace) -> int:
    """Test motors."""
    motor_ids = [int(x.strip()) for x in args.ids.split(",")]

    console.print()
    console.print("[bold cyan]Motor Test[/bold cyan]")
    console.print(f"  Motors: {motor_ids}")
    console.print()

    print_warning("Motors will spin briefly. Make sure wheels are off the ground!")

    if not Confirm.ask("Continue?", default=True):
        return 0

    return asyncio.run(_test_motors(args, motor_ids))


async def _test_motors(args: argparse.Namespace, motor_ids: list[int]) -> int:
    """Run motor test."""
    client = create_client_from_args(args)
    results = []

    try:
        await client.start()
        await client.cmd_arm()
        await client.cmd_set_mode("ACTIVE")

        for motor_id in motor_ids:
            console.print(f"  Testing motor {motor_id}...")

            try:
                # Forward
                await client.cmd_dc_set_speed(motor_id, 0.3)
                await asyncio.sleep(0.5)

                # Reverse
                await client.cmd_dc_set_speed(motor_id, -0.3)
                await asyncio.sleep(0.5)

                # Stop
                await client.cmd_dc_set_speed(motor_id, 0)

                results.append(TestResult(f"Motor {motor_id}", True, "Forward/Reverse OK"))

            except Exception as e:
                results.append(TestResult(f"Motor {motor_id}", False, str(e)))
                await client.cmd_dc_set_speed(motor_id, 0)

    finally:
        await client.cmd_disarm()
        await client.stop()

    print_results(results)
    return 0 if all(r.passed for r in results) else 1
