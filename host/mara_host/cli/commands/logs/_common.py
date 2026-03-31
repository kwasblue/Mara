# cli/commands/logs/_common.py
"""Common utilities for logs commands."""

from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Default log directory
LOG_DIR = Path("logs")


def find_sessions(log_dir: Path) -> List[Dict]:
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

        size = events_file.stat().st_size
        mtime = datetime.fromtimestamp(events_file.stat().st_mtime)

        line_count = 0
        try:
            with open(events_file) as f:
                for _ in f:
                    line_count += 1
        except (OSError, IOError):
            line_count = size // 100  # Estimate on read error

        sessions.append({
            "name": session_dir.name,
            "path": session_dir,
            "events_file": events_file,
            "size": size,
            "mtime": mtime,
            "event_count": line_count,
        })

    sessions.sort(key=lambda s: s["mtime"], reverse=True)
    return sessions


def format_size(size_bytes: int) -> str:
    """Format size in human-readable form."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def print_event(event: dict) -> None:
    """Print a single event."""
    from mara_host.cli.console import console

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
