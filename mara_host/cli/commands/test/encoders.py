# mara_host/cli/commands/test/encoders.py
"""Encoder test command."""

import argparse
import asyncio

from mara_host.cli.console import (
    console,
    print_success,
    print_info,
    print_warning,
)
from ._common import create_client_from_args


def cmd_encoders(args: argparse.Namespace) -> int:
    """Test encoders."""
    console.print()
    console.print("[bold cyan]Encoder Test[/bold cyan]")
    console.print()
    print_info("Rotate the wheels manually to verify encoder readings")

    return asyncio.run(_test_encoders(args))


async def _test_encoders(args: argparse.Namespace) -> int:
    """Run encoder test."""
    client = create_client_from_args(args)
    encoder_data = {}

    def on_telemetry(data):
        if isinstance(data, dict) and "encoders" in data:
            for enc in data["encoders"]:
                enc_id = enc.get("id", 0)
                encoder_data[enc_id] = enc.get("counts", 0)

    client.bus.subscribe("telemetry", on_telemetry)

    try:
        await client.start()
        print_success("Connected - monitoring encoders")
        console.print()
        console.print("[dim]Rotate wheels to see encoder counts change[/dim]")
        console.print("[dim]Press Ctrl+C when done[/dim]")
        console.print()

        while True:
            if encoder_data:
                line = "  Encoders: " + " | ".join(
                    f"[{eid}]={cnt}" for eid, cnt in sorted(encoder_data.items())
                )
                console.print(line, end="\r")
            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        console.print()

    finally:
        await client.stop()

    if encoder_data:
        print_success(f"Detected {len(encoder_data)} encoder(s)")
    else:
        print_warning("No encoder data received")

    return 0
