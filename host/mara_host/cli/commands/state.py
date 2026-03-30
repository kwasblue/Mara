# mara_host/cli/commands/state.py
"""Robot state control commands."""

import argparse

from rich.table import Table

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
)
from mara_host.cli.context import CLIContext, run_with_context
from mara_host.cli.commands._common import add_port_arg, cmd_help


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register state command group."""
    state_parser = subparsers.add_parser(
        "state",
        help="Robot state control",
        description="Control robot state machine (arm, disarm, activate, estop)",
        aliases=["st"],
    )

    state_sub = state_parser.add_subparsers(
        dest="state_cmd",
        title="state commands",
        metavar="<subcommand>",
    )

    # state status
    status_p = state_sub.add_parser("status", help="Show current robot state")
    add_port_arg(status_p)
    status_p.set_defaults(func=cmd_status)

    # state arm
    arm_p = state_sub.add_parser("arm", help="Arm the robot (enable motors)")
    add_port_arg(arm_p)
    arm_p.set_defaults(func=cmd_arm)

    # state disarm
    disarm_p = state_sub.add_parser("disarm", help="Disarm the robot (disable motors)")
    add_port_arg(disarm_p)
    disarm_p.set_defaults(func=cmd_disarm)

    # state activate
    activate_p = state_sub.add_parser(
        "activate", help="Activate the robot (enable motion commands)"
    )
    add_port_arg(activate_p)
    activate_p.set_defaults(func=cmd_activate)

    # state deactivate
    deactivate_p = state_sub.add_parser(
        "deactivate", help="Deactivate the robot (stop accepting motion)"
    )
    add_port_arg(deactivate_p)
    deactivate_p.set_defaults(func=cmd_deactivate)

    # state estop
    estop_p = state_sub.add_parser(
        "estop", help="Emergency stop (immediately halt all motion)"
    )
    add_port_arg(estop_p)
    estop_p.set_defaults(func=cmd_estop)

    # state clear-estop
    clear_p = state_sub.add_parser(
        "clear-estop", help="Clear emergency stop condition"
    )
    add_port_arg(clear_p)
    clear_p.set_defaults(func=cmd_clear_estop)

    # state stop
    stop_p = state_sub.add_parser(
        "stop", help="Soft stop (zero velocities, keep state)"
    )
    add_port_arg(stop_p)
    stop_p.set_defaults(func=cmd_stop)

    # Default handler
    state_parser.set_defaults(func=lambda args: cmd_help(state_parser))


@run_with_context
async def cmd_status(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Get current robot state."""
    result = await ctx.state_service.get_state()

    if result.ok:
        data = result.data or {}
        mode = data.get("mode", "UNKNOWN")

        # Color based on state
        if mode == "ACTIVE":
            mode_styled = f"[bold green]{mode}[/bold green]"
        elif mode == "ARMED":
            mode_styled = f"[bold yellow]{mode}[/bold yellow]"
        elif mode == "ESTOP":
            mode_styled = f"[bold red]{mode}[/bold red]"
        else:
            mode_styled = f"[dim]{mode}[/dim]"

        table = Table(title="Robot State", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Mode", mode_styled)
        table.add_row("Armed", "Yes" if data.get("armed") else "No")
        table.add_row("Active", "Yes" if data.get("active") else "No")
        table.add_row("E-Stop", "[red]Yes[/red]" if data.get("estop") else "No")

        console.print(table)
        return 0
    else:
        print_error(f"Failed to get state: {result.error}")
        return 1


@run_with_context
async def cmd_arm(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Arm the robot."""
    # Note: CLIContext auto-arms on connect, but this allows re-arming after disarm
    result = await ctx.state_service.arm()

    if result.ok:
        print_success("Robot armed")
        return 0
    else:
        print_error(f"Failed to arm: {result.error}")
        return 1


@run_with_context
async def cmd_disarm(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Disarm the robot."""
    result = await ctx.state_service.disarm()

    if result.ok:
        print_success("Robot disarmed")
        return 0
    else:
        print_error(f"Failed to disarm: {result.error}")
        return 1


@run_with_context
async def cmd_activate(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Activate the robot."""
    result = await ctx.state_service.activate()

    if result.ok:
        print_success("Robot activated - motion commands enabled")
        return 0
    else:
        print_error(f"Failed to activate: {result.error}")
        return 1


@run_with_context
async def cmd_deactivate(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Deactivate the robot."""
    result = await ctx.state_service.deactivate()

    if result.ok:
        print_success("Robot deactivated")
        return 0
    else:
        print_error(f"Failed to deactivate: {result.error}")
        return 1


@run_with_context
async def cmd_estop(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Emergency stop the robot."""
    result = await ctx.state_service.estop()

    print_warning("EMERGENCY STOP activated")
    if result.error:
        console.print(f"  Note: {result.error}")
    return 0


@run_with_context
async def cmd_clear_estop(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Clear emergency stop."""
    result = await ctx.state_service.clear_estop()

    if result.ok:
        print_success("Emergency stop cleared")
        return 0
    else:
        print_error(f"Failed to clear E-STOP: {result.error}")
        return 1


@run_with_context
async def cmd_stop(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Soft stop - zero velocities."""
    result = await ctx.state_service.stop()

    if result.ok:
        print_success("Motion stopped")
        return 0
    else:
        print_error(f"Failed to stop: {result.error}")
        return 1
