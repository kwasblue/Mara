# robot_host/cli/commands/record.py
"""Recording and replay commands for MARA CLI."""

import argparse
from pathlib import Path

from robot_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
    print_warning,
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register record/replay commands."""
    # record command
    record_parser = subparsers.add_parser(
        "record",
        help="Record telemetry session",
        description="Record robot telemetry data to a session file",
    )
    record_parser.add_argument(
        "session",
        help="Session name (creates logs/<session>/ directory)",
    )
    record_parser.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port (default: /dev/cu.usbserial-0001)",
    )
    record_parser.add_argument(
        "-d", "--duration",
        type=float,
        default=0,
        help="Recording duration in seconds (0=unlimited)",
    )
    record_parser.add_argument(
        "--tcp",
        metavar="HOST",
        help="Use TCP transport instead of serial",
    )
    record_parser.add_argument(
        "--console",
        action="store_true",
        help="Also print events to console",
    )
    record_parser.set_defaults(func=cmd_record)

    # replay command
    replay_parser = subparsers.add_parser(
        "replay",
        help="Replay recorded session",
        description="Replay a recorded telemetry session",
    )
    replay_parser.add_argument(
        "session",
        help="Session name to replay",
    )
    replay_parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed multiplier (default: 1.0)",
    )
    replay_parser.add_argument(
        "--metrics",
        action="store_true",
        help="Generate metrics from replay",
    )
    replay_parser.add_argument(
        "-o", "--output",
        help="Output file for metrics",
    )
    replay_parser.set_defaults(func=cmd_replay)


def cmd_record(args: argparse.Namespace) -> int:
    """Record telemetry session."""
    session = args.session
    port = args.port
    duration = args.duration
    tcp_host = args.tcp
    show_console = args.console

    console.print()
    console.print("[bold cyan]Recording Session[/bold cyan]")
    console.print(f"  Session: [green]{session}[/green]")

    if tcp_host:
        console.print(f"  Transport: [yellow]TCP ({tcp_host})[/yellow]")
    else:
        console.print(f"  Transport: [yellow]Serial ({port})[/yellow]")

    if duration > 0:
        console.print(f"  Duration: [yellow]{duration}s[/yellow]")
    else:
        console.print("  Duration: [yellow]unlimited (Ctrl+C to stop)[/yellow]")

    console.print()

    return _run_recording(session, port, tcp_host, duration, show_console)


def _run_recording(
    session: str,
    port: str,
    tcp_host: str | None,
    duration: float,
    show_console: bool,
) -> int:
    """Run the recording session."""
    import asyncio

    try:
        from robot_host.logger.logger import MaraLogBundle
        from robot_host.research.recording import RecordingConfig, RecordingEventBus, RecordingTransport
        from robot_host.command.client import AsyncRobotClient
    except ImportError as e:
        print_error(f"Recording dependencies not available: {e}")
        return 1

    async def main():
        # Create log bundle
        config = RecordingConfig(name=session, console=show_console)
        log_dir = Path(config.log_dir) / session
        log_dir.mkdir(parents=True, exist_ok=True)

        bundle = MaraLogBundle(str(log_dir))
        print_success(f"Logging to: {log_dir}")

        # Create transport
        if tcp_host:
            from robot_host.transport.tcp_transport import AsyncTcpTransport
            inner_transport = AsyncTcpTransport(host=tcp_host, port=3333)
        else:
            from robot_host.transport.serial_transport import SerialTransport
            inner_transport = SerialTransport(port, baudrate=115200)

        transport = RecordingTransport(inner_transport, bundle)
        client = AsyncRobotClient(transport)

        # Wrap event bus for recording
        client.bus = RecordingEventBus(client.bus, bundle)

        # Subscribe for console output if requested
        if show_console:
            client.bus.subscribe("heartbeat", lambda d: console.print(f"[dim][HB][/dim] {d}"))
            client.bus.subscribe("json", lambda d: console.print(f"[cyan][JSON][/cyan] {d}"))

        await client.start()
        print_success("Recording started")

        try:
            if duration > 0:
                await asyncio.sleep(duration)
                print_info(f"Duration reached ({duration}s)")
            else:
                while True:
                    await asyncio.sleep(0.1)
        finally:
            await client.stop()
            bundle.close()
            print_success("Recording stopped")

    try:
        asyncio.run(main())
        return 0
    except KeyboardInterrupt:
        console.print("\n[dim]Recording stopped[/dim]")
        return 0
    except Exception as e:
        print_error(f"Recording failed: {e}")
        return 1


def cmd_replay(args: argparse.Namespace) -> int:
    """Replay recorded session."""
    session = args.session
    speed = args.speed
    metrics = args.metrics
    output = args.output

    # Find session directory
    log_dir = Path("logs") / session
    if not log_dir.exists():
        print_error(f"Session not found: {log_dir}")
        return 1

    console.print()
    console.print("[bold cyan]Replaying Session[/bold cyan]")
    console.print(f"  Session: [green]{session}[/green]")
    console.print(f"  Speed: [yellow]{speed}x[/yellow]")
    if metrics:
        console.print(f"  Metrics: [yellow]enabled[/yellow]")
        if output:
            console.print(f"  Output: [yellow]{output}[/yellow]")
    console.print()

    if metrics:
        return _replay_to_metrics(log_dir, output)
    else:
        return _replay_session(log_dir, speed)


def _replay_session(log_dir: Path, speed: float) -> int:
    """Replay session events."""
    import json
    import time

    events_file = log_dir / "events.jsonl"
    if not events_file.exists():
        print_error(f"Events file not found: {events_file}")
        return 1

    print_info(f"Replaying from: {events_file}")
    console.print()

    last_ts = None
    count = 0

    try:
        with open(events_file) as f:
            for line in f:
                if not line.strip():
                    continue

                event = json.loads(line)
                ts = event.get("ts", 0)
                event_type = event.get("event", "unknown")

                # Timing
                if last_ts is not None and speed > 0:
                    delay = (ts - last_ts) / speed
                    if delay > 0:
                        time.sleep(delay)
                last_ts = ts

                # Display event
                if event_type == "bus.publish":
                    topic = event.get("topic", "?")
                    data = event.get("data", {})
                    console.print(f"[dim]{ts:.3f}[/dim] [{topic}] {data}")
                elif event_type.startswith("transport."):
                    console.print(f"[dim]{ts:.3f}[/dim] [yellow]{event_type}[/yellow]")

                count += 1

    except KeyboardInterrupt:
        console.print("\n[dim]Replay stopped[/dim]")

    print_info(f"Replayed {count} events")
    return 0


def _replay_to_metrics(log_dir: Path, output: str | None) -> int:
    """Generate metrics from replay."""
    print_warning("Metrics generation is a work in progress")
    print_info("Use the replay_to_metrics.py runner for full functionality")
    return 0
