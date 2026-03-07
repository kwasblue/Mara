# mara_host/cli/commands/pins/_common.py
"""
Common utilities for pin commands.
"""

from rich.prompt import Confirm

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
)
from mara_host.services.pins import PinService


def do_assign(name: str, gpio: int, force: bool = False) -> bool:
    """Assign a pin (helper for interactive mode and wizards)."""
    service = PinService()

    info = service.get_pin_info(gpio)
    if info and info.warning and not force:
        print_warning(info.warning)
        if not Confirm.ask("Continue anyway?", default=False):
            console.print("[dim]Cancelled.[/dim]")
            return False

    success, message = service.assign(name, gpio)
    if success:
        print_success(message)
        return True
    else:
        print_error(message)
        return False


def do_remove(name: str) -> bool:
    """Remove a pin assignment (helper for interactive mode)."""
    service = PinService()

    success, message = service.remove(name)
    if success:
        print_success(message)
        return True
    else:
        print_error(message)
        return False
