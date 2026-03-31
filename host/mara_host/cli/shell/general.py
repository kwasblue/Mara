# mara_host/cli/commands/run/shell/commands/general.py
"""General shell commands: help, quit, events, clear, commands, send, raw."""

import asyncio
from rich.markup import escape

from .registry import command, alias, get_commands, get_groups
from mara_host.cli.console import console, print_success, print_error, print_info


@command("help", "Show available commands", group="General")
async def cmd_help(shell, args: list[str]) -> None:
    """Show help."""
    console.print()
    console.print("[bold]Available Commands:[/bold]")
    console.print()

    # Define group order for consistent display
    group_order = [
        "Connection",
        "General",
        "Safety",
        "Actuators",
        "Sensors",
        "Camera",
        "Telemetry",
        "Control",
        "Info",
        "Advanced",
    ]

    groups = get_groups()
    commands = get_commands()

    # Show groups in defined order, then any extras
    shown = set()
    for group in group_order:
        if group in groups:
            _print_group(group, groups[group], commands)
            shown.add(group)

    # Show any groups not in the predefined order
    for group in sorted(groups.keys()):
        if group not in shown:
            _print_group(group, groups[group], commands)


def _print_group(group: str, cmds: list[str], commands: dict) -> None:
    """Print a command group."""
    console.print(f"[bold cyan]{group}:[/bold cyan]")
    for cmd in cmds:
        if cmd in commands:
            _, desc = commands[cmd]
            console.print(f"  [green]{cmd:12}[/green] {desc}")
    console.print()


@command("quit", "Exit the shell", group="General")
async def cmd_quit(shell, args: list[str]) -> str:
    """Exit the shell."""
    return "quit"


# Alias for quit
alias("exit", "quit")


@command("events", "Show events: events [count|all|on|off]", group="General")
async def cmd_events(shell, args: list[str]) -> None:
    """Show recent events or toggle live display."""
    # Handle on/off toggle
    if args and args[0].lower() in ("on", "off"):
        shell.show_events_live[0] = args[0].lower() == "on"
        status = "enabled" if shell.show_events_live[0] else "disabled"
        print_success(f"Live event display {status}")
        return

    # Parse args
    show_all = False
    count = 10
    if args:
        if args[0].lower() == "all":
            show_all = True
            count = int(args[1]) if len(args) > 1 else 20
        else:
            try:
                count = int(args[0])
            except ValueError:
                print_error(f"Unknown argument: {args[0]}. Use: events [count|all|on|off]")
                return

    if not shell.event_log:
        print_info("No events yet")
        return

    # Filter events (skip heartbeats unless show_all)
    filtered = [(t, d) for t, d in shell.event_log if show_all or t != "heartbeat"]

    if not filtered:
        print_info("No events (use 'events all' to include heartbeats)")
        return

    console.print()
    console.print(f"[bold]Recent Events (last {count}):[/bold]")
    console.print()

    for topic, data in filtered[-count:]:
        # Escape topic to prevent Rich markup interpretation
        safe_topic = escape(topic)
        # Format data - skip empty dicts
        if isinstance(data, dict) and not data:
            data_str = "[dim](empty)[/dim]"
        elif isinstance(data, dict):
            # Format dict more readably
            data_str = " ".join(f"{k}={v}" for k, v in data.items())
        else:
            data_str = str(data)

        if topic == "error":
            console.print(f"  [red]\\[{safe_topic}][/red] {data_str}")
        elif topic == "heartbeat":
            console.print(f"  [dim]\\[{safe_topic}][/dim] {data_str}")
        elif topic == "state":
            console.print(f"  [yellow]\\[{safe_topic}][/yellow] {data_str}")
        else:
            console.print(f"  [cyan]\\[{safe_topic}][/cyan] {data_str}")


@command("clear", "Clear event log", group="General")
async def cmd_clear(shell, args: list[str]) -> None:
    """Clear event log."""
    shell.event_log.clear()
    print_success("Event log cleared")


@command("send", "Send any command: send CMD_NAME [key=value ...]", group="Advanced")
async def cmd_send(shell, args: list[str]) -> None:
    """Send any command by name with key=value payload."""
    if not args:
        console.print("Usage: send CMD_NAME [key=value ...]")
        console.print("Example: send CMD_SERVO_SET_ANGLE servo_id=0 angle=180")
        console.print("Example: send CMD_ENCODER_READ encoder_id=0")
        console.print("Use 'commands' to list all available commands")
        return
    if not shell.require_connection():
        return

    from mara_host.tools.schema import COMMANDS as SCHEMA_COMMANDS

    cmd_name = args[0].upper()
    if not cmd_name.startswith("CMD_"):
        cmd_name = "CMD_" + cmd_name

    if cmd_name not in SCHEMA_COMMANDS:
        print_error(f"Unknown command: {cmd_name}")
        console.print("Use 'commands' to list all available commands")
        return

    # Parse key=value pairs
    payload = {}
    for arg in args[1:]:
        if "=" in arg:
            key, value = arg.split("=", 1)
            # Try to parse as number or bool
            try:
                if value.lower() == "true":
                    payload[key] = True
                elif value.lower() == "false":
                    payload[key] = False
                elif "." in value:
                    payload[key] = float(value)
                else:
                    payload[key] = int(value)
            except ValueError:
                payload[key] = value  # Keep as string
        else:
            print_error(f"Invalid argument: {arg} (use key=value format)")
            return

    try:
        # Setup response listener before sending (avoid race condition)
        response_future: asyncio.Future = asyncio.get_event_loop().create_future()
        response_data = {}

        def on_response(data: dict) -> None:
            nonlocal response_data
            if not response_future.done():
                response_data = data
                response_future.set_result(data)

        shell.client.bus.subscribe(f"cmd.{cmd_name}", on_response)

        try:
            # Send the command
            ok, err = await shell.client.send_reliable(cmd_name, payload)

            if ok:
                print_success(f"{cmd_name} sent successfully")

                # Wait briefly for response data (MCU sends response with ACK)
                try:
                    data = await asyncio.wait_for(response_future, timeout=0.5)
                    if data:
                        # Filter out metadata fields to show useful response data
                        skip_fields = {"cmd", "ok", "seq", "src", "error", "error_code", "error_code_enum"}
                        useful_data = {k: v for k, v in data.items() if k not in skip_fields}
                        if useful_data:
                            console.print()
                            console.print("[bold cyan]Response:[/bold cyan]")
                            for key, value in useful_data.items():
                                console.print(f"  {key}: [green]{value}[/green]")
                except asyncio.TimeoutError:
                    pass  # No additional response data
            else:
                print_error(f"{cmd_name} failed: {err}")
        finally:
            # Unsubscribe to prevent memory leaks
            shell.client.bus.unsubscribe(f"cmd.{cmd_name}", on_response)
    except Exception as e:
        print_error(f"Error: {e}")


@command("commands", "List all available MCU commands", group="Advanced")
async def cmd_commands(shell, args: list[str]) -> None:
    """List all available commands."""
    from mara_host.tools.schema import COMMANDS as SCHEMA_COMMANDS
    from collections import defaultdict

    # Group by prefix
    groups = defaultdict(list)
    for cmd in sorted(SCHEMA_COMMANDS.keys()):
        parts = cmd.split("_")
        prefix = parts[1] if len(parts) > 1 else "OTHER"
        groups[prefix].append(cmd)

    # Filter by search term if provided
    search = args[0].upper() if args else None

    console.print()
    console.print(f"[bold]Available Commands ({len(SCHEMA_COMMANDS)} total):[/bold]")
    console.print()

    for prefix in sorted(groups.keys()):
        cmds = groups[prefix]
        if search and search not in prefix:
            cmds = [c for c in cmds if search in c]
            if not cmds:
                continue

        console.print(f"[bold cyan]{prefix}:[/bold cyan]")
        for cmd in cmds:
            desc = SCHEMA_COMMANDS[cmd].get("description", "")[:50]
            console.print(f"  [green]{cmd:30}[/green] {desc}")
        console.print()


@command("raw", "Send raw JSON command", group="Advanced")
async def cmd_raw(shell, args: list[str]) -> None:
    """Send raw JSON command."""
    if not args:
        console.print("Usage: raw <json_command>")
        console.print('Example: raw {"cmd": "ping"}')
        return
    if not shell.require_connection():
        return

    import json
    try:
        cmd_str = " ".join(args)
        cmd_obj = json.loads(cmd_str)
        await shell.client.send_command(cmd_obj)
        print_success("Command sent")
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON: {e}")
