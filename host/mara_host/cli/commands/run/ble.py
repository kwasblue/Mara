# mara_host/cli/commands/run/ble.py
"""Bluetooth Classic SPP transport runtime command."""

import argparse
import asyncio
import logging

from mara_host.cli.console import console, print_success, print_error, print_info
from ._common import get_log_params


def cmd_ble(args: argparse.Namespace) -> int:
    """Connect via Bluetooth Classic SPP."""
    device_name = args.ble_name
    baudrate = args.baudrate
    log_level, log_dir = get_log_params(args)

    console.print()
    console.print("[bold cyan]Bluetooth SPP Connection[/bold cyan]")
    console.print(f"  Device: [green]{device_name}[/green]")
    console.print(f"  Baud: [green]{baudrate}[/green]")
    console.print(f"  Logs: [dim]{log_dir}[/dim]")
    console.print()

    if args.shell:
        shell_args = argparse.Namespace(
            transport="ble",
            port=None,
            host=None,
            tcp_port=3333,
            ble_name=device_name,
            baudrate=baudrate,
        )
        shell_args.log_level = args.log_level
        shell_args.log_dir = args.log_dir
        from .shell import cmd_shell
        return cmd_shell(shell_args)

    return _run_ble_client(device_name, baudrate, log_level, log_dir)


def _run_ble_client(
    device_name: str,
    baudrate: int,
    log_level: int = logging.INFO,
    log_dir: str = "logs",
) -> int:
    """Run basic BLE client."""
    from mara_host.command.client import MaraClient
    from mara_host.transport.bluetooth_transport import BluetoothSerialTransport

    async def main():
        transport = BluetoothSerialTransport.auto(device_name=device_name, baudrate=baudrate)
        client = MaraClient(transport, log_level=log_level, log_dir=log_dir)

        client.bus.subscribe("heartbeat", lambda d: console.print(f"[dim][HEARTBEAT][/dim] {d}"))
        client.bus.subscribe("pong", lambda d: console.print(f"[dim][PONG][/dim] {d}"))
        client.bus.subscribe("error", lambda e: console.print(f"[red][ERROR][/red] {e}"))

        await client.start()
        print_success(f"Connected via {transport.port}")

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
        print_error(f"BLE connection failed: {e}")
        return 1
