# mara_host/cli/commands/mqtt.py
"""MQTT broker management commands."""

import argparse
import shutil
import signal
import subprocess
import socket
import sys
import os
from pathlib import Path

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
    print_info,
)


PID_FILE = Path.home() / ".mara" / "mosquitto.pid"
CONF_FILE = Path.home() / ".mara" / "mosquitto.conf"


def _get_local_ip() -> str:
    """Get local IP address for display."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _find_mosquitto() -> str | None:
    """Find mosquitto binary."""
    return shutil.which("mosquitto")


def _get_running_pid() -> int | None:
    """Get PID of running broker if any."""
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process exists
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        PID_FILE.unlink(missing_ok=True)
        return None


def cmd_start(args: argparse.Namespace) -> int:
    """Start local MQTT broker."""
    port = args.port
    verbose = args.verbose

    # Check if already running
    pid = _get_running_pid()
    if pid:
        print_warning(f"Broker already running (PID {pid})")
        return 0

    # Check if port is in use
    if _is_port_in_use(port):
        print_error(f"Port {port} is already in use")
        print_info("Another broker may be running, or use --port to specify a different port")
        return 1

    # Find mosquitto
    mosquitto = _find_mosquitto()
    if not mosquitto:
        print_error("mosquitto not found")
        console.print()
        console.print("[dim]Install with:[/dim]")
        console.print("  [cyan]brew install mosquitto[/cyan]  (macOS)")
        console.print("  [cyan]apt install mosquitto[/cyan]   (Linux)")
        return 1

    # Ensure pid directory exists
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Create config file to allow remote connections (mosquitto 2.0+ requires this)
    conf_content = f"""# MARA mosquitto config
listener {port} 0.0.0.0
allow_anonymous true
"""
    CONF_FILE.write_text(conf_content)

    # Start broker with config
    cmd = [mosquitto, "-c", str(CONF_FILE)]
    if verbose:
        cmd.append("-v")

    if args.foreground:
        # Run in foreground (blocking)
        console.print(f"[bold cyan]Starting MQTT broker on port {port}...[/bold cyan]")
        console.print(f"[dim]Local IP: {_get_local_ip()}[/dim]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        console.print()
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print_info("Broker stopped")
        return 0
    else:
        # Run in background
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL if not verbose else None,
            stderr=subprocess.DEVNULL if not verbose else None,
            start_new_session=True,
        )
        PID_FILE.write_text(str(proc.pid))

        local_ip = _get_local_ip()
        print_success(f"MQTT broker started on port {port} (PID {proc.pid})")
        console.print()
        console.print("[dim]Update firmware config:[/dim]")
        console.print(f'  [cyan]#define MQTT_BROKER_HOST     "{local_ip}"[/cyan]')
        console.print(f"  [cyan]#define MQTT_BROKER_PORT     {port}[/cyan]")
        console.print()
        console.print("[dim]Stop with:[/dim]  [cyan]mara mqtt stop[/cyan]")
        return 0


def cmd_stop(args: argparse.Namespace) -> int:
    """Stop local MQTT broker."""
    pid = _get_running_pid()
    if not pid:
        print_info("No broker running")
        return 0

    try:
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        print_success(f"Broker stopped (PID {pid})")
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        print_info("Broker was not running")
    except PermissionError:
        print_error(f"Cannot stop broker (PID {pid}) - permission denied")
        return 1

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Check MQTT broker status."""
    port = args.port
    pid = _get_running_pid()

    console.print()
    console.print("[bold cyan]MQTT Broker Status[/bold cyan]")
    console.print()

    if pid:
        print_success(f"Running (PID {pid})")
    else:
        # Check if something else is on the port
        if _is_port_in_use(port):
            print_warning(f"Port {port} in use (external broker?)")
        else:
            print_info("Not running")

    console.print()
    console.print(f"[dim]Local IP:[/dim] {_get_local_ip()}")
    console.print(f"[dim]Port:[/dim]     {port}")

    return 0


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register mqtt command group."""
    mqtt_parser = subparsers.add_parser(
        "mqtt",
        help="MQTT broker management",
        description="Start, stop, and manage local MQTT broker for MCU communication.",
    )

    mqtt_sub = mqtt_parser.add_subparsers(dest="mqtt_command", required=True)

    # start
    start_p = mqtt_sub.add_parser("start", help="Start local MQTT broker")
    start_p.add_argument("-p", "--port", type=int, default=1883, help="Broker port (default: 1883)")
    start_p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    start_p.add_argument("-f", "--foreground", action="store_true", help="Run in foreground")
    start_p.set_defaults(func=cmd_start)

    # stop
    stop_p = mqtt_sub.add_parser("stop", help="Stop local MQTT broker")
    stop_p.set_defaults(func=cmd_stop)

    # status
    status_p = mqtt_sub.add_parser("status", help="Check broker status")
    status_p.add_argument("-p", "--port", type=int, default=1883, help="Port to check (default: 1883)")
    status_p.set_defaults(func=cmd_status)
