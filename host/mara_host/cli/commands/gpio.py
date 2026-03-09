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

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
<<<<<<< HEAD
from mara_host.cli.context import CLIContext, run_with_context
=======
from mara_host.cli.cli_config import get_serial_port as _get_port
>>>>>>> 6ae4738 (	modified:   host/mara_host/cli/cli_config.py)


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
            default=_get_port(),
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


@run_with_context
async def cmd_gpio_register(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Register GPIO channel."""
    result = await ctx.gpio_service.register(
        args.channel,
        args.pin,
        mode=args.mode,
    )

    if result.ok:
        print_success(f"GPIO channel {args.channel}: pin {args.pin} as {args.mode}")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_gpio_high(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set channel high."""
    result = await ctx.gpio_service.high(args.channel)

    if result.ok:
        print_success(f"GPIO {args.channel}: HIGH")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_gpio_low(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set channel low."""
    result = await ctx.gpio_service.low(args.channel)

    if result.ok:
        print_success(f"GPIO {args.channel}: LOW")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_gpio_write(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Write value to channel."""
    result = await ctx.gpio_service.write(args.channel, args.value)

    if result.ok:
        state = "HIGH" if args.value else "LOW"
        print_success(f"GPIO {args.channel}: {state}")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_gpio_read(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Read channel state."""
    result = await ctx.gpio_service.read(args.channel)

    if result.ok:
        print_info(f"GPIO {args.channel}: read request sent (check telemetry)")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_gpio_toggle(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Toggle channel state."""
    result = await ctx.gpio_service.toggle(args.channel)

    if result.ok:
        print_success(f"GPIO {args.channel}: toggled")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_gpio_blink(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Blink channel."""
    console.print(f"[bold cyan]Blinking GPIO {args.channel}[/bold cyan]")
    console.print(f"  Count: {args.count}")
    console.print(f"  Interval: {args.interval}s")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    try:
        for i in range(args.count):
            # High
            await ctx.gpio_service.high(args.channel)
            await asyncio.sleep(args.interval / 2)

            # Low
            await ctx.gpio_service.low(args.channel)
            await asyncio.sleep(args.interval / 2)

        print_success(f"GPIO {args.channel}: blink complete")
        return 0

    except KeyboardInterrupt:
        # Ensure low state on interrupt
        await ctx.gpio_service.low(args.channel)
        console.print("\n[dim]Blink interrupted[/dim]")
        return 0
    except Exception as e:
        print_error(f"Error: {e}")
        return 1
