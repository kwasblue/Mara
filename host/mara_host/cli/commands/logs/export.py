# cli/commands/logs/export.py
"""Export session command."""

import argparse
import csv
import json

from mara_host.cli.console import console, print_error, print_success
from ._common import LOG_DIR


def cmd_export(args: argparse.Namespace) -> int:
    """Export session to different format."""
    session = args.session
    output = args.output
    fmt = args.format

    events_file = LOG_DIR / session / "events.jsonl"
    if not events_file.exists():
        print_error(f"Session not found: {session}")
        return 1

    if not output:
        output = f"{session}.{fmt}"

    console.print()
    console.print(f"[bold cyan]Exporting: {session}[/bold cyan]")
    console.print(f"  Format: {fmt}")
    console.print(f"  Output: {output}")
    console.print()

    events = []
    with open(events_file) as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # Skip malformed JSON lines

    if fmt == "json":
        with open(output, "w") as f:
            json.dump(events, f, indent=2)

    elif fmt == "csv":
        with open(output, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "event", "topic", "data"])

            for event in events:
                writer.writerow([
                    event.get("ts", ""),
                    event.get("event", ""),
                    event.get("topic", ""),
                    json.dumps(event.get("data", {})),
                ])

    print_success(f"Exported {len(events)} events to {output}")

    return 0
