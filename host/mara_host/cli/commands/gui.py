# mara_host/cli/commands/gui.py
"""
GUI command for launching the MARA Control desktop application.

Usage:
    mara gui                     # Launch GUI
    mara gui --port /dev/ttyUSB0 # Launch and connect via serial
    mara gui --tcp 192.168.4.1   # Launch and connect via TCP
    mara gui --dev               # Launch with verbose logging
"""

import argparse
import sys


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the gui command."""
    parser = subparsers.add_parser(
        "gui",
        help="Launch the MARA Control GUI",
        description="Launch the MARA Control desktop application.",
    )

    # Connection options
    conn_group = parser.add_argument_group("Connection")
    conn_group.add_argument(
        "--port", "-p",
        help="Serial port to connect to on startup",
    )
    conn_group.add_argument(
        "--tcp", "-t",
        metavar="HOST",
        help="TCP host to connect to on startup",
    )
    conn_group.add_argument(
        "--tcp-port",
        type=int,
        default=3333,
        help="TCP port (default: 3333)",
    )

    # Dev mode
    parser.add_argument(
        "--dev", "-d",
        action="store_true",
        help="Enable dev mode with verbose logging",
    )

    parser.set_defaults(func=cmd_gui)


def cmd_gui(args: argparse.Namespace) -> int:
    """Launch the GUI application."""
    try:
        from mara_host.gui import run_app
    except ImportError as e:
        print(f"Error: GUI dependencies not installed.")
        print(f"Install with: pip install PySide6 pyqtgraph")
        print(f"\nDetails: {e}")
        return 1

    # Determine connection type
    port = args.port
    host = args.tcp
    tcp_port = args.tcp_port
    dev = args.dev

    # Launch
    return run_app(port=port, host=host, tcp_port=tcp_port, dev=dev)
