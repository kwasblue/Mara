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
import time

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
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


async def _connect_and_run(port: str, command: str, payload: dict) -> tuple[bool, str]:
    """Connect to robot, send command, and return result."""
    from mara_host.services.transport import ConnectionService, ConnectionConfig, TransportType

    config = ConnectionConfig(
        transport_type=TransportType.SERIAL,
        port=port,
        baudrate=115200,
    )

    conn = ConnectionService(config)
    try:
        await conn.connect()
        ok, error = await conn.client.send_reliable(command, payload)
        return ok, error or ""
    finally:
        await conn.disconnect()


def _run_async(coro):
    return asyncio.run(coro)


def cmd_ultrasonic_attach(args: argparse.Namespace) -> int:
    """Attach ultrasonic sensor."""
    payload = {
        "sensor_id": args.id,
        "trig_pin": args.trig,
        "echo_pin": args.echo,
        "max_distance_cm": args.max_distance,
    }

    console.print(f"[bold cyan]Attaching Ultrasonic Sensor {args.id}[/bold cyan]")
    console.print(f"  Trigger: GPIO {args.trig}")
    console.print(f"  Echo: GPIO {args.echo}")
    console.print(f"  Max Distance: {args.max_distance} cm")
    console.print()

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_ULTRASONIC_ATTACH", payload))
        if ok:
            print_success(f"Ultrasonic {args.id}: attached")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_ultrasonic_detach(args: argparse.Namespace) -> int:
    """Detach ultrasonic sensor."""
    payload = {"sensor_id": args.id}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_ULTRASONIC_DETACH", payload))
        if ok:
            print_success(f"Ultrasonic {args.id}: detached")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_ultrasonic_read(args: argparse.Namespace) -> int:
    """Read ultrasonic distance."""
    payload = {"sensor_id": args.id}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_ULTRASONIC_READ", payload))
        if ok:
            print_info(f"Ultrasonic {args.id}: read request sent")
            console.print("[dim]Check telemetry stream for distance data[/dim]")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_ultrasonic_monitor(args: argparse.Namespace) -> int:
    """Monitor ultrasonic continuously."""
    console.print(f"[bold cyan]Monitoring Ultrasonic {args.id}[/bold cyan]")
    console.print(f"  Interval: {args.interval}s")
    console.print(f"  Unit: {args.unit}")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    try:
        while True:
            payload = {"sensor_id": args.id}
            _run_async(_connect_and_run(args.port, "CMD_ULTRASONIC_READ", payload))
            console.print(f"[dim]Ultrasonic {args.id}: polling...[/dim]", end="\r")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Monitoring stopped[/dim]")

    return 0
