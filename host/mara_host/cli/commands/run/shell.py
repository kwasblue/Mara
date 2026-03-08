# mara_host/cli/commands/run/shell.py
"""Interactive command shell."""

import argparse
import asyncio
import logging
import shlex
from typing import Optional, Any

from rich.prompt import Prompt

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from ._common import get_log_params


def cmd_shell(args: argparse.Namespace) -> int:
    """Launch interactive command shell."""
    transport_type = args.transport
    log_level, log_dir = get_log_params(args)

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

    return asyncio.run(_run_interactive_shell(args, log_level, log_dir))


async def _run_interactive_shell(args: argparse.Namespace, log_level: int = logging.INFO, log_dir: str = "logs") -> int:
    """Run the interactive shell."""
    from mara_host.command.client import MaraClient

    # Create transport
    if args.transport == "serial":
        from mara_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)
    else:
        from mara_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.host, port=args.tcp_port)

    client = MaraClient(transport, connection_timeout_s=6.0, log_level=log_level, log_dir=log_dir)

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
        from mara_host import __version__
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
                    console.print(f"  [green]v[/green] {feature}")
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
