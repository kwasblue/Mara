# robot_host/cli/commands/logs.py
"""Log viewing and management commands for MARA CLI."""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

from robot_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
    print_warning,
)


# Default log directory
LOG_DIR = Path("logs")


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register logs commands."""
    logs_parser = subparsers.add_parser(
        "logs",
        help="View and manage recorded sessions",
        description="Browse, search, and analyze recorded telemetry sessions",
    )

    logs_sub = logs_parser.add_subparsers(
        dest="logs_cmd",
        title="log commands",
        metavar="<subcommand>",
    )

    # list
    list_p = logs_sub.add_parser(
        "list",
        help="List recorded sessions",
    )
    list_p.add_argument(
        "-d", "--dir",
        default="logs",
        help="Log directory (default: logs/)",
    )
    list_p.add_argument(
        "-n", "--limit",
        type=int,
        default=20,
        help="Maximum sessions to show (default: 20)",
    )
    list_p.set_defaults(func=cmd_list)

    # show
    show_p = logs_sub.add_parser(
        "show",
        help="Show session contents",
    )
    show_p.add_argument("session", help="Session name")
    show_p.add_argument(
        "-n", "--lines",
        type=int,
        default=50,
        help="Number of lines to show (default: 50)",
    )
    show_p.add_argument(
        "--head",
        action="store_true",
        help="Show first lines instead of last",
    )
    show_p.set_defaults(func=cmd_show)

    # tail
    tail_p = logs_sub.add_parser(
        "tail",
        help="Follow session log in real-time",
    )
    tail_p.add_argument("session", help="Session name")
    tail_p.add_argument(
        "-n", "--lines",
        type=int,
        default=10,
        help="Initial lines to show (default: 10)",
    )
    tail_p.set_defaults(func=cmd_tail)

    # search
    search_p = logs_sub.add_parser(
        "search",
        help="Search sessions for pattern",
    )
    search_p.add_argument("pattern", help="Search pattern (regex)")
    search_p.add_argument(
        "-s", "--session",
        help="Search specific session (default: all)",
    )
    search_p.add_argument(
        "-t", "--topic",
        help="Filter by event topic",
    )
    search_p.add_argument(
        "-n", "--limit",
        type=int,
        default=100,
        help="Maximum matches (default: 100)",
    )
    search_p.set_defaults(func=cmd_search)

    # stats
    stats_p = logs_sub.add_parser(
        "stats",
        help="Show session statistics",
    )
    stats_p.add_argument("session", help="Session name")
    stats_p.set_defaults(func=cmd_stats)

    # delete
    delete_p = logs_sub.add_parser(
        "delete",
        help="Delete a session",
    )
    delete_p.add_argument("session", help="Session name to delete")
    delete_p.add_argument(
        "-f", "--force",
        action="store_true",
        help="Skip confirmation",
    )
    delete_p.set_defaults(func=cmd_delete)

    # export
    export_p = logs_sub.add_parser(
        "export",
        help="Export session to different format",
    )
    export_p.add_argument("session", help="Session name")
    export_p.add_argument(
        "-o", "--output",
        help="Output file (default: <session>.csv)",
    )
    export_p.add_argument(
        "-f", "--format",
        choices=["csv", "json"],
        default="csv",
        help="Export format (default: csv)",
    )
    export_p.set_defaults(func=cmd_export)

    # Default
    logs_parser.set_defaults(func=cmd_list)


def _find_sessions(log_dir: Path) -> list[dict]:
    """Find all sessions in the log directory."""
    sessions = []

    if not log_dir.exists():
        return sessions

    for session_dir in log_dir.iterdir():
        if not session_dir.is_dir():
            continue

        events_file = session_dir / "events.jsonl"
        if not events_file.exists():
            continue

        # Get stats
        size = events_file.stat().st_size
        mtime = datetime.fromtimestamp(events_file.stat().st_mtime)

        # Count events (estimate from file size)
        line_count = 0
        try:
            with open(events_file) as f:
                for _ in f:
                    line_count += 1
        except:
            line_count = size // 100  # rough estimate

        sessions.append({
            "name": session_dir.name,
            "path": session_dir,
            "events_file": events_file,
            "size": size,
            "mtime": mtime,
            "event_count": line_count,
        })

    # Sort by modification time (newest first)
    sessions.sort(key=lambda s: s["mtime"], reverse=True)
    return sessions


def cmd_list(args: argparse.Namespace) -> int:
    """List recorded sessions."""
    log_dir = Path(args.dir)
    limit = args.limit

    sessions = _find_sessions(log_dir)

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
        size_str = _format_size(s["size"])
        table.add_row(s["name"], date_str, str(s["event_count"]), size_str)

    console.print(table)

    if len(sessions) > limit:
        console.print(f"\n[dim]Showing {limit} of {len(sessions)} sessions[/dim]")

    return 0


def _format_size(size_bytes: int) -> str:
    """Format size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def cmd_show(args: argparse.Namespace) -> int:
    """Show session contents."""
    session = args.session
    lines = args.lines
    head = args.head

    # Find session
    events_file = LOG_DIR / session / "events.jsonl"
    if not events_file.exists():
        print_error(f"Session not found: {session}")
        return 1

    console.print()
    console.print(f"[bold cyan]Session: {session}[/bold cyan]")
    console.print()

    # Read events
    events = []
    with open(events_file) as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except:
                    pass

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

    import time

    # Show initial lines
    with open(events_file) as f:
        lines = f.readlines()

    for line in lines[-initial_lines:]:
        if line.strip():
            try:
                event = json.loads(line)
                _print_event(event)
            except:
                pass

    # Follow for new lines
    try:
        with open(events_file) as f:
            # Seek to end
            f.seek(0, 2)

            while True:
                line = f.readline()
                if line:
                    try:
                        event = json.loads(line)
                        _print_event(event)
                    except:
                        pass
                else:
                    time.sleep(0.1)

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped[/dim]")

    return 0


def _print_event(event: dict) -> None:
    """Print a single event."""
    ts = event.get("ts", 0)
    event_type = event.get("event", "unknown")
    topic = event.get("topic", "")
    data = event.get("data", {})

    if event_type == "bus.publish":
        if topic == "error":
            console.print(f"[dim]{ts:.3f}[/dim] [red][{topic}][/red] {data}")
        else:
            console.print(f"[dim]{ts:.3f}[/dim] [cyan][{topic}][/cyan] {data}")
    else:
        console.print(f"[dim]{ts:.3f}[/dim] [yellow]{event_type}[/yellow]")


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

    # Find sessions to search
    if session:
        sessions = [{"name": session, "events_file": LOG_DIR / session / "events.jsonl"}]
    else:
        sessions = _find_sessions(LOG_DIR)

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
                except:
                    continue

                # Filter by topic
                if topic_filter and event.get("topic") != topic_filter:
                    continue

                # Search in the line
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
        ts = event.get("ts", 0)
        topic = event.get("topic", event.get("event", ""))
        data = event.get("data", {})

        console.print(f"[dim]{m['session']}:{m['line']}[/dim] [{topic}] {data}")

    console.print()
    console.print(f"[dim]Found {len(matches)} match(es)[/dim]")

    return 0


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

    # Analyze events
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
            except:
                continue

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

    # Duration
    if first_ts is not None and last_ts is not None:
        duration = last_ts - first_ts
    else:
        duration = 0

    # File size
    size = events_file.stat().st_size

    # Summary
    console.print(f"  Total events: [green]{total_events}[/green]")
    console.print(f"  Duration: [green]{duration:.1f}s[/green]")
    console.print(f"  File size: [green]{_format_size(size)}[/green]")
    console.print(f"  Events/sec: [green]{total_events / duration:.1f}[/green]" if duration > 0 else "")
    console.print()

    # Topic breakdown
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

    # Calculate size
    total_size = sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file())
    console.print(f"  Size: {_format_size(total_size)}")

    if not force:
        from rich.prompt import Confirm
        if not Confirm.ask("[red]Are you sure?[/red]", default=False):
            console.print("[dim]Cancelled[/dim]")
            return 0

    # Delete
    import shutil
    shutil.rmtree(session_dir)
    print_success(f"Deleted session: {session}")

    return 0


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
                except:
                    pass

    if fmt == "json":
        with open(output, "w") as f:
            json.dump(events, f, indent=2)

    elif fmt == "csv":
        import csv

        # Flatten events for CSV
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
