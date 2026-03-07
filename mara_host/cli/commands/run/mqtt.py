# mara_host/cli/commands/run/mqtt.py
"""MQTT transport runtime command (placeholder)."""

import argparse

from mara_host.cli.console import (
    console,
    print_warning,
    print_info,
)


def cmd_mqtt(args: argparse.Namespace) -> int:
    """Connect via MQTT."""
    host = args.host
    port = args.port
    topic_prefix = args.topic_prefix

    console.print()
    console.print("[bold cyan]MQTT Connection[/bold cyan]")
    console.print(f"  Broker: [green]{host}:{port}[/green]")
    console.print(f"  Topic prefix: [green]{topic_prefix}[/green]")
    console.print()

    print_warning("MQTT transport is a work in progress")
    print_info("Use 'mara run serial' or 'mara run tcp' for now")

    return 0
