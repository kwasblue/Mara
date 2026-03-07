# mara_host/cli/commands/run/serial.py
"""Serial transport runtime command."""

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


def cmd_serial(args: argparse.Namespace) -> int:
    """Connect via serial port."""
    port = args.port
    baudrate = args.baudrate
    shell = getattr(args, 'shell', False)
    log_level, log_dir = get_log_params(args)

    console.print()
    console.print("[bold cyan]Serial Connection[/bold cyan]")
    console.print(f"  Port: [green]{port}[/green]")
    console.print(f"  Baud: [green]{baudrate}[/green]")
    console.print(f"  Logs: [dim]{log_dir}[/dim]")
    console.print()

    if shell:
        return _run_serial_shell(port, baudrate, log_level, log_dir)
    else:
        return _run_serial_client(port, baudrate, log_level, log_dir)


def _run_serial_client(port: str, baudrate: int, log_level: int = logging.INFO, log_dir: str = "logs") -> int:
    """Run basic serial client."""
    from mara_host.command.client import MaraClient
    from mara_host.transport.serial_transport import SerialTransport

    async def main():
        transport = SerialTransport(port, baudrate=baudrate)
        client = MaraClient(transport, log_level=log_level, log_dir=log_dir)

        # Subscribe to events
        client.bus.subscribe("heartbeat", lambda d: console.print(f"[dim][HEARTBEAT][/dim] {d}"))
        client.bus.subscribe("pong", lambda d: console.print(f"[dim][PONG][/dim] {d}"))
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


def _run_serial_shell(port: str, baudrate: int, log_level: int = logging.INFO, log_dir: str = "logs") -> int:
    """Run interactive serial shell."""
    print_info("Launching interactive shell...")

    # Import and run the interactive shell
    try:
        from mara_host.examples.shells.interactive_shell import main as shell_main
        asyncio.run(shell_main())
        return 0
    except ImportError:
        print_error("Interactive shell not available")
        return 1
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted[/dim]")
        return 130
