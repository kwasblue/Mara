# mara_host/cli/commands/run/shell/commands/safety.py
"""Safety and state commands: arm, disarm, activate, deactivate, estop, state, safety."""

import asyncio

from .registry import command, alias
from mara_host.cli.console import console, print_success, print_error, print_info


@command("arm", "Arm the robot", group="Safety")
async def cmd_arm(shell, args: list[str]) -> None:
    """Arm the robot."""
    if not shell.require_connection():
        return
    await shell.client.cmd_arm()
    print_success("Robot armed")


@command("disarm", "Disarm the robot", group="Safety")
async def cmd_disarm(shell, args: list[str]) -> None:
    """Disarm the robot."""
    if not shell.require_connection():
        return
    await shell.client.cmd_disarm()
    print_success("Robot disarmed")


@command("activate", "Set mode to ACTIVE", group="Safety")
async def cmd_activate(shell, args: list[str]) -> None:
    """Set mode to ACTIVE."""
    if not shell.require_connection():
        return
    await shell.client.cmd_set_mode("ACTIVE")
    print_success("Mode set to ACTIVE")


# Alias for activate
alias("active", "activate")


@command("deactivate", "Set mode to IDLE", group="Safety")
async def cmd_deactivate(shell, args: list[str]) -> None:
    """Set mode to IDLE."""
    if not shell.require_connection():
        return
    await shell.client.send_reliable("CMD_DEACTIVATE", {})
    print_success("Mode set to IDLE")


# Alias for deactivate
alias("idle", "deactivate")


@command("estop", "Emergency stop", group="Safety")
async def cmd_estop(shell, args: list[str]) -> None:
    """Emergency stop."""
    if not shell.require_connection():
        return
    await shell.client.send_reliable("CMD_ESTOP", {})
    print_error("EMERGENCY STOP activated!")


@command("state", "Get robot state", group="Safety")
async def cmd_state(shell, args: list[str]) -> None:
    """Get robot state."""
    if not shell.require_connection():
        return

    # Setup response listener
    response_future: asyncio.Future = asyncio.get_event_loop().create_future()

    def on_response(data: dict) -> None:
        if not response_future.done():
            response_future.set_result(data)

    shell.client.bus.subscribe("cmd.CMD_GET_STATE", on_response)

    try:
        ok, err = await shell.client.send_reliable("CMD_GET_STATE", {})
        if not ok:
            print_error(f"Failed to get state: {err}")
            return

        # Wait for response
        try:
            data = await asyncio.wait_for(response_future, timeout=2.0)
            state = data.get("state", "?")
            armed = data.get("armed", "?")
            mode = data.get("mode", "?")

            console.print()
            console.print("[bold]Robot State:[/bold]")
            console.print(f"  State: [green]{state}[/green]")
            console.print(f"  Armed: [green]{armed}[/green]")
            console.print(f"  Mode:  [green]{mode}[/green]")

            # Show additional fields if present
            skip_fields = {"cmd", "ok", "seq", "src", "state", "armed", "mode", "error", "error_code"}
            extra = {k: v for k, v in data.items() if k not in skip_fields}
            if extra:
                for key, value in extra.items():
                    console.print(f"  {key}: [cyan]{value}[/cyan]")
        except asyncio.TimeoutError:
            print_error("State response timed out")
    finally:
        shell.client.bus.unsubscribe("cmd.CMD_GET_STATE", on_response)


@command("safety", "Safety timeouts: safety [on|off|status|set <host_ms> <motion_ms>]", group="Safety")
async def cmd_safety(shell, args: list[str]) -> None:
    """Safety timeout control."""
    if not args:
        console.print("Usage:")
        console.print("  safety status              Show current timeout settings")
        console.print("  safety on                  Enable timeouts (3000ms host, 500ms motion)")
        console.print("  safety off                 Disable timeouts (0ms = disabled)")
        console.print("  safety set <host> <motion> Set specific timeout values (ms)")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()

    if action == "status":
        # Get current timeout settings
        response_future: asyncio.Future = asyncio.get_event_loop().create_future()

        def on_response(data: dict) -> None:
            if not response_future.done():
                response_future.set_result(data)

        shell.client.bus.subscribe("cmd.CMD_GET_SAFETY_TIMEOUTS", on_response)

        try:
            ok, err = await shell.client.send_reliable("CMD_GET_SAFETY_TIMEOUTS", {})
            if not ok:
                print_error(f"Failed to get safety timeouts: {err}")
                return

            try:
                data = await asyncio.wait_for(response_future, timeout=2.0)
                console.print()
                console.print("[bold]Safety Timeouts:[/bold]")
                host_ms = data.get("host_timeout_ms", 0)
                motion_ms = data.get("motion_timeout_ms", 0)
                enabled = data.get("enabled", False)

                status = "[green]enabled[/green]" if enabled else "[yellow]disabled[/yellow]"
                console.print(f"  Status: {status}")
                console.print(f"  Host timeout:   [cyan]{host_ms}[/cyan] ms {'(disabled)' if host_ms == 0 else ''}")
                console.print(f"  Motion timeout: [cyan]{motion_ms}[/cyan] ms {'(disabled)' if motion_ms == 0 else ''}")
            except asyncio.TimeoutError:
                print_error("Safety timeout query timed out")
        finally:
            shell.client.bus.unsubscribe("cmd.CMD_GET_SAFETY_TIMEOUTS", on_response)

    elif action == "on":
        # Enable with default values
        ok, err = await shell.client.send_reliable("CMD_SET_SAFETY_TIMEOUTS", {
            "host_timeout_ms": 3000,
            "motion_timeout_ms": 500
        })
        if ok:
            print_success("Safety timeouts enabled (host=3000ms, motion=500ms)")
        else:
            print_error(f"Failed to enable timeouts: {err}")

    elif action == "off":
        # Disable (set to 0)
        ok, err = await shell.client.send_reliable("CMD_SET_SAFETY_TIMEOUTS", {
            "host_timeout_ms": 0,
            "motion_timeout_ms": 0
        })
        if ok:
            print_success("Safety timeouts disabled")
        else:
            print_error(f"Failed to disable timeouts: {err}")

    elif action == "set" and len(args) >= 3:
        host_ms = int(args[1])
        motion_ms = int(args[2])
        ok, err = await shell.client.send_reliable("CMD_SET_SAFETY_TIMEOUTS", {
            "host_timeout_ms": host_ms,
            "motion_timeout_ms": motion_ms
        })
        if ok:
            print_success(f"Safety timeouts set (host={host_ms}ms, motion={motion_ms}ms)")
        else:
            print_error(f"Failed to set timeouts: {err}")

    else:
        print_error(f"Unknown safety action: {args[0]}")
        console.print("Use: safety status | on | off | set <host_ms> <motion_ms>")
