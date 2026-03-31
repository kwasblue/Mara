# mara_host/cli/commands/run/shell/commands/telemetry.py
"""Telemetry, WiFi, and logging commands."""

import asyncio

from .registry import command
from mara_host.cli.console import console, print_success, print_error, print_info


@command("telem", "Telemetry: telem rate/interval ...", group="Telemetry")
async def cmd_telem(shell, args: list[str]) -> None:
    """Telemetry commands."""
    if not args:
        console.print("Usage:")
        console.print("  telem rate <hz>        Set telemetry rate")
        console.print("  telem interval <ms>    Set telemetry interval")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "rate" and len(args) >= 2:
        rate = int(args[1])
        await shell.client.send_reliable("CMD_TELEM_SET_RATE", {"rate_hz": rate})
        print_success(f"Telemetry rate set to {rate} Hz")
    elif action == "interval" and len(args) >= 2:
        interval = int(args[1])
        await shell.client.send_reliable("CMD_TELEM_SET_INTERVAL", {"interval_ms": interval})
        print_success(f"Telemetry interval set to {interval} ms")
    else:
        print_error(f"Unknown telem action: {args}")


@command("wifi", "WiFi: wifi scan/join/disconnect/status", group="Telemetry")
async def cmd_wifi(shell, args: list[str]) -> None:
    """WiFi commands."""
    if not args:
        console.print("Usage:")
        console.print("  wifi status            Get WiFi status")
        console.print("  wifi scan              Scan for networks")
        console.print("  wifi join <ssid> <pw>  Connect to network")
        console.print("  wifi disconnect        Disconnect from network")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "status":
        await shell.client.send_reliable("CMD_WIFI_STATUS", {})
        print_info("WiFi status requested (check events)")
    elif action == "scan":
        await shell.client.send_reliable("CMD_WIFI_SCAN", {})
        print_info("WiFi scan started (check events)")
    elif action == "join" and len(args) >= 3:
        ssid = args[1]
        password = args[2]
        await shell.client.send_reliable("CMD_WIFI_JOIN", {"ssid": ssid, "password": password})
        print_info(f"Connecting to WiFi '{ssid}'...")
    elif action == "disconnect":
        await shell.client.send_reliable("CMD_WIFI_DISCONNECT", {})
        print_success("WiFi disconnected")
    else:
        print_error(f"Unknown wifi action: {args}")


@command("log", "MCU logging: log level <level> or log <subsystem> <level>", group="Telemetry")
async def cmd_log(shell, args: list[str]) -> None:
    """MCU logging commands."""
    if not args:
        console.print("Usage:")
        console.print("  log level <level>              Set global MCU log level (debug/info/warn/error/off)")
        console.print("  log <subsystem> <level>        Set subsystem log level (e.g., log servo debug)")
        console.print("  log levels                     Get current log levels")
        console.print("  log clear                      Clear subsystem overrides")
        console.print()
        console.print("Subsystems: servo, motor, control, gpio, encoder, imu, safety, telem")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()

    # Global level: log level <level>
    if action == "level" and len(args) >= 2:
        level = args[1].lower()
        if level not in ("debug", "info", "warn", "error", "off"):
            print_error(f"Invalid level: {level}. Use: debug, info, warn, error, off")
            return
        await shell.client.send_reliable("CMD_SET_LOG_LEVEL", {"level": level})
        print_success(f"MCU global log level set to {level}")

    # Get levels: log levels
    elif action == "levels":
        response_future: asyncio.Future = asyncio.get_event_loop().create_future()

        def on_response(data: dict) -> None:
            if not response_future.done():
                response_future.set_result(data)

        shell.client.bus.subscribe("cmd.CMD_GET_LOG_LEVELS", on_response)

        try:
            ok, err = await shell.client.send_reliable("CMD_GET_LOG_LEVELS", {})
            if not ok:
                print_error(f"Failed to get log levels: {err}")
                return

            try:
                data = await asyncio.wait_for(response_future, timeout=2.0)
                console.print()
                console.print("[bold]MCU Log Levels:[/bold]")
                console.print(f"  Global: [green]{data.get('global', '?')}[/green]")
                subsystems = data.get("subsystems", {})
                if subsystems:
                    console.print("  Subsystem overrides:")
                    for sub, level in subsystems.items():
                        console.print(f"    {sub}: [cyan]{level}[/cyan]")
                else:
                    console.print("  [dim]No subsystem overrides[/dim]")
            except asyncio.TimeoutError:
                print_error("Log levels response timed out")
        finally:
            shell.client.bus.unsubscribe("cmd.CMD_GET_LOG_LEVELS", on_response)

    # Clear overrides: log clear
    elif action == "clear":
        await shell.client.send_reliable("CMD_CLEAR_SUBSYSTEM_LOG_LEVELS", {})
        print_success("Subsystem log level overrides cleared")

    # Subsystem level: log <subsystem> <level>
    elif len(args) >= 2:
        subsystem = args[0].lower()
        level = args[1].lower()
        if level not in ("debug", "info", "warn", "error", "off"):
            print_error(f"Invalid level: {level}. Use: debug, info, warn, error, off")
            return
        await shell.client.send_reliable("CMD_SET_SUBSYSTEM_LOG_LEVEL", {"subsystem": subsystem, "level": level})
        print_success(f"MCU {subsystem} log level set to {level}")

    else:
        print_error(f"Unknown log action: {args}")
