# mara_host/cli/commands/pins/validate.py
"""
Pin validation commands: validate, conflicts.
"""

import argparse

from mara_host.cli.console import (
    console,
    print_success,
)
from mara_host.services.pins import PinService


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate current pin assignments for issues."""
    service = PinService()
    pins = service.get_assignments()

    conflicts = service.detect_conflicts()

    errors = [c for c in conflicts if c.severity == "error"]
    warnings = [c for c in conflicts if c.severity == "warning"]

    console.print()
    console.print("[bold cyan]Pin Assignment Validation[/bold cyan]")
    console.print()

    if errors:
        console.print("[bold red]ERRORS:[/bold red]")
        for c in errors:
            console.print(f"  [red]\u2717[/red] {c.message}")
        console.print()

    if warnings:
        console.print("[bold yellow]WARNINGS:[/bold yellow]")
        for c in warnings:
            console.print(f"  [yellow]\u26a0[/yellow]  {c.message}")
        console.print()

    if not errors and not warnings:
        print_success("All pin assignments look good!")
        console.print()

    console.print(f"[dim]Total: {len(pins)} pins assigned[/dim]")

    return 1 if errors else 0


def cmd_conflicts(args: argparse.Namespace) -> int:
    """Check for pin conflicts and potential issues."""
    service = PinService()
    pins = service.get_assignments()

    conflicts = service.detect_conflicts()

    console.print()
    console.print("[bold cyan]Pin Conflict Analysis[/bold cyan]")
    console.print()

    errors = [c for c in conflicts if c.severity == "error"]
    warnings = [c for c in conflicts if c.severity == "warning"]

    if errors:
        console.print("[bold red]CONFLICTS:[/bold red]")
        for c in errors:
            console.print(f"  [red]\u2717[/red] [bold]{c.conflict_type}:[/bold] {c.message}")
        console.print()

    if warnings:
        console.print("[bold yellow]WARNINGS:[/bold yellow]")
        for c in warnings:
            console.print(f"  [yellow]\u26a0[/yellow]  [bold]{c.conflict_type}:[/bold] {c.message}")
        console.print()

    # Show boot pins in use separately
    boot_conflicts = [c for c in conflicts if c.conflict_type == "boot_pin"]
    if boot_conflicts:
        console.print("[bold yellow]BOOT PINS IN USE:[/bold yellow]")
        for c in boot_conflicts:
            console.print(f"  [yellow]\u26a0[/yellow]  GPIO {c.gpio}")
            console.print(f"      [dim]{c.message}[/dim]")
        console.print()

    if not conflicts:
        print_success("No conflicts or issues detected!")
        console.print()

    console.print(f"[dim]Analyzed {len(pins)} pin assignments[/dim]")

    return 1 if errors else 0
