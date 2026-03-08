# mara_host/cli/commands/monitor.py
"""Live monitoring dashboard for MARA CLI."""

import argparse
import asyncio
import time
from typing import Any
from dataclasses import dataclass, field

from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import Group

from mara_host.cli.console import (
    console,
    print_error,
)


@dataclass
class MonitorState:
    """State for the monitor display."""
    connected: bool = False
    uptime_ms: int = 0
    mode: str = "UNKNOWN"
    armed: bool = False

    # Telemetry
    encoders: dict[int, tuple[int, float]] = field(default_factory=dict)  # id -> (counts, velocity)
    motors: dict[int, float] = field(default_factory=dict)  # id -> speed
    servos: dict[int, float] = field(default_factory=dict)  # id -> angle
    imu_accel: tuple[float, float, float] = (0.0, 0.0, 0.0)
    imu_gyro: tuple[float, float, float] = (0.0, 0.0, 0.0)
    ultrasonic: dict[int, float] = field(default_factory=dict)  # id -> distance_m

    # Stats
    msg_count: int = 0
    error_count: int = 0
    last_heartbeat: float = 0.0
    start_time: float = field(default_factory=time.time)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register monitor command."""
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Live monitoring dashboard",
        description="Real-time dashboard showing robot telemetry",
    )

    monitor_parser.add_argument(
        "-t", "--transport",
        choices=["serial", "tcp"],
        default="serial",
        help="Transport type (default: serial)",
    )
    monitor_parser.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port (for serial transport)",
    )
    monitor_parser.add_argument(
        "-H", "--host",
        default="192.168.4.1",
        help="Host address (for TCP transport)",
    )
    monitor_parser.add_argument(
        "--tcp-port",
        type=int,
        default=3333,
        help="TCP port (for TCP transport)",
    )
    monitor_parser.add_argument(
        "--refresh",
        type=float,
        default=0.1,
        help="Refresh rate in seconds (default: 0.1)",
    )

    monitor_parser.set_defaults(func=cmd_monitor)


def cmd_monitor(args: argparse.Namespace) -> int:
    """Launch live monitoring dashboard."""
    console.print()
    console.print("[bold cyan]MARA Live Monitor[/bold cyan]")
    console.print("[dim]Press Ctrl+C to exit[/dim]")
    console.print()

    return asyncio.run(_run_monitor(args))


async def _run_monitor(args: argparse.Namespace) -> int:
    """Run the live monitor."""
    from mara_host.command.client import MaraClient

    # Create transport
    if args.transport == "serial":
        from mara_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)
    else:
        from mara_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.host, port=args.tcp_port)

    client = MaraClient(transport, connection_timeout_s=6.0)
    state = MonitorState()

    # Subscribe to events
    def on_heartbeat(data: Any) -> None:
        state.last_heartbeat = time.time()
        state.msg_count += 1
        if isinstance(data, dict):
            state.uptime_ms = data.get("uptime_ms", state.uptime_ms)
            state.mode = data.get("mode", state.mode)

    def on_telemetry(data: Any) -> None:
        state.msg_count += 1
        if isinstance(data, dict):
            # Parse telemetry data
            if "encoders" in data:
                for enc in data["encoders"]:
                    state.encoders[enc.get("id", 0)] = (enc.get("counts", 0), enc.get("velocity", 0.0))
            if "imu" in data:
                imu = data["imu"]
                state.imu_accel = (imu.get("ax", 0), imu.get("ay", 0), imu.get("az", 0))
                state.imu_gyro = (imu.get("gx", 0), imu.get("gy", 0), imu.get("gz", 0))
            if "ultrasonic" in data:
                for us in data["ultrasonic"]:
                    state.ultrasonic[us.get("id", 0)] = us.get("distance_m", 0)

    def on_error(data: Any) -> None:
        state.error_count += 1
        state.msg_count += 1

    client.bus.subscribe("heartbeat", on_heartbeat)
    client.bus.subscribe("telemetry", on_telemetry)
    client.bus.subscribe("json", lambda d: setattr(state, 'msg_count', state.msg_count + 1))
    client.bus.subscribe("error", on_error)

    try:
        await client.start()
        state.connected = True
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    # Run live display
    try:
        with Live(_generate_display(state, args), refresh_per_second=10, console=console) as live:
            while True:
                live.update(_generate_display(state, args))
                await asyncio.sleep(args.refresh)
    except KeyboardInterrupt:
        pass
    finally:
        await client.stop()

    return 0


def _generate_display(state: MonitorState, args: argparse.Namespace) -> Panel:
    """Generate the monitor display."""
    # Connection status
    if state.connected:
        conn_status = "[green]CONNECTED[/green]"
        heartbeat_age = time.time() - state.last_heartbeat if state.last_heartbeat > 0 else float('inf')
        if heartbeat_age > 5:
            conn_status = "[yellow]NO HEARTBEAT[/yellow]"
    else:
        conn_status = "[red]DISCONNECTED[/red]"

    elapsed = time.time() - state.start_time

    # Build status line
    status_parts = [
        f"Status: {conn_status}",
        f"Mode: [cyan]{state.mode}[/cyan]",
        f"Uptime: [dim]{state.uptime_ms // 1000}s[/dim]",
        f"Messages: [dim]{state.msg_count}[/dim]",
        f"Errors: [{'red' if state.error_count > 0 else 'dim'}]{state.error_count}[/]",
    ]
    status_line = Text(" | ".join(status_parts))

    # Encoders table
    enc_table = Table(title="Encoders", show_header=True, header_style="bold", box=None)
    enc_table.add_column("ID", style="cyan", width=4)
    enc_table.add_column("Counts", justify="right", width=10)
    enc_table.add_column("Velocity", justify="right", width=10)

    if state.encoders:
        for enc_id, (counts, vel) in sorted(state.encoders.items()):
            enc_table.add_row(str(enc_id), str(counts), f"{vel:.2f}")
    else:
        enc_table.add_row("-", "-", "-")

    # IMU display
    ax, ay, az = state.imu_accel
    gx, gy, gz = state.imu_gyro

    imu_table = Table(title="IMU", show_header=True, header_style="bold", box=None)
    imu_table.add_column("Axis", style="cyan", width=4)
    imu_table.add_column("Accel (g)", justify="right", width=10)
    imu_table.add_column("Gyro (dps)", justify="right", width=10)

    imu_table.add_row("X", f"{ax:.3f}", f"{gx:.1f}")
    imu_table.add_row("Y", f"{ay:.3f}", f"{gy:.1f}")
    imu_table.add_row("Z", f"{az:.3f}", f"{gz:.1f}")

    # Ultrasonic display
    us_text = Text("Ultrasonic: ")
    if state.ultrasonic:
        for us_id, dist in sorted(state.ultrasonic.items()):
            color = "green" if dist > 0.3 else ("yellow" if dist > 0.1 else "red")
            us_text.append(f"[{us_id}]={dist:.2f}m ", style=color)
    else:
        us_text.append("[dim]No data[/dim]")

    # Motors display
    motors_text = Text("Motors: ")
    if state.motors:
        for m_id, speed in sorted(state.motors.items()):
            color = "green" if abs(speed) < 0.5 else "yellow"
            motors_text.append(f"[{m_id}]={speed:.0%} ", style=color)
    else:
        motors_text.append("[dim]No data[/dim]")

    # Combine all elements
    content = Group(
        status_line,
        Text(""),
        enc_table,
        Text(""),
        imu_table,
        Text(""),
        us_text,
        motors_text,
        Text(""),
        Text(f"[dim]Runtime: {elapsed:.1f}s | Refresh: {args.refresh}s[/dim]"),
    )

    transport_info = f"Serial: {args.port}" if args.transport == "serial" else f"TCP: {args.host}:{args.tcp_port}"

    return Panel(
        content,
        title=f"[bold cyan]MARA Monitor[/bold cyan] - {transport_info}",
        border_style="blue",
    )
