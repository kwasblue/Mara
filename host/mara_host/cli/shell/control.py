# mara_host/cli/commands/run/shell/commands/control.py
"""Control graph and observer commands."""

from .registry import command
from mara_host.cli.console import console, print_success, print_error, print_info


@command("ctrl", "Control graph: ctrl status/enable/disable/clear ...", group="Control")
async def cmd_ctrl(shell, args: list[str]) -> None:
    """Control graph commands."""
    if not args:
        console.print("Usage:")
        console.print("  ctrl status            Get control graph status")
        console.print("  ctrl enable            Enable control graph")
        console.print("  ctrl disable           Disable control graph")
        console.print("  ctrl clear             Clear control graph")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "status":
        await shell.client.send_reliable("CMD_CTRL_GRAPH_STATUS", {})
        print_info("Control graph status requested (check events)")
    elif action == "enable":
        await shell.client.send_reliable("CMD_CTRL_GRAPH_ENABLE", {})
        print_success("Control graph enabled")
    elif action == "disable":
        await shell.client.send_reliable("CMD_CTRL_GRAPH_DISABLE", {})
        print_success("Control graph disabled")
    elif action == "clear":
        await shell.client.send_reliable("CMD_CTRL_GRAPH_CLEAR", {})
        print_success("Control graph cleared")
    else:
        print_error(f"Unknown ctrl action: {args}")


@command("observer", "Observer: observer config/enable/disable/status ...", group="Control")
async def cmd_observer(shell, args: list[str]) -> None:
    """Observer commands."""
    if not args:
        console.print("Usage:")
        console.print("  observer status            Get observer status")
        console.print("  observer enable <id>       Enable observer")
        console.print("  observer disable <id>      Disable observer")
        console.print("  observer reset <id>        Reset observer")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "status":
        await shell.client.send_reliable("CMD_OBSERVER_STATUS", {})
        print_info("Observer status requested (check events)")
    elif action == "enable" and len(args) >= 2:
        observer_id = int(args[1])
        await shell.client.send_reliable("CMD_OBSERVER_ENABLE", {"observer_id": observer_id, "enable": True})
        print_success(f"Observer {observer_id} enabled")
    elif action == "disable" and len(args) >= 2:
        observer_id = int(args[1])
        await shell.client.send_reliable("CMD_OBSERVER_ENABLE", {"observer_id": observer_id, "enable": False})
        print_success(f"Observer {observer_id} disabled")
    elif action == "reset" and len(args) >= 2:
        observer_id = int(args[1])
        await shell.client.send_reliable("CMD_OBSERVER_RESET", {"observer_id": observer_id})
        print_success(f"Observer {observer_id} reset")
    else:
        print_error(f"Unknown observer action: {args}")
