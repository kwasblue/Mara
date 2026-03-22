# mara_host/cli/commands/monitor.py
"""Live monitoring dashboard for MARA CLI."""

import argparse
import asyncio
import time
from dataclasses import dataclass, field

from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.layout import Layout

from mara_host.cli.console import console, print_error
from mara_host.cli.context import CLIContext
from mara_host.cli.cli_config import get_serial_port as _get_port


@dataclass
class MonitorState:
    """State for the monitor display."""

    connected: bool = False
    armed: bool = False
    state: str = "UNKNOWN"
    uptime_ms: int = 0

    # IMU
    imu_ax: float = 0.0
    imu_ay: float = 0.0
    imu_az: float = 0.0
    imu_gx: float = 0.0
    imu_gy: float = 0.0
    imu_gz: float = 0.0

    # Encoders: {id: (ticks, velocity)}
    encoders: dict[int, tuple[int, float]] = field(default_factory=dict)

    # Motors: {id: speed}
    motors: dict[int, float] = field(default_factory=dict)

    # Servos: {id: angle}
    servos: dict[int, float] = field(default_factory=dict)

    # Ultrasonic: {id: distance_m}
    ultrasonic: dict[int, float] = field(default_factory=dict)

    # Stats
    msg_count: int = 0
    telem_rate: float = 0.0
    error_count: int = 0
    last_telem_time: float = 0.0
    start_time: float = field(default_factory=time.time)

    # For rate calculation
    _telem_times: list = field(default_factory=list)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register monitor command."""
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Live monitoring dashboard",
        description="Real-time dashboard showing robot telemetry",
    )

    monitor_parser.add_argument(
        "-p", "--port",
        default=_get_port(),
        help="Serial port",
    )
    monitor_parser.add_argument(
        "--tcp",
        metavar="HOST",
        help="Use TCP transport (e.g., 192.168.4.1)",
    )
    monitor_parser.add_argument(
        "--tcp-port",
        type=int,
        default=3333,
        help="TCP port (default: 3333)",
    )
    monitor_parser.add_argument(
        "--refresh",
        type=float,
        default=0.1,
        help="Display refresh rate in seconds (default: 0.1)",
    )
    monitor_parser.add_argument(
        "--interval",
        type=int,
        default=50,
        help="Telemetry interval in ms (default: 50)",
    )
    monitor_parser.add_argument(
        "--compact",
        action="store_true",
        help="Use compact display mode",
    )

    monitor_parser.set_defaults(func=cmd_monitor)


def cmd_monitor(args: argparse.Namespace) -> int:
    """Launch live monitoring dashboard."""
    return asyncio.run(_run_monitor(args))


async def _run_monitor(args: argparse.Namespace) -> int:
    """Run the live monitor with CLIContext."""
    from mara_host.services.telemetry import TelemetryService

    state = MonitorState()

    # Create context
    ctx = CLIContext(
        port=args.port,
        host=getattr(args, "tcp", None),
        tcp_port=args.tcp_port,
        verbose=not getattr(args, "quiet", False),
    )

    try:
        # Connect (this also starts telemetry and arms)
        await ctx.connect()
        state.connected = True
        state.armed = True

        # Get telemetry service from context
        telemetry = ctx._telemetry

        # Set up telemetry callbacks
        def on_imu(imu_data):
            state.imu_ax = imu_data.ax
            state.imu_ay = imu_data.ay
            state.imu_az = imu_data.az
            state.imu_gx = imu_data.gx
            state.imu_gy = imu_data.gy
            state.imu_gz = imu_data.gz
            _record_telem(state)

        def on_encoder(enc_data):
            state.encoders[enc_data.encoder_id] = (enc_data.ticks, enc_data.velocity)
            _record_telem(state)

        def on_state_change(new_state):
            state.state = new_state

        def on_raw(data):
            state.msg_count += 1
            # Extract additional data
            if "uptime_ms" in data:
                state.uptime_ms = data["uptime_ms"]
            if "motors" in data:
                for m in data["motors"]:
                    state.motors[m.get("id", 0)] = m.get("speed", 0.0)
            if "servos" in data:
                for s in data["servos"]:
                    state.servos[s.get("id", 0)] = s.get("angle", 0.0)
            if "ultrasonic" in data:
                for u in data["ultrasonic"]:
                    state.ultrasonic[u.get("id", 0)] = u.get("distance_m", 0.0)

        telemetry.on_imu(on_imu)
        telemetry.on_encoder(on_encoder)
        telemetry.on_state(on_state_change)
        telemetry.on_raw(on_raw)

        # Update telemetry interval if different
        if args.interval != 100:  # CLIContext defaults to 100ms
            await ctx.client.send_reliable(
                "CMD_TELEM_SET_INTERVAL",
                {"interval_ms": args.interval},
            )

        # Run live display
        console.print()
        console.print("[bold cyan]MARA Live Monitor[/bold cyan]")
        console.print("[dim]Press Ctrl+C to exit[/dim]")
        console.print()

        with Live(
            _generate_display(state, args),
            refresh_per_second=int(1 / args.refresh),
            console=console,
        ) as live:
            while True:
                # Update state from telemetry service
                snapshot = telemetry.get_snapshot()
                state.state = snapshot.state

                live.update(_generate_display(state, args))
                await asyncio.sleep(args.refresh)

    except KeyboardInterrupt:
        console.print("\n[dim]Monitor stopped[/dim]")
    except Exception as e:
        print_error(f"Monitor error: {e}")
        return 1
    finally:
        await ctx.disconnect()

    return 0


def _record_telem(state: MonitorState) -> None:
    """Record telemetry timestamp for rate calculation."""
    now = time.time()
    state.last_telem_time = now
    state._telem_times.append(now)

    # Keep last 20 samples for rate calculation
    if len(state._telem_times) > 20:
        state._telem_times = state._telem_times[-20:]

    # Calculate rate
    if len(state._telem_times) >= 2:
        dt = state._telem_times[-1] - state._telem_times[0]
        if dt > 0:
            state.telem_rate = (len(state._telem_times) - 1) / dt


def _generate_display(state: MonitorState, args: argparse.Namespace) -> Panel:
    """Generate the monitor display."""
    # Connection status
    if state.connected:
        conn_status = "[green]●[/green] CONNECTED"
        telem_age = time.time() - state.last_telem_time if state.last_telem_time > 0 else float("inf")
        if telem_age > 2:
            conn_status = "[yellow]●[/yellow] NO DATA"
    else:
        conn_status = "[red]●[/red] DISCONNECTED"

    elapsed = time.time() - state.start_time

    # Status line
    status_parts = [
        conn_status,
        f"State: [cyan]{state.state}[/cyan]",
        f"Rate: [green]{state.telem_rate:.0f}Hz[/green]" if state.telem_rate > 0 else "Rate: [dim]--[/dim]",
        f"Msgs: [dim]{state.msg_count}[/dim]",
    ]
    status_line = Text(" │ ".join(status_parts))

    if args.compact:
        return _generate_compact_display(state, args, status_line, elapsed)

    # Full display
    # IMU Table
    imu_table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    imu_table.add_column("IMU", width=6)
    imu_table.add_column("X", justify="right", width=8)
    imu_table.add_column("Y", justify="right", width=8)
    imu_table.add_column("Z", justify="right", width=8)

    imu_table.add_row(
        "Accel",
        f"{state.imu_ax:+.2f}",
        f"{state.imu_ay:+.2f}",
        f"{state.imu_az:+.2f}",
    )
    imu_table.add_row(
        "Gyro",
        f"{state.imu_gx:+.1f}",
        f"{state.imu_gy:+.1f}",
        f"{state.imu_gz:+.1f}",
    )

    # Encoders Table
    enc_table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    enc_table.add_column("Enc", width=4)
    enc_table.add_column("Ticks", justify="right", width=10)
    enc_table.add_column("Vel", justify="right", width=10)

    if state.encoders:
        for enc_id, (ticks, vel) in sorted(state.encoders.items()):
            enc_table.add_row(f"[{enc_id}]", str(ticks), f"{vel:+.1f}")
    else:
        enc_table.add_row("[dim]--[/dim]", "[dim]--[/dim]", "[dim]--[/dim]")

    # Motors
    motors_text = Text("Motors: ")
    if state.motors:
        for m_id, speed in sorted(state.motors.items()):
            bar = _speed_bar(speed)
            motors_text.append(f"[{m_id}]{bar} ")
    else:
        motors_text.append("[dim]--[/dim]")

    # Servos
    servos_text = Text("Servos: ")
    if state.servos:
        for s_id, angle in sorted(state.servos.items()):
            servos_text.append(f"[{s_id}]={angle:.0f}° ", style="cyan")
    else:
        servos_text.append("[dim]--[/dim]")

    # Ultrasonic
    us_text = Text("Sonar:  ")
    if state.ultrasonic:
        for us_id, dist in sorted(state.ultrasonic.items()):
            color = "green" if dist > 0.5 else ("yellow" if dist > 0.2 else "red")
            us_text.append(f"[{us_id}]={dist:.2f}m ", style=color)
    else:
        us_text.append("[dim]--[/dim]")

    # Combine
    content = Group(
        status_line,
        Text(""),
        imu_table,
        Text(""),
        enc_table,
        Text(""),
        motors_text,
        servos_text,
        us_text,
        Text(""),
        Text(f"[dim]Uptime: {state.uptime_ms // 1000}s | Runtime: {elapsed:.0f}s[/dim]"),
    )

    transport_info = f"TCP: {args.tcp}:{args.tcp_port}" if args.tcp else f"Serial: {args.port}"

    return Panel(
        content,
        title=f"[bold cyan]MARA Monitor[/bold cyan] - {transport_info}",
        border_style="blue",
    )


def _generate_compact_display(
    state: MonitorState, args: argparse.Namespace, status_line: Text, elapsed: float
) -> Panel:
    """Generate compact single-line display."""
    lines = [status_line]

    # IMU on one line
    imu_line = Text(
        f"IMU: ax={state.imu_ax:+.1f} ay={state.imu_ay:+.1f} az={state.imu_az:+.1f} "
        f"gx={state.imu_gx:+.0f} gy={state.imu_gy:+.0f} gz={state.imu_gz:+.0f}"
    )
    lines.append(imu_line)

    # Encoders on one line
    if state.encoders:
        enc_parts = [f"E{i}:{t:+d}/{v:+.0f}" for i, (t, v) in sorted(state.encoders.items())]
        lines.append(Text("Enc: " + " ".join(enc_parts)))

    transport_info = f"TCP: {args.tcp}" if args.tcp else f"Serial: {args.port}"

    return Panel(
        Group(*lines),
        title=f"[cyan]MARA[/cyan] - {transport_info}",
        border_style="blue",
    )


def _speed_bar(speed: float, width: int = 5) -> str:
    """Generate ASCII speed bar for motor display."""
    # speed is -1.0 to 1.0
    if abs(speed) < 0.05:
        return "[dim]·····[/dim]"

    filled = int(abs(speed) * width)
    if speed > 0:
        bar = "─" * filled + "▶"
        return f"[green]{bar.ljust(width + 1)}[/green]"
    else:
        bar = "◀" + "─" * filled
        return f"[red]{bar.rjust(width + 1)}[/red]"
