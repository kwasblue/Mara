# cli/commands/logs/list.py
"""List sessions command."""

import argparse
from pathlib import Path

from rich.table import Table

from mara_host.cli.console import console, print_info
from ._common import find_sessions, format_size


def cmd_list(args: argparse.Namespace) -> int:
    """List recorded sessions."""
    log_dir = Path(args.dir)
    limit = args.limit

    sessions = find_sessions(log_dir)

    console.print()
    console.print("[bold cyan]Recorded Sessions[/bold cyan]")
    console.print()

    if not sessions:
        print_info(f"No sessions found in {log_dir}")
        print_info("Record a session with: mara record <session_name>")
        return 0

    table = Table(show_header=True)
    table.add_column("Session", style="cyan")
    table.add_column("Date", style="dim")
    table.add_column("Events", justify="right")
    table.add_column("Size", justify="right")

    for s in sessions[:limit]:
        date_str = s["mtime"].strftime("%Y-%m-%d %H:%M")
        size_str = format_size(s["size"])
        table.add_row(s["name"], date_str, str(s["event_count"]), size_str)

    console.print(table)

    if len(sessions) > limit:
        console.print(f"\n[dim]Showing {limit} of {len(sessions)} sessions[/dim]")

    return 0
