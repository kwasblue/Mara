# mara_host/cli/commands/run/shell/commands/info.py
"""Info commands: info, version, identity, rates."""

import asyncio

from .registry import command
from mara_host.cli.console import console, print_success, print_error, print_info


@command("info", "Request robot info", group="Info")
async def cmd_info(shell, args: list[str]) -> None:
    """Request robot info."""
    if not shell.require_connection():
        return
    await shell.client.cmd_get_info()
    print_info("Info requested (check events)")


@command("version", "Show host version", group="Info")
async def cmd_version(shell, args: list[str]) -> None:
    """Show version."""
    console.print()
    console.print("[bold]MARA Shell[/bold]")
    from mara_host import __version__
    console.print(f"  Host version: [green]{__version__}[/green]")
    print_info("Use 'identity' to get MCU build info")


@command("identity", "Get MCU build identity and features", group="Info")
async def cmd_identity(shell, args: list[str]) -> None:
    """Get MCU build identity and features."""
    if not shell.require_connection():
        return

    console.print()
    console.print("[bold]Querying MCU identity...[/bold]")

    # Use asyncio.Future to wait for response
    response_future: asyncio.Future = asyncio.get_event_loop().create_future()

    def on_identity_response(data: dict) -> None:
        if not response_future.done():
            response_future.set_result(data)

    # Subscribe to the specific command response topic
    shell.client.bus.subscribe("cmd.CMD_GET_IDENTITY", on_identity_response)

    try:
        # Send identity request
        await shell.client.cmd_get_identity()

        # Wait for response with timeout
        try:
            data = await asyncio.wait_for(response_future, timeout=2.0)
        except asyncio.TimeoutError:
            print_error("Identity request timed out")
            return

        # Parse and display the response (data is flat, not wrapped in "payload")
        console.print()
        console.print("[bold cyan]MCU Identity:[/bold cyan]")
        console.print(f"  Firmware:  [green]{data.get('firmware', 'unknown')}[/green]")
        console.print(f"  Board:     {data.get('board', 'unknown')}")
        console.print(f"  Name:      {data.get('name', 'unknown')}")
        console.print(f"  Protocol:  v{data.get('protocol', '?')}")
        console.print(f"  Schema:    v{data.get('schema', '?')}")
        console.print(f"  Caps:      0x{data.get('caps', 0):08X}")

        features = data.get("features", [])
        if features:
            console.print()
            console.print("[bold cyan]Enabled Features:[/bold cyan]")
            for feature in sorted(features):
                console.print(f"  [green]v[/green] {feature}")
        else:
            console.print()
            console.print("[dim]No features list (check caps bitmask)[/dim]")

    finally:
        # Unsubscribe (EventBus may not have unsubscribe, but try)
        pass


@command("rates", "Get loop rates", group="Info")
async def cmd_rates(shell, args: list[str]) -> None:
    """Get loop rates."""
    if not shell.require_connection():
        return

    # Setup response listener
    response_future: asyncio.Future = asyncio.get_event_loop().create_future()

    def on_response(data: dict) -> None:
        if not response_future.done():
            response_future.set_result(data)

    shell.client.bus.subscribe("cmd.CMD_GET_RATES", on_response)

    try:
        ok, err = await shell.client.send_reliable("CMD_GET_RATES", {})
        if not ok:
            print_error(f"Failed to get rates: {err}")
            return

        # Wait for response
        try:
            data = await asyncio.wait_for(response_future, timeout=2.0)
            console.print()
            console.print("[bold]Loop Rates:[/bold]")
            console.print(f"  Control:   [green]{data.get('ctrl_hz', '?')} Hz[/green] ({data.get('ctrl_ms', '?')} ms)")
            console.print(f"  Safety:    [green]{data.get('safety_hz', '?')} Hz[/green] ({data.get('safety_ms', '?')} ms)")
            console.print(f"  Telemetry: [green]{data.get('telem_hz', '?')} Hz[/green] ({data.get('telem_ms', '?')} ms)")
        except asyncio.TimeoutError:
            print_error("Rates response timed out")
    finally:
        shell.client.bus.unsubscribe("cmd.CMD_GET_RATES", on_response)
