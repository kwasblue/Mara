# mara_host/cli/commands/pins/list.py
"""
Pin listing commands: pinout, list, free.
"""

import argparse

from mara_host.cli.console import (
    console,
    print_info,
    print_pinout_panel,
    create_pin_table,
    format_pin_status,
)
from mara_host.tools.pins import PINS_JSON
from mara_host.services.pins import PinService


def cmd_pinout(args: argparse.Namespace) -> int:
    """Display visual ASCII pinout diagram."""
    service = PinService()
    pinout_text = service.generate_pinout_diagram()

    console.print()
    print_pinout_panel(pinout_text, "ESP32 DevKit V1 - Pin Assignment")

    pinout_file = PINS_JSON.parent / "pinout.txt"
    pinout_file.write_text(pinout_text)
    print_info(f"Saved to: {pinout_file}")

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all pins with their status."""
    service = PinService()
    assignments = service.get_assignments_by_gpio()
    all_pins = service.get_all_pins()
    all_gpios = sorted(all_pins.keys())

    console.print()
    console.print("[bold cyan]ESP32 GPIO Pin Status[/bold cyan]")
    console.print()

    table = create_pin_table()

    for gpio in all_gpios:
        info = service.get_pin_info(gpio)
        if not info:
            continue

        status_text, status_style = format_pin_status(
            gpio=gpio,
            assigned_name=assignments.get(gpio),
            is_flash=service.is_flash_pin(gpio),
            is_boot=service.is_boot_pin(gpio),
            is_input_only=service.is_input_only(gpio),
            has_warning=bool(info.warning),
        )

        caps = service.capability_string(gpio)
        notes = info.notes[:40] + "..." if len(info.notes) > 43 else info.notes

        table.add_row(
            str(gpio),
            f"[{status_style}]{status_text}[/{status_style}]",
            caps,
            notes,
        )

    console.print(table)

    # Summary
    pins = service.get_assignments()
    used = len(pins)
    flash_pins = service.get_flash_pins()
    usable = len([g for g in all_pins if g not in flash_pins])
    safe_set = service.get_safe_pin_set()
    safe_used = len([g for g in pins.values() if g in safe_set])
    console.print()
    console.print(f"[dim]Assigned: {used}/{usable} usable pins[/dim]")
    console.print(f"[dim]Safe pins available: {len(service.get_safe_pins()) - safe_used}[/dim]")

    return 0


def cmd_free(args: argparse.Namespace) -> int:
    """Show only available pins."""
    service = PinService()
    free_by_category = service.get_free_pins_by_category()

    console.print()
    console.print("[bold cyan]Available GPIO Pins[/bold cyan]")
    console.print()

    def print_pin_section(title: str, gpios: list[int], style: str = "white") -> None:
        if not gpios:
            return

        console.print(f"[bold {style}]{title}[/bold {style}]")
        table = create_pin_table()

        for gpio in gpios:
            info = service.get_pin_info(gpio)
            if not info:
                continue
            status_text, status_style = format_pin_status(
                gpio=gpio,
                assigned_name=None,
                is_flash=service.is_flash_pin(gpio),
                is_boot=service.is_boot_pin(gpio),
                is_input_only=service.is_input_only(gpio),
                has_warning=bool(info.warning),
            )
            table.add_row(
                str(gpio),
                f"[{status_style}]{status_text}[/{status_style}]",
                service.capability_string(gpio),
                info.notes[:40],
            )

        console.print(table)
        console.print()

    print_pin_section("RECOMMENDED (no boot/flash restrictions)", free_by_category["safe"], "green")
    print_pin_section("INPUT-ONLY PINS (GPIO 34-39, no output/PWM)", free_by_category["input_only"], "blue")
    print_pin_section("BOOT PINS (usable but check warnings)", free_by_category["boot"], "yellow")

    return 0
