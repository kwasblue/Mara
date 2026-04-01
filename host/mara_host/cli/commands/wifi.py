# mara_host/cli/commands/wifi.py
"""Wi-Fi control commands."""

import argparse

from rich.table import Table

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from mara_host.cli.context import CLIContext, run_with_context
from mara_host.cli.commands._common import add_port_arg, cmd_help


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register wifi command group."""
    wifi_parser = subparsers.add_parser(
        "wifi",
        help="Wi-Fi network control",
        description="Control Wi-Fi STA/AP mode on the robot",
    )

    wifi_sub = wifi_parser.add_subparsers(
        dest="wifi_cmd",
        title="wifi commands",
        metavar="<subcommand>",
    )

    # wifi status
    status_p = wifi_sub.add_parser("status", help="Show Wi-Fi connection status")
    add_port_arg(status_p)
    status_p.set_defaults(func=cmd_status)

    # wifi join
    join_p = wifi_sub.add_parser("join", help="Join a Wi-Fi network")
    join_p.add_argument("ssid", help="Network SSID")
    join_p.add_argument("password", help="Network password")
    join_p.add_argument(
        "--timeout",
        type=int,
        default=10000,
        help="Connection timeout in ms (default: 10000)",
    )
    join_p.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for connection to complete",
    )
    add_port_arg(join_p)
    join_p.set_defaults(func=cmd_join)

    # wifi disconnect
    disconnect_p = wifi_sub.add_parser(
        "disconnect", help="Disconnect from current network"
    )
    add_port_arg(disconnect_p)
    disconnect_p.set_defaults(func=cmd_disconnect)

    # wifi scan
    scan_p = wifi_sub.add_parser("scan", help="Scan for available networks")
    add_port_arg(scan_p)
    scan_p.set_defaults(func=cmd_scan)

    # Default handler
    wifi_parser.set_defaults(func=lambda args: cmd_help(wifi_parser))


@run_with_context
async def cmd_status(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Show Wi-Fi status."""
    result = await ctx.wifi_service.status()

    if result.ok:
        data = result.data or {}
        table = Table(title="Wi-Fi Status", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Mode", data.get("mode", "unknown"))
        table.add_row("SSID", data.get("ssid", "-"))
        table.add_row("Connected", str(data.get("connected", False)))
        table.add_row("IP Address", data.get("ip", "-"))
        table.add_row("RSSI", f"{data.get('rssi', 0)} dBm")
        table.add_row("MAC", data.get("mac", "-"))

        if data.get("ap_active"):
            table.add_row("AP SSID", data.get("ap_ssid", "-"))
            table.add_row("AP IP", data.get("ap_ip", "-"))

        console.print(table)
        return 0
    else:
        print_error(f"Failed to get status: {result.error}")
        return 1


@run_with_context
async def cmd_join(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Connect to Wi-Fi network."""
    print_info(f"Connecting to '{args.ssid}'...")

    result = await ctx.wifi_service.join(
        ssid=args.ssid,
        password=args.password,
        wait_for_connect=not args.no_wait,
        timeout_ms=args.timeout,
    )

    if result.ok:
        data = result.data or {}
        print_success(f"Connected to '{args.ssid}'")
        if data.get("ip"):
            console.print(f"  IP Address: {data['ip']}")
        return 0
    else:
        print_error(f"Failed to connect: {result.error}")
        return 1


@run_with_context
async def cmd_disconnect(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Disconnect from current network."""
    result = await ctx.wifi_service.disconnect()

    if result.ok:
        print_success("Disconnected from Wi-Fi")
        return 0
    else:
        print_error(f"Failed to disconnect: {result.error}")
        return 1


@run_with_context
async def cmd_scan(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Scan for available networks."""
    print_info("Scanning for networks...")

    result = await ctx.wifi_service.scan()

    if result.ok:
        data = result.data or {}
        networks = data.get("networks", [])

        if not networks:
            console.print("No networks found")
            return 0

        table = Table(title=f"Found {len(networks)} Networks")
        table.add_column("SSID", style="cyan")
        table.add_column("RSSI", justify="right")
        table.add_column("Channel", justify="center")
        table.add_column("Security")

        for net in sorted(networks, key=lambda x: x.get("rssi", -100), reverse=True):
            rssi = net.get("rssi", 0)
            signal = "Strong" if rssi > -50 else "Good" if rssi > -70 else "Weak"
            table.add_row(
                net.get("ssid", "?"),
                f"{rssi} dBm ({signal})",
                str(net.get("channel", "?")),
                net.get("security", "Open"),
            )

        console.print(table)
        return 0
    else:
        print_error(f"Scan failed: {result.error}")
        return 1
