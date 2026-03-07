# mara_host/cli/commands/pins/assign.py
"""
Pin assignment commands: assign, remove, clear.
"""

import argparse

from rich.prompt import Confirm

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
    print_info,
    confirm,
)
from mara_host.services.pins import PinService


def cmd_assign(args: argparse.Namespace) -> int:
    """Assign a name to a GPIO pin."""
    service = PinService()
    name = args.name.upper()
    gpio = args.gpio

    # Check for warning and prompt if needed
    info = service.get_pin_info(gpio)
    if info and info.warning and not args.force:
        print_warning(info.warning)
        if not confirm("Continue anyway?"):
            console.print("[dim]Cancelled.[/dim]")
            return 0

    success, message = service.assign(name, gpio)

    if success:
        print_success(message)
        console.print()
        print_info("Run 'mara generate pins' or 'mara generate all' to regenerate code.")
        return 0
    else:
        print_error(message)
        return 1


def cmd_remove(args: argparse.Namespace) -> int:
    """Remove a pin assignment."""
    service = PinService()
    name = args.name.upper()

    success, message = service.remove(name)

    if success:
        print_success(message)
        console.print()
        print_info("Run 'mara generate pins' or 'mara generate all' to regenerate code.")
        return 0
    else:
        print_error(message)
        return 1


def cmd_clear(args: argparse.Namespace) -> int:
    """Clear all pin assignments."""
    service = PinService()
    pins = service.get_assignments()

    if not pins:
        print_info("No pin assignments to clear.")
        return 0

    console.print()
    console.print(f"[bold yellow]This will remove {len(pins)} pin assignment(s):[/bold yellow]")
    for name, gpio in sorted(pins.items()):
        console.print(f"  {name} = GPIO {gpio}")
    console.print()

    if not args.force:
        if not Confirm.ask("[red]Are you sure?[/red]", default=False):
            console.print("[dim]Cancelled.[/dim]")
            return 0

    success, message = service.clear_all()
    print_success(message)
    console.print()
    print_info("Run 'mara generate pins' to regenerate code.")

    return 0
