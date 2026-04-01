# mara_host/cli/commands/flash.py
"""Firmware flashing commands for MARA CLI.

Uses the ToolingService abstraction - no direct tool calls.
"""

import argparse

from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import IntPrompt, Confirm

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
    print_info,
)
from mara_host.services.tooling import ToolingService, DeviceService


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register flash command."""
    flash_parser = subparsers.add_parser(
        "flash",
        help="Flash firmware to device",
        description="Flash firmware with auto-detection",
    )

    flash_sub = flash_parser.add_subparsers(
        dest="flash_cmd",
        title="flash commands",
        metavar="<subcommand>",
    )

    # auto - detect and flash
    auto_p = flash_sub.add_parser(
        "auto",
        help="Auto-detect port and flash",
    )
    auto_p.add_argument(
        "-e", "--env",
        default="esp32_usb",
        help="Build environment (default: esp32_usb)",
    )
    auto_p.add_argument(
        "--backend",
        default="platformio",
        help="Build backend to use (default: platformio)",
    )
    auto_p.add_argument(
        "--erase",
        action="store_true",
        help="Erase flash before uploading",
    )
    auto_p.set_defaults(func=cmd_auto)

    # ports - list available ports
    ports_p = flash_sub.add_parser(
        "ports",
        help="List available serial ports",
    )
    ports_p.set_defaults(func=cmd_ports)

    # erase - erase flash
    erase_p = flash_sub.add_parser(
        "erase",
        help="Erase device flash memory",
    )
    erase_p.add_argument(
        "-p", "--port",
        help="Serial port (auto-detect if not specified)",
    )
    erase_p.set_defaults(func=cmd_erase)

    # info - show chip info
    info_p = flash_sub.add_parser(
        "info",
        help="Show device chip information",
    )
    info_p.add_argument(
        "-p", "--port",
        help="Serial port (auto-detect if not specified)",
    )
    info_p.set_defaults(func=cmd_info)

    # Default
    flash_parser.set_defaults(func=cmd_auto)


def cmd_ports(args: argparse.Namespace) -> int:
    """List available serial ports."""
    device_service = DeviceService()

    console.print()
    console.print("[bold cyan]Available Serial Ports[/bold cyan]")
    console.print()

    devices = device_service.detect_devices()

    if not devices:
        print_warning("No compatible serial ports found")
        print_info("Make sure your device is connected via USB")
        return 0

    table = Table(show_header=True)
    table.add_column("Port", style="green")
    table.add_column("USB Chip", style="cyan")
    table.add_column("MCU", style="yellow")
    table.add_column("Description", style="dim")

    for d in devices:
        table.add_row(
            d.port,
            d.usb_chip.value,
            d.mcu_chip.value,
            d.description,
        )

    console.print(table)
    return 0


def cmd_auto(args: argparse.Namespace) -> int:
    """Auto-detect port and flash."""
    env = getattr(args, 'env', 'esp32_usb')
    backend = getattr(args, 'backend', 'platformio')
    erase = getattr(args, 'erase', False)

    tooling = ToolingService()
    tooling.set_backend(backend)

    console.print()
    console.print("[bold cyan]Auto Flash[/bold cyan]")
    console.print(f"  Backend: [green]{backend}[/green]")
    console.print()

    # Find devices
    devices = tooling.detect_devices()

    if not devices:
        print_error("No devices detected")
        print_info("Connect your device via USB and try again")
        return 1

    if len(devices) == 1:
        device = devices[0]
        port = device.port
        console.print(f"  Detected: [green]{port}[/green] ({device.usb_chip.value})")
    else:
        console.print("  Multiple devices detected:")
        for i, d in enumerate(devices):
            console.print(f"    [{i}] {d.port} ({d.usb_chip.value})")

        idx = IntPrompt.ask("Select device", default=0)
        if idx < 0 or idx >= len(devices):
            print_error("Invalid selection")
            return 1
        device = devices[idx]
        port = device.port

    console.print(f"  Environment: [green]{env}[/green]")
    console.print()

    # Erase if requested
    if erase:
        print_info("Erasing flash...")
        success, message = tooling.erase_flash(port)
        if not success:
            print_error(f"Erase failed: {message}")
            return 1
        print_success("Flash erased")
        console.print()

    # Flash
    print_info("Uploading firmware...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Flashing...", total=None)
        outcome = tooling.flash(port=port, environment=env)

    if outcome.success:
        print_success("Firmware uploaded successfully")
        console.print()
        print_info(f"Connect with: mara run serial -p {port}")
    else:
        print_error("Upload failed")
        if outcome.error:
            console.print(f"[red]{outcome.error}[/red]")
        return outcome.return_code

    return 0


def cmd_erase(args: argparse.Namespace) -> int:
    """Erase device flash."""
    port = args.port
    tooling = ToolingService()

    if not port:
        devices = tooling.detect_devices()
        if not devices:
            print_error("No devices detected")
            return 1
        port = devices[0].port

    console.print()
    console.print("[bold cyan]Erasing Flash[/bold cyan]")
    console.print(f"  Port: [green]{port}[/green]")
    console.print()

    if not Confirm.ask("[yellow]This will erase all data. Continue?[/yellow]", default=False):
        console.print("[dim]Cancelled[/dim]")
        return 0

    success, message = tooling.erase_flash(port)

    if success:
        print_success("Flash erased")
    else:
        print_error(f"Erase failed: {message}")
        return 1

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show device chip info."""
    port = args.port
    tooling = ToolingService()

    if not port:
        devices = tooling.detect_devices()
        if not devices:
            print_error("No devices detected")
            return 1
        port = devices[0].port

    console.print()
    console.print("[bold cyan]Device Information[/bold cyan]")
    console.print(f"  Port: [green]{port}[/green]")
    console.print()

    info = tooling.get_chip_info(port)

    if info:
        for key, value in info.items():
            # Format key nicely
            display_key = key.replace('_', ' ').title()
            console.print(f"  {display_key}: [cyan]{value}[/cyan]")
    else:
        print_warning("Could not read chip info")
        print_info("Device may not be in bootloader mode or esptool not available")
        return 1

    return 0
