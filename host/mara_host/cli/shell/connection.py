# mara_host/cli/commands/run/shell/commands/connection.py
"""Connection management commands: connect, disconnect, ping, status."""

from .registry import command
from mara_host.cli.console import console, print_success, print_error, print_info


@command("connect", "Connect to robot (connect [serial|tcp|ble] ...)", group="Connection")
async def cmd_connect(shell, args: list[str]) -> None:
    """Connect to robot.

    Usage:
        connect                    - Connect with default settings
        connect serial /dev/ttyUSB0 [baudrate]
        connect tcp host [port]
        connect ble device_name [baudrate]
    """
    if shell.connected:
        print_info(f"Already connected to {shell.current_connection_info}")
        print_info("Use 'disconnect' first to connect to a different device")
        return

    # Parse connection args
    if not args:
        # Use defaults
        await shell.try_connect()
        return

    transport_type = args[0].lower()
    if transport_type == "serial":
        port = args[1] if len(args) > 1 else shell.default_args.port
        baudrate = int(args[2]) if len(args) > 2 else shell.default_args.baudrate
        await shell.try_connect("serial", port=port, baudrate=baudrate)
    elif transport_type == "tcp":
        host = args[1] if len(args) > 1 else shell.default_args.host
        port = int(args[2]) if len(args) > 2 else shell.default_args.tcp_port
        await shell.try_connect("tcp", host=host, port=port)
    elif transport_type == "ble":
        device_name = args[1] if len(args) > 1 else shell.default_args.ble_name
        baudrate = int(args[2]) if len(args) > 2 else shell.default_args.baudrate
        await shell.try_connect("ble", device_name=device_name, baudrate=baudrate)
    else:
        print_error(f"Unknown transport type: {transport_type}")
        console.print("Usage:")
        console.print("  connect                         - Connect with default settings")
        console.print("  connect serial /dev/ttyUSB0     - Serial connection")
        console.print("  connect tcp 192.168.1.100 3333  - TCP connection")
        console.print("  connect ble MARA-Robot          - Bluetooth connection")


@command("disconnect", "Disconnect from robot", group="Connection")
async def cmd_disconnect(shell, args: list[str]) -> None:
    """Disconnect from robot."""
    if not shell.connected:
        print_info("Not connected")
        return

    await shell.cleanup()
    print_success("Disconnected from robot")


@command("ping", "Send ping to robot", group="Connection")
async def cmd_ping(shell, args: list[str]) -> None:
    """Send ping."""
    if not shell.require_connection():
        return
    await shell.client.send_ping()
    print_info("Ping sent, awaiting pong...")


@command("status", "Show connection status", group="Connection")
async def cmd_status(shell, args: list[str]) -> None:
    """Show status."""
    console.print()
    console.print("[bold]Connection Status:[/bold]")
    if shell.connected:
        console.print(f"  Connected: [green]Yes[/green]")
        console.print(f"  Device: [cyan]{shell.current_connection_info}[/cyan]")

        # Show connection monitor stats
        if shell.client:
            stats = shell.client.connection.get_stats()
            time_since = shell.client.connection.time_since_last_message
            state = shell.client.connection.state.value

            console.print(f"  State: [cyan]{state}[/cyan]")
            if time_since is not None:
                console.print(f"  Last message: [cyan]{time_since:.2f}s ago[/cyan]")
            console.print(f"  Messages: [cyan]{stats.messages_received}[/cyan]")
            console.print(f"  Disconnects: [yellow]{stats.disconnects}[/yellow]")
            console.print(f"  Reconnects: [green]{stats.reconnects}[/green]")
            if stats.total_downtime_s > 0:
                console.print(f"  Total downtime: [red]{stats.total_downtime_s:.2f}s[/red]")

            # Check heartbeat task status
            hb_task = getattr(shell.client, '_heartbeat_task', None)
            if hb_task:
                hb_status = "running" if not hb_task.done() else "stopped"
                console.print(f"  Heartbeat task: [cyan]{hb_status}[/cyan]")
            else:
                console.print(f"  Heartbeat task: [red]not started[/red]")
    else:
        console.print(f"  Connected: [red]No[/red]")
        # Show default connection info
        if shell.default_args.transport == "serial":
            console.print(f"  Default: [dim]serial:{shell.default_args.port}[/dim]")
        elif shell.default_args.transport == "tcp":
            console.print(f"  Default: [dim]tcp:{shell.default_args.host}:{shell.default_args.tcp_port}[/dim]")
        else:
            console.print(f"  Default: [dim]ble:{shell.default_args.ble_name}[/dim]")
    console.print(f"  Events logged: [cyan]{len(shell.event_log)}[/cyan]")

    # Count heartbeats separately
    heartbeat_count = sum(1 for t, _ in shell.event_log if t == "heartbeat")
    if heartbeat_count > 0:
        console.print(f"  Heartbeats: [dim]{heartbeat_count}[/dim]")
