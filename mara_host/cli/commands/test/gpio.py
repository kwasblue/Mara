# mara_host/cli/commands/test/gpio.py
"""GPIO test command."""

import argparse
import asyncio

from mara_host.cli.console import (
    console,
    print_success,
    print_info,
)
from ._common import create_client_from_args


def cmd_gpio(args: argparse.Namespace) -> int:
    """Test GPIO."""
    console.print()
    console.print("[bold cyan]GPIO Test[/bold cyan]")
    console.print()
    print_info("Testing LED GPIO (channel 0)")

    return asyncio.run(_test_gpio(args))


async def _test_gpio(args: argparse.Namespace) -> int:
    """Run GPIO test."""
    client = create_client_from_args(args)

    try:
        await client.start()

        console.print("  Blinking LED 3 times...")
        for _ in range(3):
            await client.cmd_led_on()
            await asyncio.sleep(0.2)
            await client.cmd_led_off()
            await asyncio.sleep(0.2)

        print_success("GPIO test complete")

    finally:
        await client.stop()

    return 0
