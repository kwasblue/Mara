# mara_host/cli/commands/calibrate/encoder.py
"""Encoder calibration wizard."""

import argparse
import asyncio

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from ._common import create_client_from_args


def cmd_encoder(args: argparse.Namespace) -> int:
    """Calibrate encoder."""
    encoder_id = args.encoder_id

    console.print()
    console.print(f"[bold cyan]Encoder {encoder_id} Calibration[/bold cyan]")
    console.print()
    console.print("This wizard will help you determine ticks per revolution.")
    console.print()
    console.print("You will need to:")
    console.print("  1. Mark a starting position on the wheel")
    console.print("  2. Rotate the wheel exactly one revolution")
    console.print()

    if not Confirm.ask("Ready to begin?", default=True):
        return 0

    return asyncio.run(_calibrate_encoder(args))


async def _calibrate_encoder(args: argparse.Namespace) -> int:
    """Run encoder calibration."""
    client = create_client_from_args(args)
    encoder_counts = [0]

    def on_telemetry(data):
        if isinstance(data, dict) and "encoders" in data:
            for enc in data["encoders"]:
                if enc.get("id") == args.encoder_id:
                    encoder_counts[0] = enc.get("counts", 0)

    client.bus.subscribe("telemetry", on_telemetry)

    try:
        await client.start()
        print_success("Connected")
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    try:
        console.print()
        console.print("[bold]Step 1: Zero position[/bold]")
        print_info("Mark a starting position on your wheel")

        Prompt.ask("Press Enter when ready")

        start_counts = encoder_counts[0]
        console.print(f"  Starting count: {start_counts}")

        console.print()
        console.print("[bold]Step 2: Rotate one revolution[/bold]")
        print_info("Slowly rotate the wheel exactly one full revolution")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Monitoring encoder...", total=None)

            while True:
                current = encoder_counts[0]
                diff = abs(current - start_counts)
                progress.update(task, description=f"Counts: {current} (diff: {diff})")
                await asyncio.sleep(0.1)

                # Check for Enter key (non-blocking would need special handling)
                # For now, use a simple approach
                try:
                    import sys
                    import select
                    if select.select([sys.stdin], [], [], 0)[0]:
                        sys.stdin.readline()
                        break
                except:
                    await asyncio.sleep(0.5)
                    if Confirm.ask("Done rotating?", default=False):
                        break

        end_counts = encoder_counts[0]
        ticks_per_rev = abs(end_counts - start_counts)

        console.print()
        console.print("[bold cyan]Calibration Results[/bold cyan]")
        console.print()
        console.print(f"  Encoder ID: {args.encoder_id}")
        console.print(f"  Start counts: {start_counts}")
        console.print(f"  End counts: {end_counts}")
        console.print(f"  [green]Ticks per revolution: {ticks_per_rev}[/green]")
        console.print()

        print_info("Add to your robot configuration:")
        console.print(f"""
[dim]encoders:
  encoder_{args.encoder_id}:
    ticks_per_rev: {ticks_per_rev}[/dim]
""")

    finally:
        await client.stop()

    return 0
