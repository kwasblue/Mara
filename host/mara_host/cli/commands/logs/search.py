# cli/commands/logs/search.py
"""Search sessions command."""

import argparse
import json
import re

from mara_host.cli.console import console, print_error, print_info
from ._common import LOG_DIR, find_sessions


def cmd_search(args: argparse.Namespace) -> int:
    """Search sessions for pattern."""
    pattern = args.pattern
    session = args.session
    topic_filter = args.topic
    limit = args.limit

    console.print()
    console.print(f"[bold cyan]Searching for: {pattern}[/bold cyan]")
    console.print()

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        print_error(f"Invalid regex: {e}")
        return 1

    if session:
        sessions = [{"name": session, "events_file": LOG_DIR / session / "events.jsonl"}]
    else:
        sessions = find_sessions(LOG_DIR)

    matches = []

    for s in sessions:
        events_file = s.get("events_file") or (LOG_DIR / s["name"] / "events.jsonl")
        if not events_file.exists():
            continue

        with open(events_file) as f:
            for line_num, line in enumerate(f, 1):
                if len(matches) >= limit:
                    break

                if not line.strip():
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue  # Skip malformed JSON lines

                if topic_filter and event.get("topic") != topic_filter:
                    continue

                if regex.search(line):
                    matches.append({
                        "session": s["name"],
                        "line": line_num,
                        "event": event,
                    })

        if len(matches) >= limit:
            break

    if not matches:
        print_info("No matches found")
        return 0

    for m in matches:
        event = m["event"]
        topic = event.get("topic", event.get("event", ""))
        data = event.get("data", {})

        console.print(f"[dim]{m['session']}:{m['line']}[/dim] [{topic}] {data}")

    console.print()
    console.print(f"[dim]Found {len(matches)} match(es)[/dim]")

    return 0
