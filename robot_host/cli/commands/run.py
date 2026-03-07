# robot_host/cli/commands/run.py
"""Robot runtime commands for MARA CLI."""

import argparse
import asyncio
import shlex
from typing import Optional, Callable, Any

from rich.prompt import Prompt
from rich.table import Table

from robot_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
    print_warning,
)


# Shell commands registry
SHELL_COMMANDS: dict[str, tuple[str, Callable]] = {}


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register run commands."""
    run_parser = subparsers.add_parser(
        "run",
        help="Robot runtime connections",
        description="Connect to robot via different transports",
    )

    run_sub = run_parser.add_subparsers(
        dest="run_cmd",
        title="transports",
        metavar="<transport>",
    )

    # serial
    serial_p = run_sub.add_parser(
        "serial",
        help="Connect via serial port",
    )
    serial_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port (default: /dev/cu.usbserial-0001)",
    )
    serial_p.add_argument(
        "-b", "--baudrate",
        type=int,
        default=115200,
        help="Baud rate (default: 115200)",
    )
    serial_p.add_argument(
        "--shell",
        action="store_true",
        help="Launch interactive shell",
    )
    serial_p.set_defaults(func=cmd_serial)

    # tcp
    tcp_p = run_sub.add_parser(
        "tcp",
        help="Connect via TCP/WiFi",
    )
    tcp_p.add_argument(
        "-H", "--host",
        default="192.168.4.1",
        help="Host address (default: 192.168.4.1 for AP mode)",
    )
    tcp_p.add_argument(
        "-P", "--port",
        type=int,
        default=3333,
        help="TCP port (default: 3333)",
    )
    tcp_p.add_argument(
        "--sta",
        metavar="IP",
        help="Use station mode with specified IP",
    )
    tcp_p.add_argument(
        "--shell",
        action="store_true",
        help="Launch interactive shell",
    )
    tcp_p.set_defaults(func=cmd_tcp)

    # can
    can_p = run_sub.add_parser(
        "can",
        help="Connect via CAN bus",
    )
    can_p.add_argument(
        "-c", "--channel",
        default="can0",
        help="CAN interface (default: can0)",
    )
    can_p.add_argument(
        "-t", "--bustype",
        default="socketcan",
        help="CAN bus type (default: socketcan)",
    )
    can_p.add_argument(
        "-n", "--node-id",
        type=int,
        default=0,
        help="Local node ID 0-14 (default: 0)",
    )
    can_p.add_argument(
        "--virtual",
        action="store_true",
        help="Use virtual CAN bus (for testing)",
    )
    can_p.set_defaults(func=cmd_can)

    # mqtt
    mqtt_p = run_sub.add_parser(
        "mqtt",
        help="Connect via MQTT",
    )
    mqtt_p.add_argument(
        "-H", "--host",
        default="localhost",
        help="MQTT broker host (default: localhost)",
    )
    mqtt_p.add_argument(
        "-P", "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)",
    )
    mqtt_p.add_argument(
        "--topic-prefix",
        default="mara",
        help="MQTT topic prefix (default: mara)",
    )
    mqtt_p.set_defaults(func=cmd_mqtt)

    # shell (interactive mode for any transport)
    shell_p = run_sub.add_parser(
        "shell",
        help="Interactive command shell",
    )
    shell_p.add_argument(
        "-t", "--transport",
        choices=["serial", "tcp"],
        default="serial",
        help="Transport type (default: serial)",
    )
    shell_p.add_argument(
        "-p", "--port",
        default="/dev/cu.usbserial-0001",
        help="Serial port (for serial transport)",
    )
    shell_p.add_argument(
        "-H", "--host",
        default="192.168.4.1",
        help="Host address (for TCP transport)",
    )
    shell_p.add_argument(
        "--tcp-port",
        type=int,
        default=3333,
        help="TCP port (for TCP transport)",
    )
    shell_p.set_defaults(func=cmd_shell)

    # Default handler
    run_parser.set_defaults(func=lambda args: show_transports())


def show_transports() -> int:
    """Show available transports."""
    console.print()
    console.print("[bold cyan]Available Transports[/bold cyan]")
    console.print()
    console.print("  [green]serial[/green]  Connect via USB serial port")
    console.print("  [green]tcp[/green]     Connect via TCP/WiFi")
    console.print("  [green]can[/green]     Connect via CAN bus")
    console.print("  [green]mqtt[/green]    Connect via MQTT broker")
    console.print()
    console.print("[dim]Usage: mara run <transport> [options][/dim]")
    return 0


def cmd_serial(args: argparse.Namespace) -> int:
    """Connect via serial port."""
    port = args.port
    baudrate = args.baudrate
    shell = getattr(args, 'shell', False)

    console.print()
    console.print("[bold cyan]Serial Connection[/bold cyan]")
    console.print(f"  Port: [green]{port}[/green]")
    console.print(f"  Baud: [green]{baudrate}[/green]")
    console.print()

    if shell:
        return _run_serial_shell(port, baudrate)
    else:
        return _run_serial_client(port, baudrate)


def _run_serial_client(port: str, baudrate: int) -> int:
    """Run basic serial client."""
    from robot_host.command.client import AsyncRobotClient
    from robot_host.transport.serial_transport import SerialTransport

    async def main():
        transport = SerialTransport(port, baudrate=baudrate)
        client = AsyncRobotClient(transport)

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


def _run_serial_shell(port: str, baudrate: int) -> int:
    """Run interactive serial shell."""
    print_info("Launching interactive shell...")

    # Import and run the interactive shell
    try:
        from robot_host.runners.interactive_shell import main as shell_main
        asyncio.run(shell_main())
        return 0
    except ImportError:
        print_error("Interactive shell not available")
        return 1
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted[/dim]")
        return 130


def cmd_tcp(args: argparse.Namespace) -> int:
    """Connect via TCP/WiFi."""
    host = args.sta if args.sta else args.host
    port = args.port
    shell = getattr(args, 'shell', False)

    mode = "STA" if args.sta else "AP"

    console.print()
    console.print("[bold cyan]TCP Connection[/bold cyan]")
    console.print(f"  Host: [green]{host}[/green]")
    console.print(f"  Port: [green]{port}[/green]")
    console.print(f"  Mode: [yellow]{mode}[/yellow]")
    console.print()

    return _run_tcp_client(host, port)


def _run_tcp_client(host: str, port: int) -> int:
    """Run TCP client."""
    from robot_host.command.client import AsyncRobotClient
    from robot_host.transport.tcp_transport import AsyncTcpTransport

    async def main():
        transport = AsyncTcpTransport(host=host, port=port)
        client = AsyncRobotClient(transport, connection_timeout_s=6.0)

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


def cmd_can(args: argparse.Namespace) -> int:
    """Connect via CAN bus."""
    channel = args.channel
    bustype = args.bustype
    node_id = args.node_id
    virtual = args.virtual

    console.print()
    console.print("[bold cyan]CAN Bus Connection[/bold cyan]")
    console.print(f"  Channel: [green]{channel}[/green]")
    console.print(f"  Type: [green]{bustype}[/green]")
    console.print(f"  Node ID: [green]{node_id}[/green]")
    if virtual:
        console.print("  [yellow]Virtual mode (loopback)[/yellow]")
    console.print()

    return _run_can_client(channel, bustype, node_id, virtual)


def _run_can_client(channel: str, bustype: str, node_id: int, virtual: bool) -> int:
    """Run CAN client."""
    try:
        from robot_host.command.client import AsyncRobotClient
        from robot_host.transport.can_transport import CANTransport, VirtualCANTransport
        from robot_host.transport.can_defs import NodeState
    except ImportError as e:
        print_error(f"CAN support not available: {e}")
        print_info("Install python-can: pip install python-can")
        return 1

    async def main():
        # Create transport
        if virtual:
            transport = VirtualCANTransport(channel=channel, node_id=node_id)
        else:
            transport = CANTransport(
                channel=channel,
                bustype=bustype,
                node_id=node_id,
            )

        # Set up callbacks
        transport.set_encoder_callback(
            lambda nid, counts, vel: console.print(f"[dim][ENC][/dim] n={nid} c={counts} v={vel}")
        )
        transport.set_heartbeat_callback(
            lambda nid, uptime, state: console.print(f"[dim][HB][/dim] n={nid} up={uptime}ms {state.name}")
        )

        client = AsyncRobotClient(transport, connection_timeout_s=5.0)

        client.bus.subscribe("heartbeat", lambda d: console.print(f"[dim][HEARTBEAT][/dim] {d}"))
        client.bus.subscribe("pong", lambda d: console.print(f"[dim][PONG][/dim] {d}"))
        client.bus.subscribe("error", lambda e: console.print(f"[red][ERROR][/red] {e}"))

        await client.start()
        print_success(f"CAN client started (node_id={node_id})")

        try:
            while True:
                await asyncio.sleep(0.1)
        finally:
            await client.stop()
            print_info("CAN client stopped")

    try:
        asyncio.run(main())
        return 0
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted[/dim]")
        return 130
    except Exception as e:
        print_error(f"CAN connection failed: {e}")
        return 1


def cmd_mqtt(args: argparse.Namespace) -> int:
    """Connect via MQTT."""
    host = args.host
    port = args.port
    topic_prefix = args.topic_prefix

    console.print()
    console.print("[bold cyan]MQTT Connection[/bold cyan]")
    console.print(f"  Broker: [green]{host}:{port}[/green]")
    console.print(f"  Topic prefix: [green]{topic_prefix}[/green]")
    console.print()

    print_warning("MQTT transport is a work in progress")
    print_info("Use 'mara run serial' or 'mara run tcp' for now")

    return 0


def cmd_shell(args: argparse.Namespace) -> int:
    """Launch interactive command shell."""
    transport_type = args.transport

    console.print()
    console.print("[bold cyan]MARA Interactive Shell[/bold cyan]")

    if transport_type == "serial":
        console.print(f"  Transport: [green]Serial[/green]")
        console.print(f"  Port: [green]{args.port}[/green]")
    else:
        console.print(f"  Transport: [green]TCP[/green]")
        console.print(f"  Host: [green]{args.host}:{args.tcp_port}[/green]")

    console.print()
    console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]")
    console.print()

    return asyncio.run(_run_interactive_shell(args))


async def _run_interactive_shell(args: argparse.Namespace) -> int:
    """Run the interactive shell."""
    from robot_host.command.client import AsyncRobotClient

    # Create transport
    if args.transport == "serial":
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)
    else:
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.host, port=args.tcp_port)

    client = AsyncRobotClient(transport, connection_timeout_s=6.0)

    # Event log
    event_log: list[tuple[str, Any]] = []
    max_log = 100

    def log_event(topic: str, data: Any) -> None:
        event_log.append((topic, data))
        if len(event_log) > max_log:
            event_log.pop(0)

    # Track whether to show events live
    show_events_live = [True]  # Use list for mutable closure

    def handle_event(topic: str, data: Any, style: str = "cyan") -> None:
        log_event(topic, data)
        if show_events_live[0]:
            console.print(f"  [{style}][{topic.upper()}][/{style}] {data}")

    # Subscribe to events
    client.bus.subscribe("heartbeat", lambda d: log_event("heartbeat", d))  # Silent by default
    client.bus.subscribe("pong", lambda d: handle_event("pong", d, "green"))
    client.bus.subscribe("hello", lambda d: handle_event("hello", d, "green"))
    client.bus.subscribe("json", lambda d: handle_event("json", d, "cyan"))
    client.bus.subscribe("telemetry", lambda d: log_event("telemetry", d))  # Too noisy for live
    client.bus.subscribe("error", lambda d: handle_event("error", d, "red"))

    try:
        await client.start()
        print_success("Connected to robot")
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    # Shell loop
    shell = InteractiveShell(client, event_log)

    try:
        while True:
            try:
                cmd = Prompt.ask("[green]mara>[/green]")
            except (KeyboardInterrupt, EOFError):
                console.print()
                break

            if not cmd.strip():
                continue

            result = await shell.execute(cmd.strip())
            if result == "quit":
                break

    finally:
        await client.stop()
        # Explicitly close transport to release serial port
        if hasattr(transport, 'stop'):
            transport.stop()
        print_info("Disconnected")

    return 0


class InteractiveShell:
    """Interactive command shell for robot control."""

    def __init__(self, client, event_log: list):
        self.client = client
        self.event_log = event_log
        self.commands = {
            "help": (self.cmd_help, "Show available commands"),
            "quit": (self.cmd_quit, "Exit the shell"),
            "exit": (self.cmd_quit, "Exit the shell"),
            "ping": (self.cmd_ping, "Send ping to robot"),
            "status": (self.cmd_status, "Show connection status"),
            "events": (self.cmd_events, "Show recent events"),
            "clear": (self.cmd_clear, "Clear event log"),

            # Mode commands
            "arm": (self.cmd_arm, "Arm the robot"),
            "disarm": (self.cmd_disarm, "Disarm the robot"),
            "active": (self.cmd_active, "Set mode to ACTIVE"),
            "idle": (self.cmd_idle, "Set mode to IDLE"),

            # LED commands
            "led": (self.cmd_led, "Control LED: led on/off/blink"),

            # Servo commands
            "servo": (self.cmd_servo, "Control servo: servo <id> <angle> or servo attach <id> <pin>"),

            # Motor commands
            "motor": (self.cmd_motor, "Control motor: motor <id> <speed>"),

            # GPIO commands
            "gpio": (self.cmd_gpio, "Control GPIO: gpio <pin> high/low/read"),

            # Info commands
            "info": (self.cmd_info, "Request robot info"),
            "version": (self.cmd_version, "Show host version"),
            "identity": (self.cmd_identity, "Get MCU build identity and features"),

            # Raw command
            "raw": (self.cmd_raw, "Send raw JSON command"),
        }

    async def execute(self, cmd_line: str) -> Optional[str]:
        """Execute a command line."""
        try:
            parts = shlex.split(cmd_line)
        except ValueError as e:
            print_error(f"Parse error: {e}")
            return None

        if not parts:
            return None

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in self.commands:
            handler, _ = self.commands[cmd]
            return await handler(args)
        else:
            print_error(f"Unknown command: {cmd}")
            console.print("[dim]Type 'help' for available commands[/dim]")
            return None

    async def cmd_help(self, args: list[str]) -> None:
        """Show help."""
        console.print()
        console.print("[bold]Available Commands:[/bold]")
        console.print()

        # Group commands
        groups = {
            "General": ["help", "quit", "status", "events", "clear"],
            "Control": ["arm", "disarm", "active", "idle"],
            "Hardware": ["led", "servo", "motor", "gpio"],
            "Info": ["ping", "info", "version", "identity"],
            "Advanced": ["raw"],
        }

        for group, cmds in groups.items():
            console.print(f"[bold cyan]{group}:[/bold cyan]")
            for cmd in cmds:
                if cmd in self.commands:
                    _, desc = self.commands[cmd]
                    console.print(f"  [green]{cmd:12}[/green] {desc}")
            console.print()

    async def cmd_quit(self, args: list[str]) -> str:
        """Exit the shell."""
        return "quit"

    async def cmd_ping(self, args: list[str]) -> None:
        """Send ping."""
        await self.client.send_ping()
        print_info("Ping sent, awaiting pong...")

    async def cmd_status(self, args: list[str]) -> None:
        """Show status."""
        console.print()
        console.print("[bold]Connection Status:[/bold]")
        console.print(f"  Connected: [green]Yes[/green]")
        console.print(f"  Events received: [cyan]{len(self.event_log)}[/cyan]")

        # Show last heartbeat if any
        for topic, data in reversed(self.event_log):
            if topic == "heartbeat":
                console.print(f"  Last heartbeat: [dim]{data}[/dim]")
                break

    async def cmd_events(self, args: list[str]) -> None:
        """Show recent events."""
        count = int(args[0]) if args else 10

        if not self.event_log:
            print_info("No events yet")
            return

        console.print()
        console.print(f"[bold]Recent Events (last {count}):[/bold]")
        console.print()

        for topic, data in self.event_log[-count:]:
            if topic == "error":
                console.print(f"  [red][{topic}][/red] {data}")
            elif topic == "heartbeat":
                console.print(f"  [dim][{topic}][/dim] {data}")
            else:
                console.print(f"  [cyan][{topic}][/cyan] {data}")

    async def cmd_clear(self, args: list[str]) -> None:
        """Clear event log."""
        self.event_log.clear()
        print_success("Event log cleared")

    async def cmd_arm(self, args: list[str]) -> None:
        """Arm the robot."""
        await self.client.cmd_arm()
        print_success("Robot armed")

    async def cmd_disarm(self, args: list[str]) -> None:
        """Disarm the robot."""
        await self.client.cmd_disarm()
        print_success("Robot disarmed")

    async def cmd_active(self, args: list[str]) -> None:
        """Set mode to ACTIVE."""
        await self.client.cmd_set_mode("ACTIVE")
        print_success("Mode set to ACTIVE")

    async def cmd_idle(self, args: list[str]) -> None:
        """Set mode to IDLE."""
        await self.client.cmd_set_mode("IDLE")
        print_success("Mode set to IDLE")

    async def cmd_led(self, args: list[str]) -> None:
        """Control LED."""
        if not args:
            console.print("Usage: led on/off/blink")
            return

        action = args[0].lower()
        if action == "on":
            await self.client.cmd_led_on()
            print_success("LED on")
        elif action == "off":
            await self.client.cmd_led_off()
            print_success("LED off")
        elif action == "blink":
            count = int(args[1]) if len(args) > 1 else 3
            interval_s = float(args[2]) / 1000 if len(args) > 2 else 0.2
            for _ in range(count):
                await self.client.cmd_led_on()
                await asyncio.sleep(interval_s)
                await self.client.cmd_led_off()
                await asyncio.sleep(interval_s)
            print_success(f"LED blinked {count} times")
        else:
            print_error(f"Unknown LED action: {action}")

    async def cmd_servo(self, args: list[str]) -> None:
        """Control servo."""
        if not args:
            console.print("Usage:")
            console.print("  servo attach <id> <pin>     Attach servo to GPIO pin")
            console.print("  servo <id> <angle>          Set servo angle (0-180)")
            console.print("  servo detach <id>           Detach servo")
            return

        # Handle subcommands
        if args[0] == "attach":
            if len(args) < 3:
                console.print("Usage: servo attach <id> <pin> [min_us] [max_us]")
                return
            servo_id = int(args[1])
            pin = int(args[2])
            min_us = int(args[3]) if len(args) > 3 else 500
            max_us = int(args[4]) if len(args) > 4 else 2500
            await self.client.cmd_servo_attach(servo_id, pin, min_us, max_us)
            print_success(f"Servo {servo_id} attached to GPIO {pin}")
            return

        if args[0] == "detach":
            if len(args) < 2:
                console.print("Usage: servo detach <id>")
                return
            servo_id = int(args[1])
            await self.client.cmd_servo_detach(servo_id)
            print_success(f"Servo {servo_id} detached")
            return

        # Default: set angle
        if len(args) < 2:
            console.print("Usage: servo <id> <angle> [duration_ms]")
            return

        servo_id = int(args[0])
        angle = float(args[1])
        duration = int(args[2]) if len(args) > 2 else 0

        await self.client.cmd_servo_set_angle(servo_id, angle, duration)
        print_success(f"Servo {servo_id} set to {angle} degrees")

    async def cmd_motor(self, args: list[str]) -> None:
        """Control motor."""
        if len(args) < 2:
            console.print("Usage: motor <id> <speed> (-100 to 100)")
            return

        motor_id = int(args[0])
        speed = float(args[1])

        # Clamp speed
        speed = max(-100, min(100, speed))

        await self.client.cmd_dc_set_speed(motor_id, speed / 100.0)
        print_success(f"Motor {motor_id} set to {speed}%")

    async def cmd_gpio(self, args: list[str]) -> None:
        """Control GPIO."""
        if len(args) < 2:
            console.print("Usage: gpio <channel> high/low/read")
            return

        channel = int(args[0])
        action = args[1].lower()

        if action == "high":
            await self.client.cmd_gpio_write(channel, True)
            print_success(f"GPIO channel {channel} set HIGH")
        elif action == "low":
            await self.client.cmd_gpio_write(channel, False)
            print_success(f"GPIO channel {channel} set LOW")
        elif action == "read":
            # Note: This would need async response handling
            print_info(f"GPIO read not yet implemented in shell")
        else:
            print_error(f"Unknown GPIO action: {action}")

    async def cmd_info(self, args: list[str]) -> None:
        """Request robot info."""
        await self.client.cmd_get_info()
        print_info("Info requested (check events)")

    async def cmd_version(self, args: list[str]) -> None:
        """Show version."""
        console.print()
        console.print("[bold]MARA Shell[/bold]")
        from robot_host import __version__
        console.print(f"  Host version: [green]{__version__}[/green]")
        print_info("Use 'identity' to get MCU build info")

    async def cmd_identity(self, args: list[str]) -> None:
        """Get MCU build identity and features."""
        import asyncio

        console.print()
        console.print("[bold]Querying MCU identity...[/bold]")

        # Use asyncio.Future to wait for response
        response_future: asyncio.Future = asyncio.get_event_loop().create_future()

        def on_identity_response(data: dict) -> None:
            if not response_future.done():
                response_future.set_result(data)

        # Subscribe to the specific command response topic
        self.client.bus.subscribe("cmd.CMD_GET_IDENTITY", on_identity_response)

        try:
            # Send identity request
            await self.client.cmd_get_identity()

            # Wait for response with timeout
            try:
                data = await asyncio.wait_for(response_future, timeout=2.0)
            except asyncio.TimeoutError:
                print_error("Identity request timed out")
                return

            # Parse and display the response (data is flat, not wrapped in "payload")
            console.print()
            console.print("[bold cyan]MCU Identity:[/bold cyan]")
            console.print(f"  Firmware:  [green]{data.get('firmware', 'unknown')}[/green]")
            console.print(f"  Board:     {data.get('board', 'unknown')}")
            console.print(f"  Name:      {data.get('name', 'unknown')}")
            console.print(f"  Protocol:  v{data.get('protocol', '?')}")
            console.print(f"  Schema:    v{data.get('schema', '?')}")
            console.print(f"  Caps:      0x{data.get('caps', 0):08X}")

            features = data.get("features", [])
            if features:
                console.print()
                console.print("[bold cyan]Enabled Features:[/bold cyan]")
                for feature in sorted(features):
                    console.print(f"  [green]✓[/green] {feature}")
            else:
                console.print()
                console.print("[dim]No features list (check caps bitmask)[/dim]")

        finally:
            # Unsubscribe (EventBus may not have unsubscribe, but try)
            pass

    async def cmd_raw(self, args: list[str]) -> None:
        """Send raw JSON command."""
        if not args:
            console.print("Usage: raw <json_command>")
            console.print('Example: raw {"cmd": "ping"}')
            return

        import json
        try:
            cmd_str = " ".join(args)
            cmd_obj = json.loads(cmd_str)
            await self.client.send_command(cmd_obj)
            print_success("Command sent")
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON: {e}")
