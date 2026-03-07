# mara_host/cli/commands/pins/interactive.py
"""
Interactive pin assignment mode.
"""

import argparse

from rich.prompt import Prompt

from mara_host.cli.console import (
    console,
    print_error,
)
from mara_host.cli.commands.pins._common import do_assign, do_remove
from mara_host.cli.commands.pins.list import cmd_list, cmd_free, cmd_pinout
from mara_host.cli.commands.pins.info import cmd_info
from mara_host.cli.commands.pins.suggest import cmd_suggest
from mara_host.cli.commands.pins.validate import cmd_validate, cmd_conflicts


def cmd_interactive(args: argparse.Namespace) -> int:
    """Interactive pin assignment mode."""
    console.print()
    console.print("[bold cyan]Interactive Pin Assignment[/bold cyan]")
    console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]")
    console.print()

    while True:
        try:
            cmd = Prompt.ask("[green]pins>[/green]").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting...[/dim]")
            break

        if not cmd:
            continue

        parts = cmd.split()
        action = parts[0]

        if action in ("quit", "exit", "q"):
            break
        elif action == "help":
            _interactive_help()
        elif action == "list":
            cmd_list(args)
        elif action == "free":
            cmd_free(args)
        elif action == "pinout":
            cmd_pinout(args)
        elif action == "info" and len(parts) > 1:
            try:
                gpio = int(parts[1])
                args.gpio = gpio
                cmd_info(args)
            except ValueError:
                print_error(f"Invalid GPIO number: {parts[1]}")
        elif action == "assign" and len(parts) >= 3:
            name = parts[1].upper()
            try:
                gpio = int(parts[2])
                do_assign(name, gpio, force=False)
            except ValueError:
                print_error(f"Invalid GPIO number: {parts[2]}")
        elif action == "remove" and len(parts) > 1:
            name = parts[1].upper()
            do_remove(name)
        elif action == "suggest" and len(parts) > 1:
            use_case = parts[1]
            if use_case in ["pwm", "adc", "input", "output", "i2c", "spi", "uart", "touch", "dac"]:
                args.use_case = use_case
                cmd_suggest(args)
            else:
                print_error(f"Unknown use case: {use_case}")
        elif action == "conflicts":
            cmd_conflicts(args)
        elif action == "validate":
            cmd_validate(args)
        elif action == "save":
            console.print("[green]Pins are automatically saved after each change[/green]")
        else:
            print_error(f"Unknown command: {action}")
            console.print("[dim]Type 'help' for available commands[/dim]")

    return 0


def _interactive_help() -> None:
    """Show interactive mode help."""
    console.print()
    console.print("[bold]Available Commands:[/bold]")
    console.print()
    console.print("  [cyan]list[/cyan]                  Show all pins")
    console.print("  [cyan]free[/cyan]                  Show available pins")
    console.print("  [cyan]pinout[/cyan]                Show board diagram")
    console.print("  [cyan]info <gpio>[/cyan]           Show details for a pin")
    console.print("  [cyan]assign <name> <gpio>[/cyan]  Assign a pin")
    console.print("  [cyan]remove <name>[/cyan]         Remove assignment")
    console.print("  [cyan]suggest <use_case>[/cyan]    Suggest pins (pwm, adc, i2c, etc.)")
    console.print("  [cyan]conflicts[/cyan]             Check for conflicts")
    console.print("  [cyan]validate[/cyan]              Validate assignments")
    console.print("  [cyan]quit[/cyan]                  Exit interactive mode")
    console.print()
