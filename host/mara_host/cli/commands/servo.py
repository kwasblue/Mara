# mara_host/cli/commands/servo.py
"""Servo direct control commands.

Examples:
    mara servo attach 0 --pin 13      # Attach servo 0 to pin 13
    mara servo set 0 90               # Set servo 0 to 90 degrees
    mara servo set 0 45 --duration 500  # Move to 45 deg over 500ms
    mara servo detach 0               # Detach servo 0
    mara servo sweep 0                # Sweep servo 0 back and forth
"""

import argparse
import asyncio
import time

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
)
from mara_host.cli.cli_config import get_serial_port as _get_port


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register servo control commands."""
    servo_parser = subparsers.add_parser(
        "servo",
        help="Servo direct control",
        description="Control servo motors directly",
        aliases=["sv"],
    )

    servo_sub = servo_parser.add_subparsers(
        dest="servo_cmd",
        title="servo commands",
        metavar="<subcommand>",
    )

    def add_port_arg(parser):
        parser.add_argument(
            "-p", "--port",
            default=_get_port(),
            help="Serial port",
        )

    # servo attach <id>
    attach_p = servo_sub.add_parser(
        "attach",
        help="Attach servo to PWM channel",
    )
    attach_p.add_argument("id", type=int, help="Servo ID (0-7)")
    attach_p.add_argument(
        "--pin",
        type=int,
        help="GPIO pin (if not using default mapping)",
    )
    attach_p.add_argument(
        "--min-us",
        type=int,
        default=500,
        help="Minimum pulse width in microseconds (default: 500)",
    )
    attach_p.add_argument(
        "--max-us",
        type=int,
        default=2500,
        help="Maximum pulse width in microseconds (default: 2500)",
    )
    add_port_arg(attach_p)
    attach_p.set_defaults(func=cmd_servo_attach)

    # servo detach <id>
    detach_p = servo_sub.add_parser(
        "detach",
        help="Detach servo (release PWM)",
    )
    detach_p.add_argument("id", type=int, help="Servo ID (0-7)")
    add_port_arg(detach_p)
    detach_p.set_defaults(func=cmd_servo_detach)

    # servo set <id> <angle>
    set_p = servo_sub.add_parser(
        "set",
        help="Set servo angle (0-180 degrees)",
    )
    set_p.add_argument("id", type=int, help="Servo ID (0-7)")
    set_p.add_argument("angle", type=float, help="Angle in degrees (0-180)")
    set_p.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Transition duration in ms (0 = instant)",
    )
    add_port_arg(set_p)
    set_p.set_defaults(func=cmd_servo_set)

    # servo pulse <id> <pulse_us>
    pulse_p = servo_sub.add_parser(
        "pulse",
        help="Set raw pulse width in microseconds",
    )
    pulse_p.add_argument("id", type=int, help="Servo ID (0-7)")
    pulse_p.add_argument("pulse_us", type=int, help="Pulse width in microseconds")
    add_port_arg(pulse_p)
    pulse_p.set_defaults(func=cmd_servo_pulse)

    # servo sweep <id>
    sweep_p = servo_sub.add_parser(
        "sweep",
        help="Sweep servo back and forth (demo)",
    )
    sweep_p.add_argument("id", type=int, help="Servo ID (0-7)")
    sweep_p.add_argument(
        "--min",
        type=float,
        default=0,
        help="Minimum angle (default: 0)",
    )
    sweep_p.add_argument(
        "--max",
        type=float,
        default=180,
        help="Maximum angle (default: 180)",
    )
    sweep_p.add_argument(
        "--cycles",
        type=int,
        default=3,
        help="Number of sweep cycles (default: 3)",
    )
    add_port_arg(sweep_p)
    sweep_p.set_defaults(func=cmd_servo_sweep)

    # servo center <id>
    center_p = servo_sub.add_parser(
        "center",
        help="Move servo to center position (90 degrees)",
    )
    center_p.add_argument("id", type=int, help="Servo ID (0-7)")
    add_port_arg(center_p)
    center_p.set_defaults(func=cmd_servo_center)

    servo_parser.set_defaults(func=lambda args: cmd_help(servo_parser))


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


def cmd_servo_attach(args: argparse.Namespace) -> int:
    """Attach servo."""
    payload = {
        "servo_id": args.id,
        "min_us": args.min_us,
        "max_us": args.max_us,
    }
    if args.pin is not None:
        payload["pin"] = args.pin

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_SERVO_ATTACH", payload))
        if ok:
            print_success(f"Servo {args.id}: attached")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_servo_detach(args: argparse.Namespace) -> int:
    """Detach servo."""
    payload = {"servo_id": args.id}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_SERVO_DETACH", payload))
        if ok:
            print_success(f"Servo {args.id}: detached")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_servo_set(args: argparse.Namespace) -> int:
    """Set servo angle."""
    if not 0 <= args.angle <= 180:
        print_error(f"Angle must be 0-180 degrees (got {args.angle})")
        return 1

    payload = {
        "servo_id": args.id,
        "angle": args.angle,
        "duration_ms": args.duration,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_SERVO_SET_ANGLE", payload))
        if ok:
            print_success(f"Servo {args.id}: {args.angle}°")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_servo_pulse(args: argparse.Namespace) -> int:
    """Set raw pulse width."""
    payload = {
        "servo_id": args.id,
        "pulse_us": args.pulse_us,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_SERVO_SET_PULSE", payload))
        if ok:
            print_success(f"Servo {args.id}: {args.pulse_us}µs")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_servo_sweep(args: argparse.Namespace) -> int:
    """Sweep servo back and forth."""
    console.print(f"[bold cyan]Sweeping servo {args.id}[/bold cyan]")
    console.print(f"  Range: {args.min}° - {args.max}°")
    console.print(f"  Cycles: {args.cycles}")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    try:
        for cycle in range(args.cycles):
            # Go to max
            payload = {"servo_id": args.id, "angle": args.max, "duration_ms": 500}
            _run_async(_connect_and_run(args.port, "CMD_SERVO_SET_ANGLE", payload))
            time.sleep(0.6)

            # Go to min
            payload = {"servo_id": args.id, "angle": args.min, "duration_ms": 500}
            _run_async(_connect_and_run(args.port, "CMD_SERVO_SET_ANGLE", payload))
            time.sleep(0.6)

        # Return to center
        payload = {"servo_id": args.id, "angle": 90, "duration_ms": 300}
        _run_async(_connect_and_run(args.port, "CMD_SERVO_SET_ANGLE", payload))

        print_success(f"Servo {args.id}: sweep complete, centered")
    except KeyboardInterrupt:
        console.print("\n[dim]Sweep interrupted[/dim]")
    except Exception as e:
        print_error(f"Error: {e}")
        return 1

    return 0


def cmd_servo_center(args: argparse.Namespace) -> int:
    """Center servo."""
    payload = {
        "servo_id": args.id,
        "angle": 90,
        "duration_ms": 300,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_SERVO_SET_ANGLE", payload))
        if ok:
            print_success(f"Servo {args.id}: centered (90°)")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0
