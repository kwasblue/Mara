# mara_host/cli/commands/gpio.py
"""GPIO direct control commands.

Examples:
    mara gpio register 0 2 output    # Register channel 0 on pin 2 as output
    mara gpio register 1 4 input     # Register channel 1 on pin 4 as input
    mara gpio high 0                 # Set channel 0 high
    mara gpio low 0                  # Set channel 0 low
    mara gpio toggle 0               # Toggle channel 0
    mara gpio read 1                 # Read channel 1 state
    mara gpio blink 0                # Blink channel 0
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
    """Register GPIO control commands."""
    gpio_parser = subparsers.add_parser(
        "gpio",
        help="GPIO direct control",
        description="Control GPIO pins directly",
    )

    gpio_sub = gpio_parser.add_subparsers(
        dest="gpio_cmd",
        title="gpio commands",
        metavar="<subcommand>",
    )

    def add_port_arg(parser):
        parser.add_argument(
            "-p", "--port",
            default="/dev/cu.usbserial-0001",
            help="Serial port",
        )

    # gpio register <channel> <pin> <mode>
    reg_p = gpio_sub.add_parser(
        "register",
        help="Register GPIO channel",
    )
    reg_p.add_argument("channel", type=int, help="Channel number (0-15)")
    reg_p.add_argument("pin", type=int, help="GPIO pin number")
    reg_p.add_argument(
        "mode",
        choices=["input", "output", "input_pullup", "input_pulldown"],
        help="Pin mode",
    )
    add_port_arg(reg_p)
    reg_p.set_defaults(func=cmd_gpio_register)

    # gpio high <channel>
    high_p = gpio_sub.add_parser(
        "high",
        help="Set channel high (1)",
    )
    high_p.add_argument("channel", type=int, help="Channel number")
    add_port_arg(high_p)
    high_p.set_defaults(func=cmd_gpio_high)

    # gpio low <channel>
    low_p = gpio_sub.add_parser(
        "low",
        help="Set channel low (0)",
    )
    low_p.add_argument("channel", type=int, help="Channel number")
    add_port_arg(low_p)
    low_p.set_defaults(func=cmd_gpio_low)

    # gpio write <channel> <value>
    write_p = gpio_sub.add_parser(
        "write",
        help="Write value to channel (0 or 1)",
    )
    write_p.add_argument("channel", type=int, help="Channel number")
    write_p.add_argument("value", type=int, choices=[0, 1], help="Value (0 or 1)")
    add_port_arg(write_p)
    write_p.set_defaults(func=cmd_gpio_write)

    # gpio read <channel>
    read_p = gpio_sub.add_parser(
        "read",
        help="Read channel state",
    )
    read_p.add_argument("channel", type=int, help="Channel number")
    add_port_arg(read_p)
    read_p.set_defaults(func=cmd_gpio_read)

    # gpio toggle <channel>
    toggle_p = gpio_sub.add_parser(
        "toggle",
        help="Toggle channel state",
    )
    toggle_p.add_argument("channel", type=int, help="Channel number")
    add_port_arg(toggle_p)
    toggle_p.set_defaults(func=cmd_gpio_toggle)

    # gpio blink <channel>
    blink_p = gpio_sub.add_parser(
        "blink",
        help="Blink channel (demo)",
    )
    blink_p.add_argument("channel", type=int, help="Channel number")
    blink_p.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of blinks (default: 5)",
    )
    blink_p.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Blink interval in seconds (default: 0.5)",
    )
    add_port_arg(blink_p)
    blink_p.set_defaults(func=cmd_gpio_blink)

    gpio_parser.set_defaults(func=lambda args: cmd_help(gpio_parser))


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


MODE_MAP = {
    "input": 0,
    "output": 1,
    "input_pullup": 2,
    "input_pulldown": 3,
}


def cmd_gpio_register(args: argparse.Namespace) -> int:
    """Register GPIO channel."""
    payload = {
        "channel": args.channel,
        "pin": args.pin,
        "mode": MODE_MAP[args.mode],
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_GPIO_REGISTER_CHANNEL", payload))
        if ok:
            print_success(f"GPIO channel {args.channel}: pin {args.pin} as {args.mode}")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_gpio_high(args: argparse.Namespace) -> int:
    """Set channel high."""
    payload = {"channel": args.channel, "value": 1}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_GPIO_WRITE", payload))
        if ok:
            print_success(f"GPIO {args.channel}: HIGH")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_gpio_low(args: argparse.Namespace) -> int:
    """Set channel low."""
    payload = {"channel": args.channel, "value": 0}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_GPIO_WRITE", payload))
        if ok:
            print_success(f"GPIO {args.channel}: LOW")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_gpio_write(args: argparse.Namespace) -> int:
    """Write value to channel."""
    payload = {"channel": args.channel, "value": args.value}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_GPIO_WRITE", payload))
        if ok:
            state = "HIGH" if args.value else "LOW"
            print_success(f"GPIO {args.channel}: {state}")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_gpio_read(args: argparse.Namespace) -> int:
    """Read channel state."""
    payload = {"channel": args.channel}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_GPIO_READ", payload))
        if ok:
            print_info(f"GPIO {args.channel}: read request sent (check telemetry)")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_gpio_toggle(args: argparse.Namespace) -> int:
    """Toggle channel state."""
    payload = {"channel": args.channel}

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_GPIO_TOGGLE", payload))
        if ok:
            print_success(f"GPIO {args.channel}: toggled")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_gpio_blink(args: argparse.Namespace) -> int:
    """Blink channel."""
    console.print(f"[bold cyan]Blinking GPIO {args.channel}[/bold cyan]")
    console.print(f"  Count: {args.count}")
    console.print(f"  Interval: {args.interval}s")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    try:
        for i in range(args.count):
            # High
            payload = {"channel": args.channel, "value": 1}
            _run_async(_connect_and_run(args.port, "CMD_GPIO_WRITE", payload))
            time.sleep(args.interval / 2)

            # Low
            payload = {"channel": args.channel, "value": 0}
            _run_async(_connect_and_run(args.port, "CMD_GPIO_WRITE", payload))
            time.sleep(args.interval / 2)

        print_success(f"GPIO {args.channel}: blink complete")
    except KeyboardInterrupt:
        # Ensure low state on interrupt
        payload = {"channel": args.channel, "value": 0}
        _run_async(_connect_and_run(args.port, "CMD_GPIO_WRITE", payload))
        console.print("\n[dim]Blink interrupted[/dim]")
    except Exception as e:
        print_error(f"Error: {e}")
        return 1

    return 0
