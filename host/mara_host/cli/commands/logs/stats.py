# cli/commands/logs/stats.py
"""Session statistics command."""

import argparse
import json

from rich.table import Table

from mara_host.cli.console import console, print_error
from ._common import LOG_DIR, format_size


def cmd_stats(args: argparse.Namespace) -> int:
    """Show session statistics."""
    session = args.session

    events_file = LOG_DIR / session / "events.jsonl"
    if not events_file.exists():
        print_error(f"Session not found: {session}")
        return 1

    console.print()
    console.print(f"[bold cyan]Session Statistics: {session}[/bold cyan]")
    console.print()

    topic_counts: dict[str, int] = {}
    event_type_counts: dict[str, int] = {}
    first_ts = None
    last_ts = None
    total_events = 0

    with open(events_file) as f:
        for line in f:
            if not line.strip():
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue  # Skip malformed JSON lines

            total_events += 1

            ts = event.get("ts", 0)
            if first_ts is None:
                first_ts = ts
            last_ts = ts

            topic = event.get("topic", "")
            if topic:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

            event_type = event.get("event", "unknown")
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

    if first_ts is not None and last_ts is not None:
        duration = last_ts - first_ts
    else:
        duration = 0

    size = events_file.stat().st_size

    console.print(f"  Total events: [green]{total_events}[/green]")
    console.print(f"  Duration: [green]{duration:.1f}s[/green]")
    console.print(f"  File size: [green]{format_size(size)}[/green]")
    if duration > 0:
        console.print(f"  Events/sec: [green]{total_events / duration:.1f}[/green]")
    console.print()

    if topic_counts:
        console.print("[bold]Events by Topic:[/bold]")
        table = Table(show_header=True)
        table.add_column("Topic", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Rate", justify="right")

        for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
            rate = f"{count / duration:.1f}/s" if duration > 0 else "-"
            table.add_row(topic, str(count), rate)

        console.print(table)

    return 0
