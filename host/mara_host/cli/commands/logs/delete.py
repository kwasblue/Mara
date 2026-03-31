# cli/commands/logs/delete.py
"""Delete session command."""

import argparse
import shutil

from mara_host.cli.console import console, print_error, print_success
from ._common import LOG_DIR, format_size


def cmd_delete(args: argparse.Namespace) -> int:
    """Delete a session."""
    session = args.session
    force = args.force

    session_dir = LOG_DIR / session
    if not session_dir.exists():
        print_error(f"Session not found: {session}")
        return 1

    console.print()
    console.print(f"[bold yellow]Delete session: {session}[/bold yellow]")

    total_size = sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file())
    console.print(f"  Size: {format_size(total_size)}")

    if not force:
        from rich.prompt import Confirm
        if not Confirm.ask("[red]Are you sure?[/red]", default=False):
            console.print("[dim]Cancelled[/dim]")
            return 0

    shutil.rmtree(session_dir)
    print_success(f"Deleted session: {session}")

    return 0
