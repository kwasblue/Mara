# cli/commands/logs/tail.py
"""Tail session command."""

import argparse
import json
import time

from mara_host.cli.console import console, print_error
from ._common import LOG_DIR, print_event


def cmd_tail(args: argparse.Namespace) -> int:
    """Follow session log."""
    session = args.session
    initial_lines = args.lines

    events_file = LOG_DIR / session / "events.jsonl"
    if not events_file.exists():
        print_error(f"Session not found: {session}")
        return 1

    console.print()
    console.print(f"[bold cyan]Tailing: {session}[/bold cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    # Show initial lines
    with open(events_file) as f:
        lines = f.readlines()

    for line in lines[-initial_lines:]:
        if line.strip():
            try:
                event = json.loads(line)
                print_event(event)
            except json.JSONDecodeError:
                pass  # Skip malformed JSON lines

    # Follow for new lines
    try:
        with open(events_file) as f:
            f.seek(0, 2)

            while True:
                line = f.readline()
                if line:
                    try:
                        event = json.loads(line)
                        print_event(event)
                    except json.JSONDecodeError:
                        pass  # Skip malformed JSON lines
                else:
                    time.sleep(0.1)

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped[/dim]")

    return 0
