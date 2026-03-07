# mara_host/cli/commands/flash.py
"""Firmware flashing commands for MARA CLI."""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
    print_info,
)

from mara_host.tools.build_firmware import MCU_PROJECT


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register flash command."""
    flash_parser = subparsers.add_parser(
        "flash",
        help="Flash firmware to ESP32",
        description="Flash firmware to ESP32 with auto-detection",
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
        help="PlatformIO environment (default: esp32_usb)",
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
        help="Erase ESP32 flash memory",
    )
    erase_p.add_argument(
        "-p", "--port",
        help="Serial port (auto-detect if not specified)",
    )
    erase_p.set_defaults(func=cmd_erase)

    # info - show chip info
    info_p = flash_sub.add_parser(
        "info",
        help="Show ESP32 chip information",
    )
    info_p.add_argument(
        "-p", "--port",
        help="Serial port (auto-detect if not specified)",
    )
    info_p.set_defaults(func=cmd_info)

    # Default
    flash_parser.set_defaults(func=cmd_auto)


def _find_esp32_ports() -> list[dict]:
    """Find ESP32 serial ports."""
    ports = []

    try:
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            # Check for common ESP32 USB-UART chips
            is_esp32 = False
            chip_type = "Unknown"

            desc = (port.description or "").lower()
            hwid = (port.hwid or "").lower()

            if "cp210" in desc or "cp210" in hwid:
                is_esp32 = True
                chip_type = "CP2102/CP2104"
            elif "ch340" in desc or "ch340" in hwid:
                is_esp32 = True
                chip_type = "CH340"
            elif "ftdi" in desc or "ftdi" in hwid:
                is_esp32 = True
                chip_type = "FTDI"
            elif "usb" in desc and "serial" in desc:
                is_esp32 = True
                chip_type = "USB Serial"

            if is_esp32:
                ports.append({
                    "port": port.device,
                    "description": port.description,
                    "chip": chip_type,
                    "hwid": port.hwid,
                })

    except ImportError:
        # Try platform-specific detection
        import glob
        if sys.platform == "darwin":
            for p in glob.glob("/dev/cu.usbserial-*") + glob.glob("/dev/cu.SLAB_USBtoUART*"):
                ports.append({"port": p, "description": "USB Serial", "chip": "Unknown"})
        elif sys.platform == "linux":
            for p in glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"):
                ports.append({"port": p, "description": "USB Serial", "chip": "Unknown"})

    return ports


def cmd_ports(args: argparse.Namespace) -> int:
    """List available serial ports."""
    console.print()
    console.print("[bold cyan]Available Serial Ports[/bold cyan]")
    console.print()

    ports = _find_esp32_ports()

    if not ports:
        print_warning("No ESP32-compatible serial ports found")
        print_info("Make sure your ESP32 is connected via USB")
        return 0

    table = Table(show_header=True)
    table.add_column("Port", style="green")
    table.add_column("Chip", style="cyan")
    table.add_column("Description", style="dim")

    for p in ports:
        table.add_row(p["port"], p.get("chip", ""), p.get("description", ""))

    console.print(table)
    return 0


def cmd_auto(args: argparse.Namespace) -> int:
    """Auto-detect port and flash."""
    env = getattr(args, 'env', 'esp32_usb')
    erase = getattr(args, 'erase', False)

    console.print()
    console.print("[bold cyan]Auto Flash[/bold cyan]")
    console.print()

    # Find ports
    ports = _find_esp32_ports()

    if not ports:
        print_error("No ESP32 serial ports detected")
        print_info("Connect your ESP32 via USB and try again")
        return 1

    if len(ports) == 1:
        port = ports[0]["port"]
        console.print(f"  Detected: [green]{port}[/green] ({ports[0].get('chip', 'Unknown')})")
    else:
        console.print("  Multiple ports detected:")
        for i, p in enumerate(ports):
            console.print(f"    [{i}] {p['port']} ({p.get('chip', '')})")

        from rich.prompt import IntPrompt
        idx = IntPrompt.ask("Select port", default=0)
        if idx < 0 or idx >= len(ports):
            print_error("Invalid selection")
            return 1
        port = ports[idx]["port"]

    console.print(f"  Environment: [green]{env}[/green]")
    console.print()

    # Erase if requested
    if erase:
        print_info("Erasing flash...")
        rc = _run_esptool(["erase_flash"], port)
        if rc != 0:
            print_error("Erase failed")
            return rc

    # Flash
    print_info("Uploading firmware...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Flashing...", total=None)

        cmd = ["pio", "run", "-e", env, "-t", "upload", "--upload-port", port]
        result = subprocess.run(cmd, cwd=MCU_PROJECT, capture_output=True, text=True)

    if result.returncode == 0:
        print_success("Firmware uploaded successfully")
        console.print()
        print_info(f"Connect with: mara run serial -p {port}")
    else:
        print_error("Upload failed")
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
        return 1

    return 0


def cmd_erase(args: argparse.Namespace) -> int:
    """Erase ESP32 flash."""
    port = args.port

    if not port:
        ports = _find_esp32_ports()
        if not ports:
            print_error("No ESP32 detected")
            return 1
        port = ports[0]["port"]

    console.print()
    console.print("[bold cyan]Erasing Flash[/bold cyan]")
    console.print(f"  Port: [green]{port}[/green]")
    console.print()

    from rich.prompt import Confirm
    if not Confirm.ask("[yellow]This will erase all data. Continue?[/yellow]", default=False):
        console.print("[dim]Cancelled[/dim]")
        return 0

    rc = _run_esptool(["erase_flash"], port)

    if rc == 0:
        print_success("Flash erased")
    else:
        print_error("Erase failed")

    return rc


def cmd_info(args: argparse.Namespace) -> int:
    """Show ESP32 chip info."""
    port = args.port

    if not port:
        ports = _find_esp32_ports()
        if not ports:
            print_error("No ESP32 detected")
            return 1
        port = ports[0]["port"]

    console.print()
    console.print("[bold cyan]ESP32 Chip Information[/bold cyan]")
    console.print(f"  Port: [green]{port}[/green]")
    console.print()

    result = subprocess.run(
        ["esptool.py", "--port", port, "chip_id"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        # Parse and display info
        for line in result.stdout.split('\n'):
            if ':' in line and not line.startswith('esptool'):
                console.print(f"  {line.strip()}")
    else:
        # Try with pio
        result = subprocess.run(
            ["pio", "device", "list", "--serial"],
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)

    return result.returncode


def _run_esptool(esptool_args: list[str], port: str) -> int:
    """Run esptool.py command."""
    try:
        cmd = ["esptool.py", "--port", port] + esptool_args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode
    except FileNotFoundError:
        # Try via PlatformIO
        try:
            cmd = ["pio", "run", "-t", "erase"] if "erase" in esptool_args else ["pio", "device", "list"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode
        except FileNotFoundError:
            print_error("Neither esptool.py nor PlatformIO found")
            return 1
