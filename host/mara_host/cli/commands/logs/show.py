# cli/commands/logs/show.py
"""Show session command."""

import argparse
import json

from mara_host.cli.console import console, print_error
from ._common import LOG_DIR


def cmd_show(args: argparse.Namespace) -> int:
    """Show session contents."""
    session = args.session
    lines = args.lines
    head = args.head

    events_file = LOG_DIR / session / "events.jsonl"
    if not events_file.exists():
        print_error(f"Session not found: {session}")
        return 1

    console.print()
    console.print(f"[bold cyan]Session: {session}[/bold cyan]")
    console.print()

    events = []
    with open(events_file) as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # Skip malformed JSON lines

    if head:
        display_events = events[:lines]
    else:
        display_events = events[-lines:]

    for event in display_events:
        ts = event.get("ts", 0)
        event_type = event.get("event", "unknown")
        topic = event.get("topic", "")
        data = event.get("data", {})

        if event_type == "bus.publish":
            if topic == "error":
                console.print(f"[dim]{ts:.3f}[/dim] [red][{topic}][/red] {data}")
            elif topic == "heartbeat":
                console.print(f"[dim]{ts:.3f}[/dim] [dim][{topic}][/dim] {data}")
            else:
                console.print(f"[dim]{ts:.3f}[/dim] [cyan][{topic}][/cyan] {data}")
        else:
            console.print(f"[dim]{ts:.3f}[/dim] [yellow]{event_type}[/yellow]")

    console.print()
    console.print(f"[dim]Showing {len(display_events)} of {len(events)} events[/dim]")

    return 0
