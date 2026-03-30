# mara_host/cli/commands/signal.py
"""Signal bus commands."""

import argparse

from rich.table import Table

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from mara_host.cli.context import CLIContext, run_with_context
from mara_host.cli.commands._common import add_port_arg, cmd_help


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register signal command group."""
    signal_parser = subparsers.add_parser(
        "signal",
        help="Signal bus operations",
        description="Manage signals in the MCU signal bus",
        aliases=["sig"],
    )

    signal_sub = signal_parser.add_subparsers(
        dest="signal_cmd",
        title="signal commands",
        metavar="<subcommand>",
    )

    # signal define
    define_p = signal_sub.add_parser("define", help="Define a new signal")
    define_p.add_argument("signal_id", type=int, help="Signal ID (0-255)")
    define_p.add_argument("name", help="Signal name")
    define_p.add_argument(
        "--kind",
        choices=["continuous", "discrete", "event"],
        default="continuous",
        help="Signal kind (default: continuous)",
    )
    define_p.add_argument(
        "--value",
        type=float,
        default=0.0,
        help="Initial value (default: 0.0)",
    )
    add_port_arg(define_p)
    define_p.set_defaults(func=cmd_define)

    # signal set
    set_p = signal_sub.add_parser("set", help="Set a signal value")
    set_p.add_argument("signal_id", type=int, help="Signal ID")
    set_p.add_argument("value", type=float, help="Value to set")
    add_port_arg(set_p)
    set_p.set_defaults(func=cmd_set)

    # signal get
    get_p = signal_sub.add_parser("get", help="Get a signal value")
    get_p.add_argument("signal_id", type=int, help="Signal ID")
    add_port_arg(get_p)
    get_p.set_defaults(func=cmd_get)

    # signal list
    list_p = signal_sub.add_parser("list", help="List all defined signals")
    add_port_arg(list_p)
    list_p.set_defaults(func=cmd_list)

    # signal delete
    delete_p = signal_sub.add_parser("delete", help="Delete a signal")
    delete_p.add_argument("signal_id", type=int, help="Signal ID to delete")
    add_port_arg(delete_p)
    delete_p.set_defaults(func=cmd_delete)

    # signal clear
    clear_p = signal_sub.add_parser("clear", help="Clear all signals")
    add_port_arg(clear_p)
    clear_p.set_defaults(func=cmd_clear)

    # Default handler
    signal_parser.set_defaults(func=lambda args: cmd_help(signal_parser))


@run_with_context
async def cmd_define(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Define a new signal."""
    result = await ctx.signal_service.define(
        signal_id=args.signal_id,
        name=args.name,
        kind=args.kind,
        initial_value=args.value,
    )

    if result.ok:
        print_success(f"Signal {args.signal_id} ({args.name}) defined")
        return 0
    else:
        print_error(f"Failed to define signal: {result.error}")
        return 1


@run_with_context
async def cmd_set(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set a signal value."""
    result = await ctx.signal_service.set(
        signal_id=args.signal_id,
        value=args.value,
    )

    if result.ok:
        print_success(f"Signal {args.signal_id} = {args.value}")
        return 0
    else:
        print_error(f"Failed to set signal: {result.error}")
        return 1


@run_with_context
async def cmd_get(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Get a signal value."""
    result = await ctx.signal_service.get(args.signal_id)

    if result.ok:
        data = result.data or {}
        value = data.get("value", 0.0)
        console.print(f"Signal {args.signal_id} = {value}")
        return 0
    else:
        print_error(f"Failed to get signal: {result.error}")
        return 1


@run_with_context
async def cmd_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """List all defined signals."""
    result = await ctx.signal_service.list()

    if result.ok:
        signals = ctx.signal_service.signals
        if not signals:
            console.print("No signals defined")
            return 0

        table = Table(title="Defined Signals")
        table.add_column("ID", style="cyan", justify="center")
        table.add_column("Name", style="green")
        table.add_column("Kind")
        table.add_column("Value", justify="right")

        for sig_id, signal in sorted(signals.items()):
            table.add_row(
                str(sig_id),
                signal.name,
                signal.kind.value,
                f"{signal.value:.4f}",
            )

        console.print(table)
        return 0
    else:
        print_error(f"Failed to list signals: {result.error}")
        return 1


@run_with_context
async def cmd_delete(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Delete a signal."""
    result = await ctx.signal_service.delete(args.signal_id)

    if result.ok:
        print_success(f"Signal {args.signal_id} deleted")
        return 0
    else:
        print_error(f"Failed to delete signal: {result.error}")
        return 1


@run_with_context
async def cmd_clear(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Clear all signals."""
    result = await ctx.signal_service.clear()

    if result.ok:
        print_success("All signals cleared")
        return 0
    else:
        print_error(f"Failed to clear signals: {result.error}")
        return 1
