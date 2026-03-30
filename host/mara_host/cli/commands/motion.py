# mara_host/cli/commands/motion.py
"""Motion control commands."""

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
    """Register motion command group."""
    motion_parser = subparsers.add_parser(
        "motion",
        help="Motion control",
        description="Control robot body velocity (differential drive)",
        aliases=["mov"],
    )

    motion_sub = motion_parser.add_subparsers(
        dest="motion_cmd",
        title="motion commands",
        metavar="<subcommand>",
    )

    # motion velocity
    vel_p = motion_sub.add_parser("velocity", help="Set body velocity", aliases=["vel"])
    vel_p.add_argument("vx", type=float, help="Linear velocity (m/s, positive=forward)")
    vel_p.add_argument("omega", type=float, help="Angular velocity (rad/s, positive=CCW)")
    add_port_arg(vel_p)
    vel_p.set_defaults(func=cmd_velocity)

    # motion forward
    fwd_p = motion_sub.add_parser("forward", help="Move forward", aliases=["fwd"])
    fwd_p.add_argument(
        "--speed",
        type=float,
        default=0.3,
        help="Forward speed in m/s (default: 0.3)",
    )
    add_port_arg(fwd_p)
    fwd_p.set_defaults(func=cmd_forward)

    # motion backward
    back_p = motion_sub.add_parser("backward", help="Move backward", aliases=["back"])
    back_p.add_argument(
        "--speed",
        type=float,
        default=0.3,
        help="Backward speed in m/s (default: 0.3)",
    )
    add_port_arg(back_p)
    back_p.set_defaults(func=cmd_backward)

    # motion left
    left_p = motion_sub.add_parser("left", help="Rotate left (CCW)")
    left_p.add_argument(
        "--speed",
        type=float,
        default=0.5,
        help="Rotation speed in rad/s (default: 0.5)",
    )
    add_port_arg(left_p)
    left_p.set_defaults(func=cmd_left)

    # motion right
    right_p = motion_sub.add_parser("right", help="Rotate right (CW)")
    right_p.add_argument(
        "--speed",
        type=float,
        default=0.5,
        help="Rotation speed in rad/s (default: 0.5)",
    )
    add_port_arg(right_p)
    right_p.set_defaults(func=cmd_right)

    # motion stop
    stop_p = motion_sub.add_parser("stop", help="Stop all motion")
    add_port_arg(stop_p)
    stop_p.set_defaults(func=cmd_stop)

    # motion limits
    limits_p = motion_sub.add_parser("limits", help="Set velocity limits")
    limits_p.add_argument(
        "--linear",
        type=float,
        help="Max linear velocity (m/s)",
    )
    limits_p.add_argument(
        "--angular",
        type=float,
        help="Max angular velocity (rad/s)",
    )
    add_port_arg(limits_p)
    limits_p.set_defaults(func=cmd_limits)

    # motion status
    status_p = motion_sub.add_parser("status", help="Show motion status")
    add_port_arg(status_p)
    status_p.set_defaults(func=cmd_status)

    # Default handler
    motion_parser.set_defaults(func=lambda args: cmd_help(motion_parser))


@run_with_context
async def cmd_velocity(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set body velocity."""
    result = await ctx.motion_service.set_velocity_reliable(args.vx, args.omega)

    if result.ok:
        print_success(f"Velocity: vx={args.vx:.2f} m/s, omega={args.omega:.2f} rad/s")
        return 0
    else:
        print_error(f"Failed to set velocity: {result.error}")
        return 1


@run_with_context
async def cmd_forward(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Move forward."""
    await ctx.motion_service.forward(args.speed)
    print_success(f"Moving forward at {args.speed} m/s")
    return 0


@run_with_context
async def cmd_backward(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Move backward."""
    await ctx.motion_service.backward(args.speed)
    print_success(f"Moving backward at {args.speed} m/s")
    return 0


@run_with_context
async def cmd_left(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Rotate left."""
    await ctx.motion_service.rotate_left(args.speed)
    print_success(f"Rotating left at {args.speed} rad/s")
    return 0


@run_with_context
async def cmd_right(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Rotate right."""
    await ctx.motion_service.rotate_right(args.speed)
    print_success(f"Rotating right at {args.speed} rad/s")
    return 0


@run_with_context
async def cmd_stop(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Stop all motion."""
    result = await ctx.motion_service.stop()

    if result.ok:
        print_success("Motion stopped")
        return 0
    else:
        print_error(f"Failed to stop: {result.error}")
        return 1


@run_with_context
async def cmd_limits(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set velocity limits."""
    if args.linear is None and args.angular is None:
        # Show current limits
        console.print(f"Linear limit: {ctx.motion_service.velocity_limit_linear:.2f} m/s")
        console.print(f"Angular limit: {ctx.motion_service.velocity_limit_angular:.2f} rad/s")
        return 0

    ctx.motion_service.set_limits(linear=args.linear, angular=args.angular)

    msg = "Limits updated:"
    if args.linear is not None:
        msg += f" linear={args.linear} m/s"
    if args.angular is not None:
        msg += f" angular={args.angular} rad/s"

    print_success(msg)
    return 0


@run_with_context
async def cmd_status(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Show motion status."""
    last_vel = ctx.motion_service.last_velocity

    table = Table(title="Motion Status", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Linear Velocity", f"{last_vel.vx:.3f} m/s")
    table.add_row("Angular Velocity", f"{last_vel.omega:.3f} rad/s")
    table.add_row("Linear Limit", f"{ctx.motion_service.velocity_limit_linear:.2f} m/s")
    table.add_row("Angular Limit", f"{ctx.motion_service.velocity_limit_angular:.2f} rad/s")
    table.add_row("Rate Limit", f"{ctx.motion_service.rate_limit_hz:.0f} Hz")

    console.print(table)
    return 0
