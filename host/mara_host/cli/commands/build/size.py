# cli/commands/build/size.py
"""Firmware size command."""

import argparse
import re
import subprocess
import sys
from typing import Optional

from mara_host.cli.console import console, print_error
from mara_host.tools.build_firmware import MCU_PROJECT


def cmd_size(args: argparse.Namespace) -> int:
    """Show firmware size information."""
    env = args.env
    detailed = getattr(args, 'detailed', False)

    console.print()
    console.print(f"[bold cyan]Firmware Size - {env}[/bold cyan]")
    console.print()

    try:
        result = subprocess.run(
            [sys.executable, "-m", "platformio", "run", "-e", env, "-t", "size"],
            cwd=MCU_PROJECT,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print_error("PlatformIO not found. Install with: pip install platformio")
        return 1

    output = result.stdout + result.stderr

    if detailed:
        console.print(output)
    else:
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

    bin_path = MCU_PROJECT / ".pio" / "build" / env / "firmware.bin"
    if bin_path.exists():
        size_kb = bin_path.stat().st_size / 1024
        console.print()
        console.print(f"[dim]Binary: {bin_path.name} ({size_kb:.1f} KB)[/dim]")

    return 0


def show_size_summary(env: str) -> None:
    """Show brief firmware size summary after build."""
    size_info = _get_firmware_size(env)
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


def _get_firmware_size(env: str) -> Optional[dict]:
    """Get firmware size information from PlatformIO."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "platformio", "run", "-e", env, "-t", "size", "--silent"],
            cwd=MCU_PROJECT,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return None

        output = result.stdout + result.stderr
        size_info = {}

        ram_match = re.search(r'RAM:.*?(\d+\.?\d*)%.*?(\d+)\s+bytes.*?(\d+)\s+bytes', output)
        if ram_match:
            size_info['ram_used'] = int(ram_match.group(2))
            size_info['ram_total'] = int(ram_match.group(3))

        flash_match = re.search(r'Flash:.*?(\d+\.?\d*)%.*?(\d+)\s+bytes.*?(\d+)\s+bytes', output)
        if flash_match:
            size_info['flash_used'] = int(flash_match.group(2))
            size_info['flash_total'] = int(flash_match.group(3))

        if size_info:
            return size_info

        size_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([0-9a-f]+)\s+', output)
        if size_match:
            text = int(size_match.group(1))
            data = int(size_match.group(2))
            bss = int(size_match.group(3))

            size_info = {
                'flash_used': text + data,
                'flash_total': 1310720,
                'ram_used': data + bss,
                'ram_total': 327680,
            }
            return size_info

        return None

    except Exception:
        return None
