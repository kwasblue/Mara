# cli/commands/build/clean.py
"""Clean build artifacts command."""

import argparse

from mara_host.cli.console import console, print_success, print_error
from mara_host.tools.build_firmware import clean as do_clean


def cmd_clean(args: argparse.Namespace) -> int:
    """Clean build artifacts."""
    env = getattr(args, 'env', None)

    console.print()
    if env:
        console.print(f"[bold cyan]Cleaning build artifacts for {env}[/bold cyan]")
    else:
        console.print("[bold cyan]Cleaning all build artifacts[/bold cyan]")
    console.print()

    rc = do_clean(env)

    if rc == 0:
        print_success("Clean completed")
    else:
        print_error(f"Clean failed with exit code {rc}")

    return rc
