# mara_host/cli/commands/test/servos.py
"""Servo test command."""

import argparse
import asyncio

from mara_host.cli.console import console
from ._common import TestResult, print_results, create_client_from_args


def cmd_servos(args: argparse.Namespace) -> int:
    """Test servos."""
    servo_ids = [int(x.strip()) for x in args.ids.split(",")]

    console.print()
    console.print("[bold cyan]Servo Test[/bold cyan]")
    console.print(f"  Servos: {servo_ids}")
    console.print()

    return asyncio.run(_test_servos(args, servo_ids))


async def _test_servos(args: argparse.Namespace, servo_ids: list[int]) -> int:
    """Run servo test."""
    client = create_client_from_args(args)
    results = []

    try:
        await client.start()
        await client.cmd_arm()

        for servo_id in servo_ids:
            console.print(f"  Testing servo {servo_id}...")

            try:
                # Center
                await client.cmd_servo_set_angle(servo_id, 90, 500)
                await asyncio.sleep(0.6)

                # Min
                await client.cmd_servo_set_angle(servo_id, 0, 500)
                await asyncio.sleep(0.6)

                # Max
                await client.cmd_servo_set_angle(servo_id, 180, 500)
                await asyncio.sleep(0.6)

                # Center
                await client.cmd_servo_set_angle(servo_id, 90, 500)

                results.append(TestResult(f"Servo {servo_id}", True, "Sweep 0-90-180-90 OK"))

            except Exception as e:
                results.append(TestResult(f"Servo {servo_id}", False, str(e)))

    finally:
        await client.cmd_disarm()
        await client.stop()

    print_results(results)
    return 0 if all(r.passed for r in results) else 1
