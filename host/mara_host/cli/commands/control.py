# mara_host/cli/commands/control.py
"""Control system commands for MARA CLI.

Commands for signal bus and observer/controller slot management.
"""

import argparse
import asyncio


from mara_host.cli.console import (
    console,
    print_success,
    print_error,
)


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

    # ==================== Signal Bus Commands ====================

    # signal list
    sig_list_p = ctrl_sub.add_parser(
        "signals",
        help="List all signals in the signal bus",
    )
    sig_list_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port (default: /dev/cu.usbserial-0001)",
    )
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
    sig_def_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port",
    )
    sig_def_p.set_defaults(func=cmd_signal_define)

    # signal set
    sig_set_p = ctrl_sub.add_parser(
        "signal-set",
        help="Set a signal value",
    )
    sig_set_p.add_argument("id", type=int, help="Signal ID")
    sig_set_p.add_argument("value", type=float, help="Value to set")
    sig_set_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port",
    )
    sig_set_p.set_defaults(func=cmd_signal_set)

    # signal clear
    sig_clear_p = ctrl_sub.add_parser(
        "signal-clear",
        help="Clear all signals",
    )
    sig_clear_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port",
    )
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
    ctrl_cfg_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port",
    )
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
    ctrl_en_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port",
    )
    ctrl_en_p.set_defaults(func=cmd_controller_enable)

    # controller set-param
    ctrl_param_p = ctrl_sub.add_parser(
        "controller-param",
        help="Set controller parameters",
    )
    ctrl_param_p.add_argument("slot", type=int, help="Slot number (0-7)")
    ctrl_param_p.add_argument("key", help="Parameter key (e.g., kp, ki, kd)")
    ctrl_param_p.add_argument("value", type=float, help="Parameter value")
    ctrl_param_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port",
    )
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
    obs_cfg_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port",
    )
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
    obs_en_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port",
    )
    obs_en_p.set_defaults(func=cmd_observer_enable)

    # observer reset
    obs_reset_p = ctrl_sub.add_parser(
        "observer-reset",
        help="Reset an observer slot",
    )
    obs_reset_p.add_argument("slot", type=int, help="Slot number (0-7)")
    obs_reset_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port",
    )
    obs_reset_p.set_defaults(func=cmd_observer_reset)

    # Default
    ctrl_parser.set_defaults(func=lambda args: cmd_help(ctrl_parser))


def cmd_help(parser: argparse.ArgumentParser) -> int:
    """Show help for control commands."""
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


# ==================== Signal Commands ====================

def cmd_signals_list(args: argparse.Namespace) -> int:
    """List all signals."""
    port = args.port

    console.print()
    console.print("[bold cyan]Signal Bus[/bold cyan]")
    console.print()

    try:
        ok, error = _run_async(_connect_and_run(port, "CMD_CTRL_SIGNALS_LIST", {}))
        if ok:
            print_success("Signal list requested (check telemetry for response)")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_signal_define(args: argparse.Namespace) -> int:
    """Define a new signal."""
    payload = {
        "signal_id": args.id,
        "name": args.name,
        "signal_kind": args.kind,
        "initial_value": args.initial,
    }

    console.print()
    console.print(f"[bold cyan]Defining Signal {args.id}[/bold cyan]")
    console.print(f"  Name: {args.name}")
    console.print(f"  Kind: {args.kind}")
    console.print(f"  Initial: {args.initial}")
    console.print()

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_CTRL_SIGNAL_DEFINE", payload))
        if ok:
            print_success(f"Signal {args.id} ({args.name}) defined")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_signal_set(args: argparse.Namespace) -> int:
    """Set a signal value."""
    payload = {
        "signal_id": args.id,
        "value": args.value,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_CTRL_SIGNAL_SET", payload))
        if ok:
            print_success(f"Signal {args.id} = {args.value}")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_signals_clear(args: argparse.Namespace) -> int:
    """Clear all signals."""
    console.print()

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_CTRL_SIGNALS_CLEAR", {}))
        if ok:
            print_success("All signals cleared")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


# ==================== Controller Commands ====================

def cmd_controller_config(args: argparse.Namespace) -> int:
    """Configure a controller slot."""
    payload = {
        "slot": args.slot,
        "controller_type": args.type,
        "rate_hz": args.rate_hz,
    }

    if args.ref_id is not None:
        payload["ref_id"] = args.ref_id
    if args.meas_id is not None:
        payload["meas_id"] = args.meas_id
    if args.out_id is not None:
        payload["out_id"] = args.out_id

    console.print()
    console.print(f"[bold cyan]Configuring Controller Slot {args.slot}[/bold cyan]")
    console.print(f"  Type: {args.type}")
    console.print(f"  Rate: {args.rate_hz} Hz")
    console.print()

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_CTRL_SLOT_CONFIG", payload))
        if ok:
            print_success(f"Controller slot {args.slot} configured")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_controller_enable(args: argparse.Namespace) -> int:
    """Enable or disable a controller slot."""
    enable = not args.disable
    payload = {
        "slot": args.slot,
        "enable": enable,
    }

    action = "Enabling" if enable else "Disabling"

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_CTRL_SLOT_ENABLE", payload))
        if ok:
            print_success(f"Controller slot {args.slot} {'enabled' if enable else 'disabled'}")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_controller_param(args: argparse.Namespace) -> int:
    """Set controller parameter."""
    payload = {
        "slot": args.slot,
        "key": args.key,
        "value": args.value,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_CTRL_SLOT_SET_PARAM", payload))
        if ok:
            print_success(f"Slot {args.slot}: {args.key} = {args.value}")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


# ==================== Observer Commands ====================

def cmd_observer_config(args: argparse.Namespace) -> int:
    """Configure an observer slot."""
    payload = {
        "slot": args.slot,
        "observer_type": args.type,
        "rate_hz": args.rate_hz,
    }

    console.print()
    console.print(f"[bold cyan]Configuring Observer Slot {args.slot}[/bold cyan]")
    console.print(f"  Type: {args.type}")
    console.print(f"  Rate: {args.rate_hz} Hz")
    console.print()

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_OBSERVER_CONFIG", payload))
        if ok:
            print_success(f"Observer slot {args.slot} configured")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_observer_enable(args: argparse.Namespace) -> int:
    """Enable or disable an observer slot."""
    enable = not args.disable
    payload = {
        "slot": args.slot,
        "enable": enable,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_OBSERVER_ENABLE", payload))
        if ok:
            print_success(f"Observer slot {args.slot} {'enabled' if enable else 'disabled'}")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0


def cmd_observer_reset(args: argparse.Namespace) -> int:
    """Reset an observer slot."""
    payload = {
        "slot": args.slot,
    }

    try:
        ok, error = _run_async(_connect_and_run(args.port, "CMD_OBSERVER_RESET", payload))
        if ok:
            print_success(f"Observer slot {args.slot} reset")
        else:
            print_error(f"Failed: {error}")
            return 1
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    return 0
