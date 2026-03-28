# mara_host/cli/commands/ultrasonic.py
"""Ultrasonic sensor direct control commands.

Examples:
    mara ultrasonic attach 0 --trig 12 --echo 14   # Attach sensor 0
    mara ultrasonic read 0                          # Read distance
    mara ultrasonic detach 0                        # Detach sensor
    mara ultrasonic monitor 0                       # Continuous reading
"""

import argparse
import asyncio

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from mara_host.cli.context import CLIContext, run_with_context
from mara_host.cli.cli_config import get_serial_port as _get_port


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register ultrasonic sensor commands."""
    us_parser = subparsers.add_parser(
        "ultrasonic",
        help="Ultrasonic sensor control",
        description="Control ultrasonic distance sensors",
        aliases=["us", "sonar"],
    )

    us_sub = us_parser.add_subparsers(
        dest="ultrasonic_cmd",
        title="ultrasonic commands",
        metavar="<subcommand>",
    )

    def add_port_arg(parser):
        parser.add_argument(
            "-p", "--port",
            default=_get_port(),
            help="Serial port",
        )

    # ultrasonic attach <id>
    attach_p = us_sub.add_parser(
        "attach",
        help="Attach ultrasonic sensor",
    )
    attach_p.add_argument("id", type=int, help="Sensor ID (0-3)")
    attach_p.add_argument(
        "--trig",
        type=int,
        required=True,
        help="Trigger pin",
    )
    attach_p.add_argument(
        "--echo",
        type=int,
        required=True,
        help="Echo pin",
    )
    attach_p.add_argument(
        "--max-distance",
        type=float,
        default=400.0,
        help="Maximum distance in cm (default: 400)",
    )
    add_port_arg(attach_p)
    attach_p.set_defaults(func=cmd_ultrasonic_attach)

    # ultrasonic detach <id>
    detach_p = us_sub.add_parser(
        "detach",
        help="Detach ultrasonic sensor",
    )
    detach_p.add_argument("id", type=int, help="Sensor ID")
    add_port_arg(detach_p)
    detach_p.set_defaults(func=cmd_ultrasonic_detach)

    # ultrasonic read <id>
    read_p = us_sub.add_parser(
        "read",
        help="Read distance measurement",
    )
    read_p.add_argument("id", type=int, help="Sensor ID")
    read_p.add_argument(
        "--unit",
        choices=["cm", "m", "in"],
        default="cm",
        help="Distance unit (default: cm)",
    )
    add_port_arg(read_p)
    read_p.set_defaults(func=cmd_ultrasonic_read)

    # ultrasonic monitor <id>
    monitor_p = us_sub.add_parser(
        "monitor",
        help="Continuously monitor distance",
    )
    monitor_p.add_argument("id", type=int, help="Sensor ID")
    monitor_p.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help="Update interval in seconds (default: 0.1)",
    )
    monitor_p.add_argument(
        "--unit",
        choices=["cm", "m", "in"],
        default="cm",
        help="Distance unit (default: cm)",
    )
    add_port_arg(monitor_p)
    monitor_p.set_defaults(func=cmd_ultrasonic_monitor)

    us_parser.set_defaults(func=lambda args: cmd_help(us_parser))


def cmd_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


@run_with_context
async def cmd_ultrasonic_attach(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Attach ultrasonic sensor."""
    console.print(f"[bold cyan]Attaching Ultrasonic Sensor {args.id}[/bold cyan]")
    console.print(f"  Trigger: GPIO {args.trig}")
    console.print(f"  Echo: GPIO {args.echo}")
    console.print(f"  Max Distance: {args.max_distance} cm")
    console.print()

    result = await ctx.ultrasonic_service.attach(
        args.id,
        trig_pin=args.trig,
        echo_pin=args.echo,
        max_distance_cm=args.max_distance,
    )

    if result.ok:
        print_success(f"Ultrasonic {args.id}: attached")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_ultrasonic_detach(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Detach ultrasonic sensor."""
    result = await ctx.ultrasonic_service.detach(args.id)

    if result.ok:
        print_success(f"Ultrasonic {args.id}: detached")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_ultrasonic_read(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Read ultrasonic distance."""
    result = await ctx.ultrasonic_service.read(args.id)

    if result.ok:
        data = result.data or {"sensor_id": args.id}
        if data.get("degraded"):
            print_info(f"Ultrasonic {args.id}: attached, but no echo was measured")
            console.print("[yellow]Continuing in degraded hardware state[/yellow]")
        elif data.get("distance_cm") is not None:
            print_success(f"Ultrasonic {args.id}: {float(data['distance_cm']):.1f} cm")
        else:
            print_info(f"Ultrasonic {args.id}: read request sent")
            console.print("[dim]Check telemetry stream for distance data[/dim]")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_ultrasonic_monitor(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Monitor ultrasonic continuously."""
    console.print(f"[bold cyan]Monitoring Ultrasonic {args.id}[/bold cyan]")
    console.print(f"  Interval: {args.interval}s")
    console.print(f"  Unit: {args.unit}")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    try:
        while True:
            await ctx.ultrasonic_service.read(args.id)
            console.print(f"[dim]Ultrasonic {args.id}: polling...[/dim]", end="\r")
            await asyncio.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Monitoring stopped[/dim]")

    return 0
