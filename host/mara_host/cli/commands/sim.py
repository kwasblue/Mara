# mara_host/cli/commands/sim.py
"""Simulation commands for MARA CLI."""

import argparse
import asyncio

from mara_host.cli.console import (
    console,
    print_success,
    print_info,
    print_warning,
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register sim command."""
    sim_parser = subparsers.add_parser(
        "sim",
        help="Launch simulation mode",
        description="Run robot in simulation mode without hardware",
    )

    sim_sub = sim_parser.add_subparsers(
        dest="sim_cmd",
        title="simulation modes",
        metavar="<mode>",
    )

    # virtual - virtual robot
    virtual_p = sim_sub.add_parser(
        "virtual",
        help="Run virtual robot (no hardware)",
    )
    virtual_p.add_argument(
        "--port",
        type=int,
        default=3333,
        help="Port for virtual server (default: 3333)",
    )
    virtual_p.add_argument(
        "--config",
        help="Robot configuration file",
    )
    virtual_p.set_defaults(func=cmd_virtual)

    # replay - replay a recorded session
    replay_p = sim_sub.add_parser(
        "replay",
        help="Replay a recorded session",
    )
    replay_p.add_argument("session", help="Session name to replay")
    replay_p.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed (default: 1.0)",
    )
    replay_p.add_argument(
        "--loop",
        action="store_true",
        help="Loop replay continuously",
    )
    replay_p.set_defaults(func=cmd_replay)

    # loopback - loopback transport for testing
    loopback_p = sim_sub.add_parser(
        "loopback",
        help="Test with loopback transport",
    )
    loopback_p.set_defaults(func=cmd_loopback)

    # Default
    sim_parser.set_defaults(func=cmd_virtual)


def cmd_virtual(args: argparse.Namespace) -> int:
    """Run virtual robot."""
    port = args.port
    config_file = getattr(args, 'config', None)

    console.print()
    console.print("[bold cyan]MARA Virtual Robot[/bold cyan]")
    console.print()

    console.print("The virtual robot simulates hardware without physical connections.")
    console.print()
    console.print("Features:")
    console.print("  - Virtual motors with physics simulation")
    console.print("  - Simulated encoders tracking motor movement")
    console.print("  - IMU with noise model")
    console.print("  - Virtual GPIO state tracking")
    console.print()

    print_warning("Virtual robot simulation is under development")
    console.print()
    print_info("For now, use 'mara sim loopback' for basic testing")
    print_info("Or use 'mara sim replay <session>' to replay recorded data")

    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Replay a recorded session as a virtual robot."""
    session = args.session
    speed = args.speed
    loop = args.loop

    console.print()
    console.print("[bold cyan]Session Replay[/bold cyan]")
    console.print(f"  Session: [green]{session}[/green]")
    console.print(f"  Speed: [yellow]{speed}x[/yellow]")
    console.print(f"  Loop: [yellow]{'Yes' if loop else 'No'}[/yellow]")
    console.print()

    # Use the existing replay functionality from record.py
    from mara_host.cli.commands.record import cmd_replay as do_replay

    class ReplayArgs:
        pass

    replay_args = ReplayArgs()
    replay_args.session = session
    replay_args.speed = speed
    replay_args.metrics = False
    replay_args.output = None

    return do_replay(replay_args)


def cmd_loopback(args: argparse.Namespace) -> int:
    """Test with loopback transport."""
    console.print()
    console.print("[bold cyan]Loopback Test Mode[/bold cyan]")
    console.print()

    print_info("Running loopback transport test...")
    console.print()

    return asyncio.run(_run_loopback_test())


async def _run_loopback_test() -> int:
    """Run loopback transport test."""

    # Create a simple loopback transport
    class LoopbackTransport:
        """Simple loopback transport for testing."""

        def __init__(self):
            self._handler = None
            self._running = False

        def set_frame_handler(self, handler):
            self._handler = handler

        async def start(self):
            self._running = True
            print_success("Loopback transport started")

        async def stop(self):
            self._running = False
            print_info("Loopback transport stopped")

        async def send_frame(self, msg_type: int, payload: bytes):
            # Echo back after a small delay
            await asyncio.sleep(0.01)
            if self._handler and self._running:
                # Create a simple echo response
                self._handler(payload)

    from mara_host.command.client import MaraClient

    transport = LoopbackTransport()
    client = MaraClient(transport)

    # Track events
    events_received = []

    def on_event(topic: str):
        def handler(data):
            events_received.append((topic, data))
            console.print(f"  [cyan][{topic}][/cyan] {data}")
        return handler

    client.bus.subscribe("pong", on_event("pong"))
    client.bus.subscribe("json", on_event("json"))
    client.bus.subscribe("error", on_event("error"))

    try:
        await client.start()

        console.print("Sending test commands...")
        console.print()

        # Send some test commands
        await client.send_ping()
        await asyncio.sleep(0.1)

        await client.cmd_led_on()
        await asyncio.sleep(0.1)

        await client.cmd_set_mode("ACTIVE")
        await asyncio.sleep(0.1)

        console.print()
        print_success(f"Loopback test complete. {len(events_received)} events received.")

    finally:
        await client.stop()

    return 0
