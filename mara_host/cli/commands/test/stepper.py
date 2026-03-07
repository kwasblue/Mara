# mara_host/cli/commands/test/stepper.py
"""Stepper motor test command."""

import argparse
import asyncio

from rich.prompt import Confirm

from mara_host.cli.console import (
    console,
    print_success,
    print_warning,
)
from ._common import TestResult, print_results, create_client_from_args


def cmd_stepper(args: argparse.Namespace) -> int:
    """Test stepper motors."""
    stepper_ids = [int(x.strip()) for x in args.ids.split(",")]

    console.print()
    console.print("[bold cyan]Stepper Motor Test[/bold cyan]")
    console.print(f"  Motors: {stepper_ids}")
    console.print(f"  Steps: {args.steps}")
    console.print(f"  Speed: {args.speed} rev/s")
    console.print(f"  Cycles: {args.cycles}")
    console.print()

    print_warning("Stepper motors will move! Make sure they're safe to operate.")

    if not Confirm.ask("Continue?", default=True):
        return 0

    return asyncio.run(_test_stepper(args, stepper_ids))


async def _test_stepper(args: argparse.Namespace, stepper_ids: list[int]) -> int:
    """Run stepper test."""
    client = create_client_from_args(args)
    results = []

    # Default steps per revolution (can be overridden)
    steps_per_rev = 200
    speed_steps_s = args.speed * steps_per_rev

    try:
        await client.start()
        print_success("Connected")

        # Safety setup
        await client.cmd_clear_estop()
        await client.cmd_arm()
        await client.cmd_set_mode("ACTIVE")

        for motor_id in stepper_ids:
            console.print(f"\n  Testing stepper {motor_id}...")

            try:
                # Enable stepper
                await client.send_json_cmd("CMD_STEPPER_ENABLE", {
                    "motor_id": motor_id,
                    "enable": True
                })
                await asyncio.sleep(0.1)

                # Forward/reverse cycles
                for cycle in range(1, args.cycles + 1):
                    console.print(f"    Cycle {cycle}/{args.cycles}: ", end="")

                    # Forward
                    console.print("FWD ", end="")
                    await client.send_json_cmd("CMD_STEPPER_MOVE_REL", {
                        "motor_id": motor_id,
                        "steps": args.steps,
                        "speed_steps_s": speed_steps_s
                    })
                    # Wait for move to complete (rough estimate)
                    move_time = abs(args.steps) / speed_steps_s + 0.2
                    await asyncio.sleep(move_time)

                    # Reverse
                    console.print("REV")
                    await client.send_json_cmd("CMD_STEPPER_MOVE_REL", {
                        "motor_id": motor_id,
                        "steps": -args.steps,
                        "speed_steps_s": speed_steps_s
                    })
                    await asyncio.sleep(move_time)

                # Stop and disable
                await client.send_json_cmd("CMD_STEPPER_STOP", {"motor_id": motor_id})
                await client.send_json_cmd("CMD_STEPPER_ENABLE", {
                    "motor_id": motor_id,
                    "enable": False
                })

                results.append(TestResult(
                    f"Stepper {motor_id}",
                    True,
                    f"{args.cycles} cycles OK"
                ))

            except Exception as e:
                results.append(TestResult(f"Stepper {motor_id}", False, str(e)))
                # Try to stop on error
                try:
                    await client.send_json_cmd("CMD_STEPPER_STOP", {"motor_id": motor_id})
                except:
                    pass

    finally:
        await client.cmd_disarm()
        await client.stop()

    print_results(results)
    return 0 if all(r.passed for r in results) else 1
