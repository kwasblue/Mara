# cli/commands/build/size.py
"""Firmware size command.

Uses the ToolingService for size information.
"""

import argparse
import re
from pathlib import Path
from typing import Optional

from mara_host.cli.console import console, print_error, print_info
from mara_host.services.tooling import ToolingService


# Default firmware location (backend-agnostic)
_DEFAULT_PROJECT = Path(__file__).resolve().parents[5] / "firmware" / "mcu"


def cmd_size(args: argparse.Namespace) -> int:
    """Show firmware size information."""
    env = args.env
    detailed = getattr(args, 'detailed', False)
    backend = getattr(args, 'build_backend', 'platformio')

    console.print()
    console.print(f"[bold cyan]Firmware Size - {env}[/bold cyan]")
    console.print(f"  Backend: [green]{backend}[/green]")
    console.print()

    tooling = ToolingService()
    tooling.set_backend(backend)

    # Build to get size info (dry-run style - just to trigger size output)
    outcome = tooling.build(environment=env, verbose=detailed)

    if not outcome.success:
        print_error("Build failed - cannot determine size")
        if outcome.error:
            console.print(f"[red]{outcome.error}[/red]")
        return outcome.return_code

    # Parse size from build output
    if detailed:
        console.print(outcome.output)
    else:
        _show_size_from_output(outcome.output)

    # Show firmware size from outcome if available
    if outcome.firmware_size:
        console.print()
        console.print(f"  Firmware: [cyan]{outcome.firmware_size:,}[/cyan] bytes")
    if outcome.ram_usage:
        console.print(f"  RAM Used: [cyan]{outcome.ram_usage:,}[/cyan] bytes")

    # Try to find binary file
    bin_path = _find_firmware_binary(env, backend)
    if bin_path and bin_path.exists():
        size_kb = bin_path.stat().st_size / 1024
        console.print()
        console.print(f"[dim]Binary: {bin_path.name} ({size_kb:.1f} KB)[/dim]")

    return 0


def _show_size_from_output(output: str) -> None:
    """Parse and display size info from build output."""
    for line in output.split('\n'):
        if 'RAM:' in line or 'Flash:' in line:
            if '[' in line and ']' in line:
                pct_match = re.search(r'(\d+\.?\d*)%', line)
                if pct_match:
                    pct = float(pct_match.group(1))
                    if pct > 90:
                        console.print(f"[red]{line}[/red]")
                    elif pct > 70:
                        console.print(f"[yellow]{line}[/yellow]")
                    else:
                        console.print(f"[green]{line}[/green]")
                else:
                    console.print(line)
            else:
                console.print(line)


def _find_firmware_binary(env: str, backend: str) -> Optional[Path]:
    """Find the firmware binary based on backend."""
    if backend == "platformio":
        return _DEFAULT_PROJECT / ".pio" / "build" / env / "firmware.bin"
    elif backend == "cmake":
        build_dir = _DEFAULT_PROJECT / "build"
        # Try common locations
        candidates = [
            build_dir / "firmware.bin",
            build_dir / f"{_DEFAULT_PROJECT.name}.bin",
            build_dir / "app.bin",
        ]
        for c in candidates:
            if c.exists():
                return c
        # Search for any .bin
        bins = list(build_dir.glob("*.bin"))
        if bins:
            return bins[0]
    return None


def show_size_summary(
    env: str,
    backend: str = "platformio",
    firmware_size: Optional[int] = None,
    ram_usage: Optional[int] = None,
) -> None:
    """Show brief firmware size summary after build.

    Args:
        env: Build environment
        backend: Build backend name
        firmware_size: Firmware size in bytes (from build outcome)
        ram_usage: RAM usage in bytes (from build outcome)
    """
    # Use provided values or fall back to cached info
    if firmware_size is not None:
        size_info = {
            'flash_used': firmware_size,
            'flash_total': 1310720,  # 1.25MB typical app partition
            'ram_used': ram_usage or 0,
            'ram_total': 327680,  # 320KB typical
        }
    else:
        size_info = _get_cached_size_info(env, backend)

    if size_info:
        flash_pct = (size_info['flash_used'] / size_info['flash_total']) * 100
        ram_pct = (size_info['ram_used'] / size_info['ram_total']) * 100

        flash_bar = _make_bar(flash_pct, 20)
        ram_bar = _make_bar(ram_pct, 20)

        console.print()
        console.print(f"  Flash: {flash_bar} {size_info['flash_used']:,}B / {size_info['flash_total']:,}B ({flash_pct:.1f}%)")
        console.print(f"  RAM:   {ram_bar} {size_info['ram_used']:,}B / {size_info['ram_total']:,}B ({ram_pct:.1f}%)")


def _make_bar(percentage: float, width: int = 20) -> str:
    """Create a simple progress bar string."""
    filled = int(width * percentage / 100)
    empty = width - filled

    if percentage > 90:
        color = "red"
    elif percentage > 70:
        color = "yellow"
    else:
        color = "green"

    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"


def _get_cached_size_info(env: str, backend: str) -> Optional[dict]:
    """Get firmware size from cached build artifacts.

    This reads size info without rebuilding.
    """
    # For now, just read binary size and estimate
    bin_path = _find_firmware_binary(env, backend)
    if bin_path and bin_path.exists():
        flash_used = bin_path.stat().st_size
        # Typical ESP32 flash and RAM sizes
        return {
            'flash_used': flash_used,
            'flash_total': 1310720,  # 1.25MB typical app partition
            'ram_used': 0,  # Can't determine without build output
            'ram_total': 327680,  # 320KB typical
        }
    return None
