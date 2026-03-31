# mara_host/cli/shell/__init__.py
"""
Interactive shell package.

Commands are auto-discovered from this package. To add new commands,
create a .py file in this directory and use the @command decorator.

Example:
    # cli/shell/my_feature.py
    from .registry import command

    @command("mycommand", "Does something cool", group="MyGroup")
    async def cmd_mycommand(shell, args: list[str]) -> None:
        shell.print_success("Did the thing!")
"""

import argparse
import asyncio
import logging
from pathlib import Path
import importlib
from typing import Any

from rich.prompt import Prompt
from rich.markup import escape

from mara_host.cli.console import console, print_info


# Modules that are not command handlers
_EXCLUDE_MODULES = {"__init__", "registry", "core"}


def _discover_commands():
    """Auto-import all command modules to register their commands."""
    pkg_dir = Path(__file__).parent
    for py_file in pkg_dir.glob("*.py"):
        module_name = py_file.stem
        if module_name not in _EXCLUDE_MODULES:
            importlib.import_module(f".{module_name}", __package__)


# Discover and register all commands on import
_discover_commands()


def cmd_shell(args: argparse.Namespace) -> int:
    """Launch interactive command shell."""
    from mara_host.cli.commands.run._common import get_log_params

    transport_type = args.transport
    log_level, log_dir = get_log_params(args)

    console.print()
    console.print("[bold cyan]MARA Interactive Shell[/bold cyan]")

    if transport_type == "serial":
        console.print(f"  Transport: [green]Serial[/green]")
        console.print(f"  Port: [green]{args.port}[/green]")
    elif transport_type == "ble":
        console.print(f"  Transport: [green]Bluetooth SPP[/green]")
        console.print(f"  Device: [green]{args.ble_name}[/green]")
    else:
        console.print(f"  Transport: [green]TCP[/green]")
        console.print(f"  Host: [green]{args.host}:{args.tcp_port}[/green]")

    console.print()
    console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]")
    console.print()

    return asyncio.run(_run_interactive_shell(args, log_level, log_dir))


async def _run_interactive_shell(args: argparse.Namespace, log_level: int = logging.INFO, log_dir: str = "logs") -> int:
    """Run the interactive shell."""
    from .core import InteractiveShell

    # Event log
    event_log: list[tuple[str, Any]] = []
    max_log = 100

    def log_event(topic: str, data: Any) -> None:
        event_log.append((topic, data))
        if len(event_log) > max_log:
            event_log.pop(0)

    # Track whether to show events live (will be set on shell instance)
    show_events_live = [False]  # Default off, use list for mutable closure

    def handle_event(topic: str, data: Any, style: str = "cyan") -> None:
        log_event(topic, data)
        if show_events_live[0]:
            safe_topic = escape(topic.upper())
            console.print(f"  [{style}]\\[{safe_topic}][/{style}] {data}")

    def setup_event_handlers(client) -> None:
        """Subscribe to events on the client."""
        client.bus.subscribe("heartbeat", lambda d: log_event("heartbeat", d))
        client.bus.subscribe("pong", lambda d: handle_event("pong", d, "green"))
        client.bus.subscribe("hello", lambda d: handle_event("hello", d, "green"))
        client.bus.subscribe("json", lambda d: handle_event("json", d, "cyan"))
        client.bus.subscribe("telemetry", lambda d: log_event("telemetry", d))
        client.bus.subscribe("error", lambda d: handle_event("error", d, "red"))
        # State and connection events
        client.bus.subscribe("state.changed", lambda d: handle_event("state", d, "yellow"))
        client.bus.subscribe("connection.lost", lambda d: handle_event("disconnected", d, "red"))
        client.bus.subscribe("connection.restored", lambda d: handle_event("reconnected", d, "green"))

    # Shell with connection factory
    shell = InteractiveShell(
        event_log=event_log,
        default_args=args,
        log_level=log_level,
        log_dir=log_dir,
        setup_event_handlers=setup_event_handlers,
        show_events_live=show_events_live,
    )

    # Try to connect with default args, but don't fail if we can't
    await shell.try_connect()

    try:
        while True:
            try:
                prompt = "[green]mara>[/green]" if shell.connected else "[yellow]mara (disconnected)>[/yellow]"
                cmd = Prompt.ask(prompt)
            except (KeyboardInterrupt, EOFError):
                console.print()
                break

            if not cmd.strip():
                continue

            result = await shell.execute(cmd.strip())
            if result == "quit":
                break

    finally:
        await shell.cleanup()
        print_info("Disconnected")

    return 0
