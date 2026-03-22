# mara_host/cli/commands/control.py
"""Control system commands for MARA CLI.

Commands for signal bus and observer/controller slot management.
"""

import argparse

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
)
from mara_host.cli.context import CLIContext, run_with_context


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register control system commands."""
    ctrl_parser = subparsers.add_parser(
        "control",
        help="Control system management (signals, controllers, observers)",
        description="Manage signal bus and control system slots",
        aliases=["ctrl"],
    )

    ctrl_sub = ctrl_parser.add_subparsers(
        dest="ctrl_cmd",
        title="control commands",
        metavar="<subcommand>",
    )

    def add_port_arg(parser):
        parser.add_argument(
            "-p", "--port",
            default="/dev/cu.usbserial-0001",
            help="Serial port (default: /dev/cu.usbserial-0001)",
        )

    # ==================== Signal Bus Commands ====================

    # signal list
    sig_list_p = ctrl_sub.add_parser(
        "signals",
        help="List all signals in the signal bus",
    )
    add_port_arg(sig_list_p)
    sig_list_p.set_defaults(func=cmd_signals_list)

    # signal define
    sig_def_p = ctrl_sub.add_parser(
        "signal-define",
        help="Define a new signal",
    )
    sig_def_p.add_argument("id", type=int, help="Signal ID (0-255)")
    sig_def_p.add_argument("name", help="Signal name")
    sig_def_p.add_argument(
        "-k", "--kind",
        choices=["continuous", "discrete", "event"],
        default="continuous",
        help="Signal kind (default: continuous)",
    )
    sig_def_p.add_argument(
        "-v", "--initial",
        type=float,
        default=0.0,
        help="Initial value (default: 0.0)",
    )
    add_port_arg(sig_def_p)
    sig_def_p.set_defaults(func=cmd_signal_define)

    # signal set
    sig_set_p = ctrl_sub.add_parser(
        "signal-set",
        help="Set a signal value",
    )
    sig_set_p.add_argument("id", type=int, help="Signal ID")
    sig_set_p.add_argument("value", type=float, help="Value to set")
    add_port_arg(sig_set_p)
    sig_set_p.set_defaults(func=cmd_signal_set)

    # signal clear
    sig_clear_p = ctrl_sub.add_parser(
        "signal-clear",
        help="Clear all signals",
    )
    add_port_arg(sig_clear_p)
    sig_clear_p.set_defaults(func=cmd_signals_clear)

    # ==================== Controller Slot Commands ====================

    # controller config
    ctrl_cfg_p = ctrl_sub.add_parser(
        "controller-config",
        help="Configure a controller slot",
    )
    ctrl_cfg_p.add_argument("slot", type=int, help="Slot number (0-7)")
    ctrl_cfg_p.add_argument(
        "-t", "--type",
        choices=["PID", "STATE_SPACE"],
        default="PID",
        help="Controller type (default: PID)",
    )
    ctrl_cfg_p.add_argument(
        "--ref-id", type=int,
        help="Reference signal ID",
    )
    ctrl_cfg_p.add_argument(
        "--meas-id", type=int,
        help="Measurement signal ID",
    )
    ctrl_cfg_p.add_argument(
        "--out-id", type=int,
        help="Output signal ID",
    )
    ctrl_cfg_p.add_argument(
        "--rate-hz", type=int, default=100,
        help="Control rate in Hz (default: 100)",
    )
    add_port_arg(ctrl_cfg_p)
    ctrl_cfg_p.set_defaults(func=cmd_controller_config)

    # controller enable
    ctrl_en_p = ctrl_sub.add_parser(
        "controller-enable",
        help="Enable or disable a controller slot",
    )
    ctrl_en_p.add_argument("slot", type=int, help="Slot number (0-7)")
    ctrl_en_p.add_argument(
        "--disable",
        action="store_true",
        help="Disable the slot (default: enable)",
    )
    add_port_arg(ctrl_en_p)
    ctrl_en_p.set_defaults(func=cmd_controller_enable)

    # controller set-param
    ctrl_param_p = ctrl_sub.add_parser(
        "controller-param",
        help="Set controller parameters",
    )
    ctrl_param_p.add_argument("slot", type=int, help="Slot number (0-7)")
    ctrl_param_p.add_argument("key", help="Parameter key (e.g., kp, ki, kd)")
    ctrl_param_p.add_argument("value", type=float, help="Parameter value")
    add_port_arg(ctrl_param_p)
    ctrl_param_p.set_defaults(func=cmd_controller_param)

    # ==================== Observer Slot Commands ====================

    # observer config
    obs_cfg_p = ctrl_sub.add_parser(
        "observer-config",
        help="Configure an observer slot",
    )
    obs_cfg_p.add_argument("slot", type=int, help="Slot number (0-7)")
    obs_cfg_p.add_argument(
        "-t", "--type",
        choices=["KALMAN", "LUENBERGER", "EKF"],
        default="KALMAN",
        help="Observer type (default: KALMAN)",
    )
    obs_cfg_p.add_argument(
        "--rate-hz", type=int, default=100,
        help="Update rate in Hz (default: 100)",
    )
    add_port_arg(obs_cfg_p)
    obs_cfg_p.set_defaults(func=cmd_observer_config)

    # observer enable
    obs_en_p = ctrl_sub.add_parser(
        "observer-enable",
        help="Enable or disable an observer slot",
    )
    obs_en_p.add_argument("slot", type=int, help="Slot number (0-7)")
    obs_en_p.add_argument(
        "--disable",
        action="store_true",
        help="Disable the slot (default: enable)",
    )
    add_port_arg(obs_en_p)
    obs_en_p.set_defaults(func=cmd_observer_enable)

    # observer reset
    obs_reset_p = ctrl_sub.add_parser(
        "observer-reset",
        help="Reset an observer slot",
    )
    obs_reset_p.add_argument("slot", type=int, help="Slot number (0-7)")
    add_port_arg(obs_reset_p)
    obs_reset_p.set_defaults(func=cmd_observer_reset)

    # Default
    ctrl_parser.set_defaults(func=lambda args: cmd_help(ctrl_parser))


def cmd_help(parser: argparse.ArgumentParser) -> int:
    """Show help for control commands."""
    parser.print_help()
    return 0


# ==================== Signal Commands ====================

@run_with_context
async def cmd_signals_list(args: argparse.Namespace, ctx: CLIContext) -> int:
    """List all signals."""
    console.print()
    console.print("[bold cyan]Signal Bus[/bold cyan]")
    console.print()

    result = await ctx.controller_service.signals_list()

    if result.ok:
        print_success("Signal list requested (check telemetry for response)")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_signal_define(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Define a new signal."""
    console.print()
    console.print(f"[bold cyan]Defining Signal {args.id}[/bold cyan]")
    console.print(f"  Name: {args.name}")
    console.print(f"  Kind: {args.kind}")
    console.print(f"  Initial: {args.initial}")
    console.print()

    result = await ctx.controller_service.signal_define(
        args.id,
        args.name,
        kind=args.kind,
        initial_value=args.initial,
    )

    if result.ok:
        print_success(f"Signal {args.id} ({args.name}) defined")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_signal_set(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set a signal value."""
    result = await ctx.controller_service.signal_set(args.id, args.value)

    if result.ok:
        print_success(f"Signal {args.id} = {args.value}")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_signals_clear(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Clear all signals."""
    console.print()

    result = await ctx.controller_service.signals_clear()

    if result.ok:
        print_success("All signals cleared")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


# ==================== Controller Commands ====================

@run_with_context
async def cmd_controller_config(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Configure a controller slot."""
    console.print()
    console.print(f"[bold cyan]Configuring Controller Slot {args.slot}[/bold cyan]")
    console.print(f"  Type: {args.type}")
    console.print(f"  Rate: {args.rate_hz} Hz")
    console.print()

    result = await ctx.controller_service.controller_config(
        args.slot,
        controller_type=args.type,
        ref_id=args.ref_id,
        meas_id=args.meas_id,
        out_id=args.out_id,
        rate_hz=args.rate_hz,
    )

    if result.ok:
        print_success(f"Controller slot {args.slot} configured")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_controller_enable(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Enable or disable a controller slot."""
    enable = not args.disable

    result = await ctx.controller_service.controller_enable(args.slot, enable)

    if result.ok:
        print_success(f"Controller slot {args.slot} {'enabled' if enable else 'disabled'}")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_controller_param(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set controller parameter."""
    result = await ctx.controller_service.controller_set_param(
        args.slot,
        args.key,
        args.value,
    )

    if result.ok:
        print_success(f"Slot {args.slot}: {args.key} = {args.value}")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


# ==================== Observer Commands ====================

@run_with_context
async def cmd_observer_config(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Configure an observer slot."""
    console.print()
    console.print(f"[bold cyan]Configuring Observer Slot {args.slot}[/bold cyan]")
    console.print(f"  Type: {args.type}")
    console.print(f"  Rate: {args.rate_hz} Hz")
    console.print()

    result = await ctx.controller_service.observer_config(
        args.slot,
        observer_type=args.type,
        rate_hz=args.rate_hz,
    )

    if result.ok:
        print_success(f"Observer slot {args.slot} configured")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_observer_enable(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Enable or disable an observer slot."""
    enable = not args.disable

    result = await ctx.controller_service.observer_enable(args.slot, enable)

    if result.ok:
        print_success(f"Observer slot {args.slot} {'enabled' if enable else 'disabled'}")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_observer_reset(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Reset an observer slot."""
    result = await ctx.controller_service.observer_reset(args.slot)

    if result.ok:
        print_success(f"Observer slot {args.slot} reset")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1
