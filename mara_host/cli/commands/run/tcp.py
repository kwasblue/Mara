# mara_host/cli/commands/run/tcp.py
"""TCP transport runtime command."""

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


def cmd_tcp(args: argparse.Namespace) -> int:
    """Connect via TCP/WiFi."""
    host = args.sta if args.sta else args.host
    port = args.port
    log_level, log_dir = get_log_params(args)

    mode = "STA" if args.sta else "AP"

    console.print()
    console.print("[bold cyan]TCP Connection[/bold cyan]")
    console.print(f"  Host: [green]{host}[/green]")
    console.print(f"  Port: [green]{port}[/green]")
    console.print(f"  Mode: [yellow]{mode}[/yellow]")
    console.print(f"  Logs: [dim]{log_dir}[/dim]")
    console.print()

    return _run_tcp_client(host, port, log_level, log_dir)


def _run_tcp_client(host: str, port: int, log_level: int = logging.INFO, log_dir: str = "logs") -> int:
    """Run TCP client."""
    from mara_host.command.client import MaraClient
    from mara_host.transport.tcp_transport import AsyncTcpTransport

    async def main():
        transport = AsyncTcpTransport(host=host, port=port)
        client = MaraClient(transport, connection_timeout_s=6.0, log_level=log_level, log_dir=log_dir)

        # Subscribe to events
        client.bus.subscribe("heartbeat", lambda d: console.print(f"[dim][HEARTBEAT][/dim] {d}"))
        client.bus.subscribe("pong", lambda d: console.print(f"[dim][PONG][/dim] {d}"))
        client.bus.subscribe("hello", lambda d: console.print(f"[green][HELLO][/green] {d}"))
        client.bus.subscribe("json", lambda d: console.print(f"[cyan][JSON][/cyan] {d}"))
        client.bus.subscribe("error", lambda e: console.print(f"[red][ERROR][/red] {e}"))

        await client.start()
        print_success("Connected")

        loop = asyncio.get_running_loop()
        last_ping = loop.time()

        try:
            while True:
                now = loop.time()
                if now - last_ping >= 5.0:
                    await client.send_ping()
                    last_ping = now
                await asyncio.sleep(0.1)
        finally:
            await client.stop()
            print_info("Disconnected")

    try:
        asyncio.run(main())
        return 0
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted[/dim]")
        return 130
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1
