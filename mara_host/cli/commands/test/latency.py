# mara_host/cli/commands/test/latency.py
"""Latency test command."""

import argparse
import asyncio
from statistics import mean, stdev

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
)
from ._common import create_client_from_args


def cmd_latency(args: argparse.Namespace) -> int:
    """Measure ping/pong latency."""
    console.print()
    console.print("[bold cyan]Ping Latency Test[/bold cyan]")
    console.print(f"  Pings: {args.count}")
    console.print(f"  Delay: {args.delay}s")
    console.print()

    return asyncio.run(_test_latency(args))


async def _test_latency(args: argparse.Namespace) -> int:
    """Run latency measurement."""
    client = create_client_from_args(args)

    if getattr(args, 'tcp', None):
        console.print(f"  Transport: TCP ({args.tcp})")
    else:
        console.print(f"  Transport: Serial ({args.port})")

    console.print()

    pending_pong: asyncio.Future | None = None
    loop = asyncio.get_event_loop()

    def on_pong(data):
        nonlocal pending_pong
        if pending_pong is not None and not pending_pong.done():
            pending_pong.set_result(loop.time())

    client.bus.subscribe("pong", on_pong)

    try:
        await client.start()
        print_success("Connected")
        console.print()

        results: list[float] = []
        timeouts = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Measuring latency...", total=None)

            for i in range(args.count):
                progress.update(task, description=f"Ping {i+1}/{args.count}...")

                # Create future and send ping
                pending_pong = loop.create_future()
                t0 = loop.time()
                await client.send_ping()

                try:
                    t1 = await asyncio.wait_for(pending_pong, timeout=1.0)
                    rtt_ms = (t1 - t0) * 1000.0
                    results.append(rtt_ms)
                except asyncio.TimeoutError:
                    timeouts += 1

                pending_pong = None
                await asyncio.sleep(args.delay)

        # Print results
        console.print()
        console.print("[bold cyan]Latency Results[/bold cyan]")
        console.print()

        if results:
            table = Table(show_header=False, box=None)
            table.add_column("Metric", style="cyan", width=12)
            table.add_column("Value", justify="right")

            table.add_row("Samples", str(len(results)))
            table.add_row("Timeouts", str(timeouts))
            table.add_row("Min", f"{min(results):.2f} ms")
            table.add_row("Max", f"{max(results):.2f} ms")
            table.add_row("Mean", f"{mean(results):.2f} ms")
            if len(results) > 1:
                table.add_row("Std Dev", f"{stdev(results):.2f} ms")

            # Percentiles
            sorted_results = sorted(results)
            p50 = sorted_results[len(sorted_results) // 2]
            p95 = sorted_results[int(len(sorted_results) * 0.95)]
            p99 = sorted_results[int(len(sorted_results) * 0.99)]

            table.add_row("P50", f"{p50:.2f} ms")
            table.add_row("P95", f"{p95:.2f} ms")
            table.add_row("P99", f"{p99:.2f} ms")

            console.print(table)
            console.print()

            if timeouts > 0:
                print_warning(f"{timeouts} pings timed out")
            else:
                print_success("All pings received")
        else:
            print_error("No successful pings - check connection")
            return 1

    finally:
        await client.stop()

    return 0
