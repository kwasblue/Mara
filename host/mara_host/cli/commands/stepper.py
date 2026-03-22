# mara_host/cli/commands/stepper.py
"""Stepper motor direct control commands.

Examples:
    mara stepper enable 0             # Enable stepper 0
    mara stepper disable 0            # Disable stepper 0
    mara stepper move 0 200           # Move 200 steps
    mara stepper move 0 -100          # Move -100 steps (reverse)
    mara stepper degrees 0 90         # Rotate 90 degrees
    mara stepper revs 0 2             # Rotate 2 full revolutions
    mara stepper stop 0               # Stop immediately
    mara stepper home 0               # Home stepper (if limit switch)
"""

import argparse

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from mara_host.cli.context import CLIContext, run_with_context


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register stepper control commands."""
    step_parser = subparsers.add_parser(
        "stepper",
        help="Stepper motor direct control",
        description="Control stepper motors directly",
        aliases=["step"],
    )

    step_sub = step_parser.add_subparsers(
        dest="stepper_cmd",
        title="stepper commands",
        metavar="<subcommand>",
    )

    def add_port_arg(parser):
        parser.add_argument(
            "-p", "--port",
            default="/dev/cu.usbserial-0001",
            help="Serial port",
        )

    # stepper enable <id>
    enable_p = step_sub.add_parser(
        "enable",
        help="Enable stepper motor (energize coils)",
    )
    enable_p.add_argument("id", type=int, help="Stepper ID (0-3)")
    add_port_arg(enable_p)
    enable_p.set_defaults(func=cmd_stepper_enable)

    # stepper disable <id>
    disable_p = step_sub.add_parser(
        "disable",
        help="Disable stepper motor (release coils)",
    )
    disable_p.add_argument("id", type=int, help="Stepper ID")
    add_port_arg(disable_p)
    disable_p.set_defaults(func=cmd_stepper_disable)

    # stepper move <id> <steps>
    move_p = step_sub.add_parser(
        "move",
        help="Move relative number of steps",
    )
    move_p.add_argument("id", type=int, help="Stepper ID")
    move_p.add_argument("steps", type=int, help="Number of steps (negative for reverse)")
    move_p.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speed in revolutions per second (default: 1.0)",
    )
    add_port_arg(move_p)
    move_p.set_defaults(func=cmd_stepper_move)

    # stepper degrees <id> <angle>
    deg_p = step_sub.add_parser(
        "degrees",
        help="Rotate by angle in degrees",
    )
    deg_p.add_argument("id", type=int, help="Stepper ID")
    deg_p.add_argument("angle", type=float, help="Angle in degrees")
    deg_p.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speed in RPS (default: 1.0)",
    )
    add_port_arg(deg_p)
    deg_p.set_defaults(func=cmd_stepper_degrees)

    # stepper revs <id> <revolutions>
    revs_p = step_sub.add_parser(
        "revs",
        help="Rotate by number of revolutions",
    )
    revs_p.add_argument("id", type=int, help="Stepper ID")
    revs_p.add_argument("revolutions", type=float, help="Number of revolutions")
    revs_p.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speed in RPS (default: 1.0)",
    )
    add_port_arg(revs_p)
    revs_p.set_defaults(func=cmd_stepper_revs)

    # stepper stop <id>
    stop_p = step_sub.add_parser(
        "stop",
        help="Stop stepper immediately",
    )
    stop_p.add_argument("id", type=int, help="Stepper ID")
    add_port_arg(stop_p)
    stop_p.set_defaults(func=cmd_stepper_stop)

    # stepper position <id>
    pos_p = step_sub.add_parser(
        "position",
        help="Get current position",
    )
    pos_p.add_argument("id", type=int, help="Stepper ID")
    add_port_arg(pos_p)
    pos_p.set_defaults(func=cmd_stepper_position)

    # stepper reset <id>
    reset_p = step_sub.add_parser(
        "reset",
        help="Reset position counter to zero",
    )
    reset_p.add_argument("id", type=int, help="Stepper ID")
    add_port_arg(reset_p)
    reset_p.set_defaults(func=cmd_stepper_reset)

    step_parser.set_defaults(func=lambda args: cmd_help(step_parser))


def cmd_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


@run_with_context
async def cmd_stepper_enable(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Enable stepper."""
    result = await ctx.stepper_service.enable(args.id)

    if result.ok:
        print_success(f"Stepper {args.id}: enabled")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_stepper_disable(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Disable stepper."""
    result = await ctx.stepper_service.disable(args.id)

    if result.ok:
        print_success(f"Stepper {args.id}: disabled")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_stepper_move(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Move stepper by steps."""
    direction = "forward" if args.steps > 0 else "reverse"

    result = await ctx.stepper_service.move_relative(
        args.id,
        args.steps,
        speed_rps=args.speed,
    )

    if result.ok:
        print_success(f"Stepper {args.id}: moving {abs(args.steps)} steps {direction}")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_stepper_degrees(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Rotate stepper by degrees."""
    result = await ctx.stepper_service.move_degrees(
        args.id,
        args.angle,
        speed_rps=args.speed,
    )

    if result.ok:
        print_success(f"Stepper {args.id}: rotating {args.angle}\u00b0")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_stepper_revs(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Rotate stepper by revolutions."""
    result = await ctx.stepper_service.move_revolutions(
        args.id,
        args.revolutions,
        speed_rps=args.speed,
    )

    if result.ok:
        print_success(f"Stepper {args.id}: rotating {args.revolutions} revolutions")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_stepper_stop(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Stop stepper."""
    result = await ctx.stepper_service.stop(args.id)

    if result.ok:
        print_success(f"Stepper {args.id}: stopped")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_stepper_position(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Get stepper position."""
    result = await ctx.stepper_service.get_position(args.id)

    if result.ok:
        print_info(f"Stepper {args.id}: position request sent")
        console.print("[dim]Check telemetry stream for position data[/dim]")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_stepper_reset(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Reset stepper position counter."""
    result = await ctx.stepper_service.reset_position(args.id)

    if result.ok:
        print_success(f"Stepper {args.id}: position reset to 0")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1
