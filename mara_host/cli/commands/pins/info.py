# mara_host/cli/commands/pins/info.py
"""
Pin info command.
"""

import argparse

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
)
from mara_host.services.pins import PinService


def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed info for a specific pin."""
    service = PinService()
    gpio = args.gpio

    info = service.get_pin_info(gpio)
    if not info:
        print_error(f"GPIO {gpio} not found in ESP32 pinout")
        return 1

    assignments = service.get_assignments_by_gpio()

    console.print()
    console.print(f"[bold cyan]GPIO {gpio}[/bold cyan]")
    console.print()

    # Status
    if gpio in assignments:
        console.print(f"[bold]Status:[/bold]       [green]ASSIGNED as '{assignments[gpio]}'[/green]")
    elif service.is_flash_pin(gpio):
        console.print(f"[bold]Status:[/bold]       [red]UNUSABLE (connected to flash)[/red]")
    else:
        console.print(f"[bold]Status:[/bold]       [cyan]Available[/cyan]")

    console.print(f"[bold]Capabilities:[/bold] {service.capability_string(gpio)}")
    console.print(f"[bold]Notes:[/bold]        {info.notes}")

    if info.adc_channel:
        console.print(f"[bold]ADC:[/bold]          {info.adc_channel}")
    if info.touch_channel is not None:
        console.print(f"[bold]Touch:[/bold]        Touch{info.touch_channel}")
    if info.rtc_gpio is not None:
        console.print(f"[bold]RTC GPIO:[/bold]     {info.rtc_gpio}")

    if info.warning:
        console.print()
        print_warning(info.warning)

    if service.is_safe_pin(gpio):
        console.print()
        print_success("This is a safe, recommended pin for general use.")

    return 0
