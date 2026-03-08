# mara_host/cli/commands/encoder.py
"""Encoder direct control commands.

Examples:
    mara encoder attach 0 --pin-a 34 --pin-b 35   # Attach encoder 0
    mara encoder read 0                            # Read encoder 0 count
    mara encoder reset 0                           # Reset encoder 0 to zero
    mara encoder detach 0                          # Detach encoder 0
    mara encoder monitor 0                         # Continuous reading (demo)
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


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register encoder control commands."""
    enc_parser = subparsers.add_parser(
        "encoder",
        help="Encoder direct control",
        description="Control rotary encoders directly",
        aliases=["enc"],
    )

    enc_sub = enc_parser.add_subparsers(
        dest="encoder_cmd",
        title="encoder commands",
        metavar="<subcommand>",
    )

    def add_port_arg(parser):
        parser.add_argument(
            "-p", "--port",
            default="/dev/cu.usbserial-0001",
            help="Serial port",
        )

    # encoder attach <id>
    attach_p = enc_sub.add_parser(
        "attach",
        help="Attach encoder to pins",
    )
    attach_p.add_argument("id", type=int, help="Encoder ID (0-3)")
    attach_p.add_argument(
        "--pin-a",
        type=int,
        required=True,
        help="Pin A (CLK/phase A)",
    )
    attach_p.add_argument(
        "--pin-b",
        type=int,
        required=True,
        help="Pin B (DT/phase B)",
    )
    attach_p.add_argument(
        "--ppr",
        type=int,
        default=11,
        help="Pulses per revolution (default: 11)",
    )
    attach_p.add_argument(
        "--gear-ratio",
        type=float,
        default=1.0,
        help="Gear ratio (default: 1.0)",
    )
    add_port_arg(attach_p)
    attach_p.set_defaults(func=cmd_encoder_attach)

    # encoder detach <id>
    detach_p = enc_sub.add_parser(
        "detach",
        help="Detach encoder",
    )
    detach_p.add_argument("id", type=int, help="Encoder ID")
    add_port_arg(detach_p)
    detach_p.set_defaults(func=cmd_encoder_detach)

    # encoder read <id>
    read_p = enc_sub.add_parser(
        "read",
        help="Read encoder count and velocity",
    )
    read_p.add_argument("id", type=int, help="Encoder ID")
    add_port_arg(read_p)
    read_p.set_defaults(func=cmd_encoder_read)

    # encoder reset <id>
    reset_p = enc_sub.add_parser(
        "reset",
        help="Reset encoder count to zero",
    )
    reset_p.add_argument("id", type=int, help="Encoder ID")
    add_port_arg(reset_p)
    reset_p.set_defaults(func=cmd_encoder_reset)

    # encoder monitor <id>
    monitor_p = enc_sub.add_parser(
        "monitor",
        help="Continuously monitor encoder (demo)",
    )
    monitor_p.add_argument("id", type=int, help="Encoder ID")
    monitor_p.add_argument(
        "--interval",
        type=float,
        default=0.2,
        help="Update interval in seconds (default: 0.2)",
    )
    add_port_arg(monitor_p)
    monitor_p.set_defaults(func=cmd_encoder_monitor)

    enc_parser.set_defaults(func=lambda args: cmd_help(enc_parser))


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


def cmd_encoder_attach(args: argparse.Namespace) -> int:
    """Attach encoder."""
    payload = {
        "encoder_id": args.id,
        "pin_a": args.pin_a,
        "pin_b": args.pin_b,
        "ppr": args.ppr,
        "gear_ratio": args.gear_ratio,
    }

    console.print(f"[bold cyan]Attaching Encoder {args.id}[/bold cyan]")
    console.print(f"  Pin A: {args.pin_a}")
    console.print(f"  Pin B: {args.pin_b}")
    console.print(f"  PPR: {args.ppr}")
    console.print()

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_ENCODER_ATTACH", payload))
        if ok:
            print_success(f"Encoder {args.id}: attached")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_encoder_detach(args: argparse.Namespace) -> int:
    """Detach encoder."""
    payload = {"encoder_id": args.id}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_ENCODER_DETACH", payload))
        if ok:
            print_success(f"Encoder {args.id}: detached")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_encoder_read(args: argparse.Namespace) -> int:
    """Read encoder."""
    payload = {"encoder_id": args.id}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_ENCODER_READ", payload))
        if ok:
            print_info(f"Encoder {args.id}: read request sent")
            console.print("[dim]Check telemetry stream for encoder data[/dim]")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_encoder_reset(args: argparse.Namespace) -> int:
    """Reset encoder count."""
    payload = {"encoder_id": args.id}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_ENCODER_RESET", payload))
        if ok:
            print_success(f"Encoder {args.id}: count reset to 0")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_encoder_monitor(args: argparse.Namespace) -> int:
    """Monitor encoder continuously."""
    console.print(f"[bold cyan]Monitoring Encoder {args.id}[/bold cyan]")
    console.print(f"  Interval: {args.interval}s")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    try:
        while True:
            payload = {"encoder_id": args.id}
            _run_async(_connect_and_run(args.port, "CMD_ENCODER_READ", payload))
            console.print(f"[dim]Encoder {args.id}: polling...[/dim]", end="\r")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Monitoring stopped[/dim]")

    return 0
