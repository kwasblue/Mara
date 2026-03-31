# cli/commands/logs/_registry.py
"""Logs command registration."""

import argparse

from .list import cmd_list
from .show import cmd_show
from .tail import cmd_tail
from .search import cmd_search
from .stats import cmd_stats
from .delete import cmd_delete
from .export import cmd_export


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
