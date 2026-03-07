# mara_host/cli/commands/run/can.py
"""CAN transport runtime command."""

import argparse
import asyncio
import logging

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from ._common import get_log_params


def cmd_can(args: argparse.Namespace) -> int:
    """Connect via CAN bus."""
    channel = args.channel
    bustype = args.bustype
    node_id = args.node_id
    virtual = args.virtual
    log_level, log_dir = get_log_params(args)

    console.print()
    console.print("[bold cyan]CAN Bus Connection[/bold cyan]")
    console.print(f"  Channel: [green]{channel}[/green]")
    console.print(f"  Type: [green]{bustype}[/green]")
    console.print(f"  Node ID: [green]{node_id}[/green]")
    if virtual:
        console.print("  [yellow]Virtual mode (loopback)[/yellow]")
    console.print(f"  Logs: [dim]{log_dir}[/dim]")
    console.print()

    return _run_can_client(channel, bustype, node_id, virtual, log_level, log_dir)


def _run_can_client(channel: str, bustype: str, node_id: int, virtual: bool, log_level: int = logging.INFO, log_dir: str = "logs") -> int:
    """Run CAN client."""
    try:
        from mara_host.command.client import MaraClient
        from mara_host.transport.can_transport import CANTransport, VirtualCANTransport
        from mara_host.transport.can_defs import NodeState
    except ImportError as e:
        print_error(f"CAN support not available: {e}")
        print_info("Install python-can: pip install python-can")
        return 1

    async def main():
        # Create transport
        if virtual:
            transport = VirtualCANTransport(channel=channel, node_id=node_id)
        else:
            transport = CANTransport(
                channel=channel,
                bustype=bustype,
                node_id=node_id,
            )

        # Set up callbacks
        transport.set_encoder_callback(
            lambda nid, counts, vel: console.print(f"[dim][ENC][/dim] n={nid} c={counts} v={vel}")
        )
        transport.set_heartbeat_callback(
            lambda nid, uptime, state: console.print(f"[dim][HB][/dim] n={nid} up={uptime}ms {state.name}")
        )

        client = MaraClient(transport, connection_timeout_s=5.0, log_level=log_level, log_dir=log_dir)

        client.bus.subscribe("heartbeat", lambda d: console.print(f"[dim][HEARTBEAT][/dim] {d}"))
        client.bus.subscribe("pong", lambda d: console.print(f"[dim][PONG][/dim] {d}"))
        client.bus.subscribe("error", lambda e: console.print(f"[red][ERROR][/red] {e}"))

        await client.start()
        print_success(f"CAN client started (node_id={node_id})")

        try:
            while True:
                await asyncio.sleep(0.1)
        finally:
            await client.stop()
            print_info("CAN client stopped")

    try:
        asyncio.run(main())
        return 0
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted[/dim]")
        return 130
    except Exception as e:
        print_error(f"CAN connection failed: {e}")
        return 1
