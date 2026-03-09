# mara_host/cli/commands/motor.py
"""DC Motor direct control commands.

Examples:
    mara motor set 0 0.5          # Set motor 0 to 50% forward
    mara motor set 0 -0.75        # Set motor 0 to 75% reverse
    mara motor stop 0             # Coast stop motor 0
    mara motor brake 0            # Active brake motor 0
    mara motor all-stop           # Stop all motors
"""

import argparse
import asyncio

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
)
from mara_host.cli.cli_config import get_serial_port as _get_port


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register motor control commands."""
    motor_parser = subparsers.add_parser(
        "motor",
        help="DC motor direct control",
        description="Control DC motors directly",
        aliases=["m"],
    )

    motor_sub = motor_parser.add_subparsers(
        dest="motor_cmd",
        title="motor commands",
        metavar="<subcommand>",
    )

    # Common port argument
    def add_port_arg(parser):
        parser.add_argument(
            "-p", "--port",
            default=_get_port(),
            help="Serial port (default: %(default)s)",
        )

    # motor set <id> <speed>
    set_p = motor_sub.add_parser(
        "set",
        help="Set motor speed (-1.0 to 1.0)",
    )
    set_p.add_argument("id", type=int, help="Motor ID (0-3)")
    set_p.add_argument(
        "speed",
        type=float,
        help="Speed from -1.0 (full reverse) to 1.0 (full forward)",
    )
    set_p.add_argument(
        "--percent",
        action="store_true",
        help="Interpret speed as percentage (-100 to 100)",
    )
    add_port_arg(set_p)
    set_p.set_defaults(func=cmd_motor_set)

    # motor stop <id>
    stop_p = motor_sub.add_parser(
        "stop",
        help="Coast stop motor (release power)",
    )
    stop_p.add_argument("id", type=int, help="Motor ID (0-3)")
    add_port_arg(stop_p)
    stop_p.set_defaults(func=cmd_motor_stop)

    # motor brake <id>
    brake_p = motor_sub.add_parser(
        "brake",
        help="Active brake (short motor windings)",
    )
    brake_p.add_argument("id", type=int, help="Motor ID (0-3)")
    add_port_arg(brake_p)
    brake_p.set_defaults(func=cmd_motor_brake)

    # motor all-stop
    allstop_p = motor_sub.add_parser(
        "all-stop",
        help="Stop all motors",
    )
    add_port_arg(allstop_p)
    allstop_p.set_defaults(func=cmd_motor_all_stop)

    # motor status
    status_p = motor_sub.add_parser(
        "status",
        help="Show motor status (requires telemetry)",
    )
    add_port_arg(status_p)
    status_p.set_defaults(func=cmd_motor_status)

    # Default handler
    motor_parser.set_defaults(func=lambda args: cmd_help(motor_parser))


def cmd_help(parser: argparse.ArgumentParser) -> int:
    """Show help."""
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
    """Run async coroutine from sync context."""
    return asyncio.run(coro)


def cmd_motor_set(args: argparse.Namespace) -> int:
    """Set motor speed."""
    speed = args.speed
    if args.percent:
        speed = speed / 100.0

    # Validate range
    if not -1.0 <= speed <= 1.0:
        print_error(f"Speed must be between -1.0 and 1.0 (got {speed})")
        return 1

    payload = {
        "motor_id": args.id,
        "speed": speed,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_DC_SET_SPEED", payload))
        if ok:
            direction = "forward" if speed > 0 else "reverse" if speed < 0 else "stopped"
            print_success(f"Motor {args.id}: {abs(speed)*100:.0f}% {direction}")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_motor_stop(args: argparse.Namespace) -> int:
    """Coast stop motor."""
    payload = {"motor_id": args.id}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_DC_STOP", payload))
        if ok:
            print_success(f"Motor {args.id}: stopped (coast)")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_motor_brake(args: argparse.Namespace) -> int:
    """Active brake motor."""
    payload = {"motor_id": args.id, "brake": True}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_DC_STOP", payload))
        if ok:
            print_success(f"Motor {args.id}: braking")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_motor_all_stop(args: argparse.Namespace) -> int:
    """Stop all motors."""
    console.print("[bold yellow]Stopping all motors...[/bold yellow]")

    errors = []
    for motor_id in range(4):
        payload = {"motor_id": motor_id}
        try:
            ok, error = _run_async(_connect_and_run(args.port, "CMD_DC_STOP", payload))
            if not ok:
                errors.append(f"Motor {motor_id}: {error}")
        except Exception as e:
            errors.append(f"Motor {motor_id}: {e}")

    if errors:
        for err in errors:
            print_warning(err)
        return 1

    print_success("All motors stopped")
    return 0


def cmd_motor_status(args: argparse.Namespace) -> int:
    """Show motor status."""
    console.print("[dim]Motor status requires active telemetry stream.[/dim]")
    console.print("[dim]Use 'mara monitor' to see real-time motor data.[/dim]")
    return 0
