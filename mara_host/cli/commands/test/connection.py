# mara_host/cli/commands/test/connection.py
"""Connection test command."""

import argparse
import asyncio
import time

from rich.progress import Progress, SpinnerColumn, TextColumn

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
)
from ._common import create_client_from_args


def cmd_connection(args: argparse.Namespace) -> int:
    """Test connection only."""
    console.print()
    console.print("[bold cyan]Connection Test[/bold cyan]")
    console.print()

    return asyncio.run(_test_connection(args))


async def _test_connection(args: argparse.Namespace) -> int:
    """Run connection test."""
    client = create_client_from_args(args)

    if getattr(args, 'tcp', None):
        console.print(f"  Transport: TCP ({args.tcp}:3333)")
    else:
        console.print(f"  Transport: Serial ({args.port})")

    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Connecting...", total=None)

        start = time.time()
        try:
            await client.start()
            elapsed = (time.time() - start) * 1000
            progress.update(task, description="Testing ping...")

            # Test ping
            pong = asyncio.Event()
            client.bus.subscribe("pong", lambda d: pong.set())
            await client.send_ping()

            try:
                await asyncio.wait_for(pong.wait(), timeout=2.0)
                print_success(f"Connected and responsive (latency: {elapsed:.0f}ms)")
            except asyncio.TimeoutError:
                print_warning("Connected but no ping response")

        except Exception as e:
            print_error(f"Connection failed: {e}")
            return 1
        finally:
            await client.stop()

    return 0
