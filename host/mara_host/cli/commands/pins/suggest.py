# mara_host/cli/commands/pins/suggest.py
"""
Pin suggestion command.
"""

import argparse

from mara_host.cli.console import (
    console,
    print_info,
    print_warning,
    create_pin_table,
    format_pin_status,
)
from mara_host.services.pins import PinService


def cmd_suggest(args: argparse.Namespace) -> int:
    """Suggest best pins for a specific use case."""
    service = PinService()
    use_case = args.use_case

    console.print()
    console.print(f"[bold cyan]Best pins for {use_case.upper()}[/bold cyan]")
    console.print()

    recommendations = service.suggest_pins(use_case, count=10)

    if not recommendations:
        print_warning("No available pins match this use case.")
        return 0

    table = create_pin_table()
    for rec in recommendations:
        info = service.get_pin_info(rec.gpio)
        if not info:
            continue

        status_text, status_style = format_pin_status(
            gpio=rec.gpio,
            assigned_name=None,
            is_flash=service.is_flash_pin(rec.gpio),
            is_boot=service.is_boot_pin(rec.gpio),
            is_input_only=service.is_input_only(rec.gpio),
            has_warning=bool(rec.warnings),
        )
        table.add_row(
            str(rec.gpio),
            f"[{status_style}]{status_text}[/{status_style}]",
            service.capability_string(rec.gpio),
            info.notes[:40],
        )

    console.print(table)

    notes = service.get_use_case_notes(use_case)
    if notes:
        console.print()
        for note in notes:
            print_info(note)

    return 0
