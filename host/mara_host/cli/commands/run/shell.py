# mara_host/cli/commands/run/shell.py
"""Interactive command shell."""

import argparse
import asyncio
import logging
import shlex
from typing import Optional, Any

from rich.prompt import Prompt
from rich.markup import escape

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
    elif transport_type == "ble":
        console.print(f"  Transport: [green]Bluetooth SPP[/green]")
        console.print(f"  Device: [green]{args.ble_name}[/green]")
    else:
        console.print(f"  Transport: [green]TCP[/green]")
        console.print(f"  Host: [green]{args.host}:{args.tcp_port}[/green]")

    console.print()
    console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]")
    console.print()

    return asyncio.run(_run_interactive_shell(args, log_level, log_dir))


async def _run_interactive_shell(args: argparse.Namespace, log_level: int = logging.INFO, log_dir: str = "logs") -> int:
    """Run the interactive shell."""
    # Event log
    event_log: list[tuple[str, Any]] = []
    max_log = 100

    def log_event(topic: str, data: Any) -> None:
        event_log.append((topic, data))
        if len(event_log) > max_log:
            event_log.pop(0)

    # Track whether to show events live (will be set on shell instance)
    show_events_live = [False]  # Default off, use list for mutable closure

    def handle_event(topic: str, data: Any, style: str = "cyan") -> None:
        log_event(topic, data)
        if show_events_live[0]:
            safe_topic = escape(topic.upper())
            console.print(f"  [{style}]\\[{safe_topic}][/{style}] {data}")

    def setup_event_handlers(client) -> None:
        """Subscribe to events on the client."""
        client.bus.subscribe("heartbeat", lambda d: log_event("heartbeat", d))
        client.bus.subscribe("pong", lambda d: handle_event("pong", d, "green"))
        client.bus.subscribe("hello", lambda d: handle_event("hello", d, "green"))
        client.bus.subscribe("json", lambda d: handle_event("json", d, "cyan"))
        client.bus.subscribe("telemetry", lambda d: log_event("telemetry", d))
        client.bus.subscribe("error", lambda d: handle_event("error", d, "red"))
        # State and connection events
        client.bus.subscribe("state.changed", lambda d: handle_event("state", d, "yellow"))
        client.bus.subscribe("connection.lost", lambda d: handle_event("disconnected", d, "red"))
        client.bus.subscribe("connection.restored", lambda d: handle_event("reconnected", d, "green"))

    # Shell with connection factory
    shell = InteractiveShell(
        event_log=event_log,
        default_args=args,
        log_level=log_level,
        log_dir=log_dir,
        setup_event_handlers=setup_event_handlers,
        show_events_live=show_events_live,
    )

    # Try to connect with default args, but don't fail if we can't
    await shell.try_connect()

    try:
        while True:
            try:
                prompt = "[green]mara>[/green]" if shell.connected else "[yellow]mara (disconnected)>[/yellow]"
                cmd = Prompt.ask(prompt)
            except (KeyboardInterrupt, EOFError):
                console.print()
                break

            if not cmd.strip():
                continue

            result = await shell.execute(cmd.strip())
            if result == "quit":
                break

    finally:
        await shell.cleanup()
        print_info("Disconnected")

    return 0


class InteractiveShell:
    """Interactive command shell for robot control."""

    def __init__(
        self,
        event_log: list,
        default_args: argparse.Namespace,
        log_level: int,
        log_dir: str,
        setup_event_handlers,
        show_events_live: list,
    ):
        self.event_log = event_log
        self.default_args = default_args
        self.log_level = log_level
        self.log_dir = log_dir
        self.setup_event_handlers = setup_event_handlers
        self.show_events_live = show_events_live  # Mutable list for toggle

        # Current connection state
        self.client = None
        self.transport = None
        self.connected = False
        self.current_connection_info = ""

        self.commands = {
            "help": (self.cmd_help, "Show available commands"),
            "quit": (self.cmd_quit, "Exit the shell"),
            "exit": (self.cmd_quit, "Exit the shell"),
            "connect": (self.cmd_connect, "Connect to robot (connect [serial|tcp|ble] ...)"),
            "disconnect": (self.cmd_disconnect, "Disconnect from robot"),
            "ping": (self.cmd_ping, "Send ping to robot"),
            "status": (self.cmd_status, "Show connection status"),
            "events": (self.cmd_events, "Show events: events [count|all|on|off]"),
            "clear": (self.cmd_clear, "Clear event log"),

            # Mode commands
            "arm": (self.cmd_arm, "Arm the robot"),
            "disarm": (self.cmd_disarm, "Disarm the robot"),
            "activate": (self.cmd_active, "Set mode to ACTIVE"),
            "deactivate": (self.cmd_deactivate, "Set mode to IDLE"),
            "active": (self.cmd_active, "Set mode to ACTIVE"),
            "idle": (self.cmd_deactivate, "Set mode to IDLE"),
            "estop": (self.cmd_estop, "Emergency stop"),
            "safety": (self.cmd_safety, "Safety timeouts: safety [on|off|status|set <host_ms> <motion_ms>]"),

            # LED commands
            "led": (self.cmd_led, "Control LED: led on/off/blink"),

            # Servo commands
            "servo": (self.cmd_servo, "Control servo: servo <id> <angle> or servo attach <id> <pin>"),

            # Motor commands
            "motor": (self.cmd_motor, "Control DC motor: motor <id> <speed>"),
            "dc": (self.cmd_dc, "DC motor control: dc set/stop/gains ..."),

            # Stepper motor commands
            "stepper": (self.cmd_stepper, "Stepper motor: stepper move/stop/enable/home ..."),

            # GPIO commands
            "gpio": (self.cmd_gpio, "Control GPIO: gpio <channel> high/low/read"),
            "pwm": (self.cmd_pwm, "PWM control: pwm <channel> <duty> [freq]"),

            # Sensor commands
            "encoder": (self.cmd_encoder, "Encoder: encoder attach/read/reset/detach ..."),
            "imu": (self.cmd_imu, "IMU: imu read/calibrate/bias ..."),
            "ultrasonic": (self.cmd_ultrasonic, "Ultrasonic: ultrasonic attach/read/detach ..."),

            # Camera commands
            "cam": (self.cmd_cam, "Camera: cam capture/stream/preset ..."),

            # Telemetry commands
            "telem": (self.cmd_telem, "Telemetry: telem rate/interval ..."),

            # WiFi commands
            "wifi": (self.cmd_wifi, "WiFi: wifi scan/join/disconnect/status"),

            # Control graph commands
            "ctrl": (self.cmd_ctrl, "Control graph: ctrl status/enable/disable/clear ..."),

            # Observer commands
            "observer": (self.cmd_observer, "Observer: observer config/enable/disable/status ..."),

            # Logging commands
            "log": (self.cmd_log, "MCU logging: log level <level> or log <subsystem> <level>"),

            # Info commands
            "info": (self.cmd_info, "Request robot info"),
            "version": (self.cmd_version, "Show host version"),
            "identity": (self.cmd_identity, "Get MCU build identity and features"),
            "state": (self.cmd_state, "Get robot state"),
            "rates": (self.cmd_rates, "Get loop rates"),

            # Generic command interface
            "send": (self.cmd_send, "Send any command: send CMD_NAME {json_payload}"),
            "commands": (self.cmd_commands, "List all available commands"),
            "raw": (self.cmd_raw, "Send raw JSON command"),
        }

    def _require_connection(self) -> bool:
        """Check if connected, print error if not."""
        if not self.connected:
            print_error("Not connected. Use 'connect' first.")
            return False
        return True

    def _create_transport(self, transport_type: str, **kwargs):
        """Create a transport based on type and parameters."""
        if transport_type == "serial":
            from mara_host.transport.serial_transport import SerialTransport
            port = kwargs.get("port", self.default_args.port)
            baudrate = kwargs.get("baudrate", self.default_args.baudrate)
            return SerialTransport(port, baudrate=baudrate), f"serial:{port}"
        elif transport_type == "ble":
            from mara_host.transport.bluetooth_transport import BluetoothSerialTransport
            device_name = kwargs.get("device_name", self.default_args.ble_name)
            baudrate = kwargs.get("baudrate", self.default_args.baudrate)
            return BluetoothSerialTransport.auto(device_name=device_name, baudrate=baudrate), f"ble:{device_name}"
        else:  # tcp
            from mara_host.transport.tcp_transport import AsyncTcpTransport
            host = kwargs.get("host", self.default_args.host)
            port = kwargs.get("port", self.default_args.tcp_port)
            return AsyncTcpTransport(host=host, port=port), f"tcp:{host}:{port}"

    def _create_client(self, transport):
        """Create a client with the given transport."""
        from mara_host.command.client import MaraClient
        client = MaraClient(
            transport,
            # Disable timeout-based disconnect for interactive shell
            connection_timeout_s=float('inf'),
            # Very long command timeout for interactive shell
            command_timeout_s=10.0,
            max_retries=5,
            log_level=self.log_level,
            log_dir=self.log_dir,
        )
        self.setup_event_handlers(client)
        return client

    async def try_connect(self, transport_type: str = None, **kwargs) -> bool:
        """Try to connect with given or default parameters."""
        if self.connected:
            print_info("Already connected. Use 'disconnect' first.")
            return False

        # Use default transport type if not specified
        if transport_type is None:
            transport_type = self.default_args.transport

        try:
            self.transport, self.current_connection_info = self._create_transport(transport_type, **kwargs)
            self.client = self._create_client(self.transport)
            await self.client.start()
            self.connected = True
            print_success(f"Connected to robot ({self.current_connection_info})")
            return True
        except Exception as e:
            self.client = None
            self.transport = None
            self.connected = False
            print_info(f"Not connected: {e}")
            print_info("Use 'connect' to connect when device is ready")
            return False

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.connected and self.client:
            try:
                await self.client.stop()
            except Exception:
                pass
        if self.transport and hasattr(self.transport, 'stop'):
            try:
                self.transport.stop()
            except Exception:
                pass
        self.client = None
        self.transport = None
        self.connected = False

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
            try:
                return await handler(args)
            except ValueError as e:
                print_error(f"Invalid argument: {e}")
                return None
            except (TypeError, IndexError) as e:
                print_error(f"Missing or invalid argument: {e}")
                return None
            except Exception as e:
                print_error(f"Command failed: {e}")
                return None
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
            "Connection": ["connect", "disconnect", "status"],
            "General": ["help", "quit", "events", "clear", "commands"],
            "Safety": ["arm", "disarm", "activate", "deactivate", "estop", "safety"],
            "Actuators": ["led", "servo", "motor", "dc", "stepper", "gpio", "pwm"],
            "Sensors": ["encoder", "imu", "ultrasonic"],
            "Camera": ["cam"],
            "Telemetry": ["telem", "wifi", "log"],
            "Control": ["ctrl", "observer"],
            "Info": ["ping", "info", "version", "identity", "state", "rates"],
            "Advanced": ["send", "raw"],
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

    async def cmd_connect(self, args: list[str]) -> None:
        """Connect to robot.

        Usage:
            connect                    - Connect with default settings
            connect serial /dev/ttyUSB0 [baudrate]
            connect tcp host [port]
            connect ble device_name [baudrate]
        """
        if self.connected:
            print_info(f"Already connected to {self.current_connection_info}")
            print_info("Use 'disconnect' first to connect to a different device")
            return

        # Parse connection args
        if not args:
            # Use defaults
            await self.try_connect()
            return

        transport_type = args[0].lower()
        if transport_type == "serial":
            port = args[1] if len(args) > 1 else self.default_args.port
            baudrate = int(args[2]) if len(args) > 2 else self.default_args.baudrate
            await self.try_connect("serial", port=port, baudrate=baudrate)
        elif transport_type == "tcp":
            host = args[1] if len(args) > 1 else self.default_args.host
            port = int(args[2]) if len(args) > 2 else self.default_args.tcp_port
            await self.try_connect("tcp", host=host, port=port)
        elif transport_type == "ble":
            device_name = args[1] if len(args) > 1 else self.default_args.ble_name
            baudrate = int(args[2]) if len(args) > 2 else self.default_args.baudrate
            await self.try_connect("ble", device_name=device_name, baudrate=baudrate)
        else:
            print_error(f"Unknown transport type: {transport_type}")
            console.print("Usage:")
            console.print("  connect                         - Connect with default settings")
            console.print("  connect serial /dev/ttyUSB0     - Serial connection")
            console.print("  connect tcp 192.168.1.100 3333  - TCP connection")
            console.print("  connect ble MARA-Robot          - Bluetooth connection")

    async def cmd_disconnect(self, args: list[str]) -> None:
        """Disconnect from robot."""
        if not self.connected:
            print_info("Not connected")
            return

        await self.cleanup()
        print_success("Disconnected from robot")

    async def cmd_ping(self, args: list[str]) -> None:
        """Send ping."""
        if not self._require_connection():
            return
        await self.client.send_ping()
        print_info("Ping sent, awaiting pong...")

    async def cmd_status(self, args: list[str]) -> None:
        """Show status."""
        console.print()
        console.print("[bold]Connection Status:[/bold]")
        if self.connected:
            console.print(f"  Connected: [green]Yes[/green]")
            console.print(f"  Device: [cyan]{self.current_connection_info}[/cyan]")

            # Show connection monitor stats
            if self.client:
                stats = self.client.connection.get_stats()
                time_since = self.client.connection.time_since_last_message
                state = self.client.connection.state.value

                console.print(f"  State: [cyan]{state}[/cyan]")
                if time_since is not None:
                    console.print(f"  Last message: [cyan]{time_since:.2f}s ago[/cyan]")
                console.print(f"  Messages: [cyan]{stats.messages_received}[/cyan]")
                console.print(f"  Disconnects: [yellow]{stats.disconnects}[/yellow]")
                console.print(f"  Reconnects: [green]{stats.reconnects}[/green]")
                if stats.total_downtime_s > 0:
                    console.print(f"  Total downtime: [red]{stats.total_downtime_s:.2f}s[/red]")

                # Check heartbeat task status
                hb_task = getattr(self.client, '_heartbeat_task', None)
                if hb_task:
                    hb_status = "running" if not hb_task.done() else "stopped"
                    console.print(f"  Heartbeat task: [cyan]{hb_status}[/cyan]")
                else:
                    console.print(f"  Heartbeat task: [red]not started[/red]")
        else:
            console.print(f"  Connected: [red]No[/red]")
            # Show default connection info
            if self.default_args.transport == "serial":
                console.print(f"  Default: [dim]serial:{self.default_args.port}[/dim]")
            elif self.default_args.transport == "tcp":
                console.print(f"  Default: [dim]tcp:{self.default_args.host}:{self.default_args.tcp_port}[/dim]")
            else:
                console.print(f"  Default: [dim]ble:{self.default_args.ble_name}[/dim]")
        console.print(f"  Events logged: [cyan]{len(self.event_log)}[/cyan]")

        # Count heartbeats separately
        heartbeat_count = sum(1 for t, _ in self.event_log if t == "heartbeat")
        if heartbeat_count > 0:
            console.print(f"  Heartbeats: [dim]{heartbeat_count}[/dim]")

    async def cmd_events(self, args: list[str]) -> None:
        """Show recent events or toggle live display."""
        # Handle on/off toggle
        if args and args[0].lower() in ("on", "off"):
            self.show_events_live[0] = args[0].lower() == "on"
            status = "enabled" if self.show_events_live[0] else "disabled"
            print_success(f"Live event display {status}")
            return

        # Parse args
        show_all = False
        count = 10
        if args:
            if args[0].lower() == "all":
                show_all = True
                count = int(args[1]) if len(args) > 1 else 20
            else:
                try:
                    count = int(args[0])
                except ValueError:
                    print_error(f"Unknown argument: {args[0]}. Use: events [count|all|on|off]")
                    return

        if not self.event_log:
            print_info("No events yet")
            return

        # Filter events (skip heartbeats unless show_all)
        filtered = [(t, d) for t, d in self.event_log if show_all or t != "heartbeat"]

        if not filtered:
            print_info("No events (use 'events all' to include heartbeats)")
            return

        console.print()
        console.print(f"[bold]Recent Events (last {count}):[/bold]")
        console.print()

        for topic, data in filtered[-count:]:
            # Escape topic to prevent Rich markup interpretation
            safe_topic = escape(topic)
            # Format data - skip empty dicts
            if isinstance(data, dict) and not data:
                data_str = "[dim](empty)[/dim]"
            elif isinstance(data, dict):
                # Format dict more readably
                data_str = " ".join(f"{k}={v}" for k, v in data.items())
            else:
                data_str = str(data)

            if topic == "error":
                console.print(f"  [red]\\[{safe_topic}][/red] {data_str}")
            elif topic == "heartbeat":
                console.print(f"  [dim]\\[{safe_topic}][/dim] {data_str}")
            elif topic == "state":
                console.print(f"  [yellow]\\[{safe_topic}][/yellow] {data_str}")
            else:
                console.print(f"  [cyan]\\[{safe_topic}][/cyan] {data_str}")

    async def cmd_clear(self, args: list[str]) -> None:
        """Clear event log."""
        self.event_log.clear()
        print_success("Event log cleared")

    async def cmd_arm(self, args: list[str]) -> None:
        """Arm the robot."""
        if not self._require_connection():
            return
        await self.client.cmd_arm()
        print_success("Robot armed")

    async def cmd_disarm(self, args: list[str]) -> None:
        """Disarm the robot."""
        if not self._require_connection():
            return
        await self.client.cmd_disarm()
        print_success("Robot disarmed")

    async def cmd_active(self, args: list[str]) -> None:
        """Set mode to ACTIVE."""
        if not self._require_connection():
            return
        await self.client.cmd_set_mode("ACTIVE")
        print_success("Mode set to ACTIVE")

    async def cmd_idle(self, args: list[str]) -> None:
        """Set mode to IDLE."""
        if not self._require_connection():
            return
        await self.client.cmd_set_mode("IDLE")
        print_success("Mode set to IDLE")

    async def cmd_led(self, args: list[str]) -> None:
        """Control LED."""
        if not args:
            console.print("Usage: led on/off/blink")
            return
        if not self._require_connection():
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
        if not self._require_connection():
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
        if not self._require_connection():
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
        if not self._require_connection():
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
        if not self._require_connection():
            return
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
        if not self._require_connection():
            return
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
        if not self._require_connection():
            return

        import json
        try:
            cmd_str = " ".join(args)
            cmd_obj = json.loads(cmd_str)
            await self.client.send_command(cmd_obj)
            print_success("Command sent")
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON: {e}")

    # -------------------------------------------------------------------------
    # Generic command interface
    # -------------------------------------------------------------------------

    async def cmd_send(self, args: list[str]) -> None:
        """Send any command by name with key=value payload."""
        if not args:
            console.print("Usage: send CMD_NAME [key=value ...]")
            console.print("Example: send CMD_SERVO_SET_ANGLE servo_id=0 angle=180")
            console.print("Example: send CMD_ENCODER_READ encoder_id=0")
            console.print("Use 'commands' to list all available commands")
            return
        if not self._require_connection():
            return

        from mara_host.tools.schema import COMMANDS

        cmd_name = args[0].upper()
        if not cmd_name.startswith("CMD_"):
            cmd_name = "CMD_" + cmd_name

        if cmd_name not in COMMANDS:
            print_error(f"Unknown command: {cmd_name}")
            console.print("Use 'commands' to list all available commands")
            return

        # Parse key=value pairs
        payload = {}
        for arg in args[1:]:
            if "=" in arg:
                key, value = arg.split("=", 1)
                # Try to parse as number or bool
                try:
                    if value.lower() == "true":
                        payload[key] = True
                    elif value.lower() == "false":
                        payload[key] = False
                    elif "." in value:
                        payload[key] = float(value)
                    else:
                        payload[key] = int(value)
                except ValueError:
                    payload[key] = value  # Keep as string
            else:
                print_error(f"Invalid argument: {arg} (use key=value format)")
                return

        try:
            # Setup response listener before sending (avoid race condition)
            response_future: asyncio.Future = asyncio.get_event_loop().create_future()
            response_data = {}

            def on_response(data: dict) -> None:
                nonlocal response_data
                if not response_future.done():
                    response_data = data
                    response_future.set_result(data)

            self.client.bus.subscribe(f"cmd.{cmd_name}", on_response)

            try:
                # Send the command
                ok, err = await self.client.send_reliable(cmd_name, payload)

                if ok:
                    print_success(f"{cmd_name} sent successfully")

                    # Wait briefly for response data (MCU sends response with ACK)
                    try:
                        data = await asyncio.wait_for(response_future, timeout=0.5)
                        if data:
                            # Filter out metadata fields to show useful response data
                            skip_fields = {"cmd", "ok", "seq", "src", "error", "error_code", "error_code_enum"}
                            useful_data = {k: v for k, v in data.items() if k not in skip_fields}
                            if useful_data:
                                console.print()
                                console.print("[bold cyan]Response:[/bold cyan]")
                                for key, value in useful_data.items():
                                    console.print(f"  {key}: [green]{value}[/green]")
                    except asyncio.TimeoutError:
                        pass  # No additional response data
                else:
                    print_error(f"{cmd_name} failed: {err}")
            finally:
                # Unsubscribe to prevent memory leaks
                self.client.bus.unsubscribe(f"cmd.{cmd_name}", on_response)
        except Exception as e:
            print_error(f"Error: {e}")

    async def cmd_commands(self, args: list[str]) -> None:
        """List all available commands."""
        from mara_host.tools.schema import COMMANDS
        from collections import defaultdict

        # Group by prefix
        groups = defaultdict(list)
        for cmd in sorted(COMMANDS.keys()):
            parts = cmd.split("_")
            prefix = parts[1] if len(parts) > 1 else "OTHER"
            groups[prefix].append(cmd)

        # Filter by search term if provided
        search = args[0].upper() if args else None

        console.print()
        console.print(f"[bold]Available Commands ({len(COMMANDS)} total):[/bold]")
        console.print()

        for prefix in sorted(groups.keys()):
            cmds = groups[prefix]
            if search and search not in prefix:
                cmds = [c for c in cmds if search in c]
                if not cmds:
                    continue

            console.print(f"[bold cyan]{prefix}:[/bold cyan]")
            for cmd in cmds:
                desc = COMMANDS[cmd].get("description", "")[:50]
                console.print(f"  [green]{cmd:30}[/green] {desc}")
            console.print()

    # -------------------------------------------------------------------------
    # Additional safety commands
    # -------------------------------------------------------------------------

    async def cmd_deactivate(self, args: list[str]) -> None:
        """Set mode to IDLE."""
        if not self._require_connection():
            return
        await self.client.send_reliable("CMD_DEACTIVATE", {})
        print_success("Mode set to IDLE")

    async def cmd_estop(self, args: list[str]) -> None:
        """Emergency stop."""
        if not self._require_connection():
            return
        await self.client.send_reliable("CMD_ESTOP", {})
        print_error("EMERGENCY STOP activated!")

    async def cmd_safety(self, args: list[str]) -> None:
        """Safety timeout control."""
        if not args:
            console.print("Usage:")
            console.print("  safety status              Show current timeout settings")
            console.print("  safety on                  Enable timeouts (3000ms host, 500ms motion)")
            console.print("  safety off                 Disable timeouts (0ms = disabled)")
            console.print("  safety set <host> <motion> Set specific timeout values (ms)")
            return
        if not self._require_connection():
            return

        action = args[0].lower()

        if action == "status":
            # Get current timeout settings
            response_future: asyncio.Future = asyncio.get_event_loop().create_future()

            def on_response(data: dict) -> None:
                if not response_future.done():
                    response_future.set_result(data)

            self.client.bus.subscribe("cmd.CMD_GET_SAFETY_TIMEOUTS", on_response)

            try:
                ok, err = await self.client.send_reliable("CMD_GET_SAFETY_TIMEOUTS", {})
                if not ok:
                    print_error(f"Failed to get safety timeouts: {err}")
                    return

                try:
                    data = await asyncio.wait_for(response_future, timeout=2.0)
                    console.print()
                    console.print("[bold]Safety Timeouts:[/bold]")
                    host_ms = data.get("host_timeout_ms", 0)
                    motion_ms = data.get("motion_timeout_ms", 0)
                    enabled = data.get("enabled", False)

                    status = "[green]enabled[/green]" if enabled else "[yellow]disabled[/yellow]"
                    console.print(f"  Status: {status}")
                    console.print(f"  Host timeout:   [cyan]{host_ms}[/cyan] ms {'(disabled)' if host_ms == 0 else ''}")
                    console.print(f"  Motion timeout: [cyan]{motion_ms}[/cyan] ms {'(disabled)' if motion_ms == 0 else ''}")
                except asyncio.TimeoutError:
                    print_error("Safety timeout query timed out")
            finally:
                self.client.bus.unsubscribe("cmd.CMD_GET_SAFETY_TIMEOUTS", on_response)

        elif action == "on":
            # Enable with default values
            ok, err = await self.client.send_reliable("CMD_SET_SAFETY_TIMEOUTS", {
                "host_timeout_ms": 3000,
                "motion_timeout_ms": 500
            })
            if ok:
                print_success("Safety timeouts enabled (host=3000ms, motion=500ms)")
            else:
                print_error(f"Failed to enable timeouts: {err}")

        elif action == "off":
            # Disable (set to 0)
            ok, err = await self.client.send_reliable("CMD_SET_SAFETY_TIMEOUTS", {
                "host_timeout_ms": 0,
                "motion_timeout_ms": 0
            })
            if ok:
                print_success("Safety timeouts disabled")
            else:
                print_error(f"Failed to disable timeouts: {err}")

        elif action == "set" and len(args) >= 3:
            host_ms = int(args[1])
            motion_ms = int(args[2])
            ok, err = await self.client.send_reliable("CMD_SET_SAFETY_TIMEOUTS", {
                "host_timeout_ms": host_ms,
                "motion_timeout_ms": motion_ms
            })
            if ok:
                print_success(f"Safety timeouts set (host={host_ms}ms, motion={motion_ms}ms)")
            else:
                print_error(f"Failed to set timeouts: {err}")

        else:
            print_error(f"Unknown safety action: {args[0]}")
            console.print("Use: safety status | on | off | set <host_ms> <motion_ms>")

    async def cmd_state(self, args: list[str]) -> None:
        """Get robot state."""
        if not self._require_connection():
            return

        # Setup response listener
        response_future: asyncio.Future = asyncio.get_event_loop().create_future()

        def on_response(data: dict) -> None:
            if not response_future.done():
                response_future.set_result(data)

        self.client.bus.subscribe("cmd.CMD_GET_STATE", on_response)

        try:
            ok, err = await self.client.send_reliable("CMD_GET_STATE", {})
            if not ok:
                print_error(f"Failed to get state: {err}")
                return

            # Wait for response
            try:
                data = await asyncio.wait_for(response_future, timeout=2.0)
                state = data.get("state", "?")
                armed = data.get("armed", "?")
                mode = data.get("mode", "?")

                console.print()
                console.print("[bold]Robot State:[/bold]")
                console.print(f"  State: [green]{state}[/green]")
                console.print(f"  Armed: [green]{armed}[/green]")
                console.print(f"  Mode:  [green]{mode}[/green]")

                # Show additional fields if present
                skip_fields = {"cmd", "ok", "seq", "src", "state", "armed", "mode", "error", "error_code"}
                extra = {k: v for k, v in data.items() if k not in skip_fields}
                if extra:
                    for key, value in extra.items():
                        console.print(f"  {key}: [cyan]{value}[/cyan]")
            except asyncio.TimeoutError:
                print_error("State response timed out")
        finally:
            self.client.bus.unsubscribe("cmd.CMD_GET_STATE", on_response)

    async def cmd_rates(self, args: list[str]) -> None:
        """Get loop rates."""
        if not self._require_connection():
            return

        # Setup response listener
        response_future: asyncio.Future = asyncio.get_event_loop().create_future()

        def on_response(data: dict) -> None:
            if not response_future.done():
                response_future.set_result(data)

        self.client.bus.subscribe("cmd.CMD_GET_RATES", on_response)

        try:
            ok, err = await self.client.send_reliable("CMD_GET_RATES", {})
            if not ok:
                print_error(f"Failed to get rates: {err}")
                return

            # Wait for response
            try:
                data = await asyncio.wait_for(response_future, timeout=2.0)
                console.print()
                console.print("[bold]Loop Rates:[/bold]")
                console.print(f"  Control:   [green]{data.get('ctrl_hz', '?')} Hz[/green] ({data.get('ctrl_ms', '?')} ms)")
                console.print(f"  Safety:    [green]{data.get('safety_hz', '?')} Hz[/green] ({data.get('safety_ms', '?')} ms)")
                console.print(f"  Telemetry: [green]{data.get('telem_hz', '?')} Hz[/green] ({data.get('telem_ms', '?')} ms)")
            except asyncio.TimeoutError:
                print_error("Rates response timed out")
        finally:
            self.client.bus.unsubscribe("cmd.CMD_GET_RATES", on_response)

    # -------------------------------------------------------------------------
    # DC Motor commands
    # -------------------------------------------------------------------------

    async def cmd_dc(self, args: list[str]) -> None:
        """DC motor control."""
        if not args:
            console.print("Usage:")
            console.print("  dc set <id> <speed>      Set motor speed (-1.0 to 1.0)")
            console.print("  dc stop <id>             Stop motor")
            console.print("  dc gains <id> <kp> <ki>  Set velocity PID gains")
            return
        if not self._require_connection():
            return

        action = args[0].lower()
        if action == "set" and len(args) >= 3:
            motor_id = int(args[1])
            speed = float(args[2])
            await self.client.send_reliable("CMD_DC_SET_SPEED", {"motor_id": motor_id, "speed": speed})
            print_success(f"DC motor {motor_id} speed set to {speed}")
        elif action == "stop" and len(args) >= 2:
            motor_id = int(args[1])
            await self.client.send_reliable("CMD_DC_STOP", {"motor_id": motor_id})
            print_success(f"DC motor {motor_id} stopped")
        elif action == "gains" and len(args) >= 4:
            motor_id = int(args[1])
            kp = float(args[2])
            ki = float(args[3])
            await self.client.send_reliable("CMD_DC_SET_VEL_GAINS", {"motor_id": motor_id, "kp": kp, "ki": ki})
            print_success(f"DC motor {motor_id} gains set: kp={kp}, ki={ki}")
        else:
            print_error(f"Unknown dc action: {args}")

    # -------------------------------------------------------------------------
    # Stepper Motor commands
    # -------------------------------------------------------------------------

    async def cmd_stepper(self, args: list[str]) -> None:
        """Stepper motor control."""
        if not args:
            console.print("Usage:")
            console.print("  stepper move <id> <steps> [speed_rps]  Move relative steps")
            console.print("  stepper deg <id> <degrees> [speed]     Move relative degrees")
            console.print("  stepper stop <id>                      Stop motor")
            console.print("  stepper enable <id> [0/1]              Enable/disable motor")
            console.print("  stepper home <id> [speed]              Home the motor")
            console.print("  stepper pos <id>                       Get position")
            return
        if not self._require_connection():
            return

        action = args[0].lower()
        if action == "move" and len(args) >= 3:
            stepper_id = int(args[1])
            steps = int(args[2])
            speed = float(args[3]) if len(args) > 3 else 1.0
            await self.client.send_reliable("CMD_STEPPER_MOVE_REL", {"stepper_id": stepper_id, "steps": steps, "speed_rps": speed})
            print_success(f"Stepper {stepper_id} moving {steps} steps")
        elif action == "deg" and len(args) >= 3:
            stepper_id = int(args[1])
            degrees = float(args[2])
            speed = float(args[3]) if len(args) > 3 else 1.0
            await self.client.send_reliable("CMD_STEPPER_MOVE_DEG", {"stepper_id": stepper_id, "degrees": degrees, "speed_rps": speed})
            print_success(f"Stepper {stepper_id} moving {degrees} degrees")
        elif action == "stop" and len(args) >= 2:
            stepper_id = int(args[1])
            await self.client.send_reliable("CMD_STEPPER_STOP", {"stepper_id": stepper_id})
            print_success(f"Stepper {stepper_id} stopped")
        elif action == "enable" and len(args) >= 2:
            stepper_id = int(args[1])
            enable = bool(int(args[2])) if len(args) > 2 else True
            await self.client.send_reliable("CMD_STEPPER_ENABLE", {"stepper_id": stepper_id, "enable": enable})
            print_success(f"Stepper {stepper_id} {'enabled' if enable else 'disabled'}")
        elif action == "home" and len(args) >= 2:
            stepper_id = int(args[1])
            speed = float(args[2]) if len(args) > 2 else 0.5
            await self.client.send_reliable("CMD_STEPPER_HOME", {"stepper_id": stepper_id, "speed_rps": speed})
            print_success(f"Stepper {stepper_id} homing")
        elif action == "pos" and len(args) >= 2:
            stepper_id = int(args[1])
            await self.client.send_reliable("CMD_STEPPER_GET_POSITION", {"stepper_id": stepper_id})
            print_info(f"Position requested for stepper {stepper_id} (check events)")
        else:
            print_error(f"Unknown stepper action: {args}")

    # -------------------------------------------------------------------------
    # PWM command
    # -------------------------------------------------------------------------

    async def cmd_pwm(self, args: list[str]) -> None:
        """PWM control."""
        if len(args) < 2:
            console.print("Usage: pwm <channel> <duty> [freq_hz]")
            console.print("  duty: 0.0 to 1.0")
            console.print("  freq: frequency in Hz (default: 1000)")
            return
        if not self._require_connection():
            return

        channel = int(args[0])
        duty = float(args[1])
        freq = float(args[2]) if len(args) > 2 else 1000.0
        await self.client.send_reliable("CMD_PWM_SET", {"channel": channel, "duty": duty, "freq_hz": freq})
        print_success(f"PWM channel {channel} set to {duty*100:.1f}% duty @ {freq}Hz")

    # -------------------------------------------------------------------------
    # Encoder commands
    # -------------------------------------------------------------------------

    async def cmd_encoder(self, args: list[str]) -> None:
        """Encoder commands."""
        if not args:
            console.print("Usage:")
            console.print("  encoder attach <id> <pin_a> <pin_b> [ppr]  Attach encoder")
            console.print("  encoder read <id>                          Read encoder")
            console.print("  encoder reset <id>                         Reset count")
            console.print("  encoder detach <id>                        Detach encoder")
            return
        if not self._require_connection():
            return

        action = args[0].lower()
        if action == "attach" and len(args) >= 4:
            encoder_id = int(args[1])
            pin_a = int(args[2])
            pin_b = int(args[3])
            ppr = int(args[4]) if len(args) > 4 else 20
            await self.client.send_reliable("CMD_ENCODER_ATTACH", {"encoder_id": encoder_id, "pin_a": pin_a, "pin_b": pin_b, "ppr": ppr})
            print_success(f"Encoder {encoder_id} attached to pins {pin_a}/{pin_b}")
        elif action == "read" and len(args) >= 2:
            encoder_id = int(args[1])
            await self.client.send_reliable("CMD_ENCODER_READ", {"encoder_id": encoder_id})
            print_info(f"Encoder {encoder_id} read requested (check events)")
        elif action == "reset" and len(args) >= 2:
            encoder_id = int(args[1])
            await self.client.send_reliable("CMD_ENCODER_RESET", {"encoder_id": encoder_id})
            print_success(f"Encoder {encoder_id} reset")
        elif action == "detach" and len(args) >= 2:
            encoder_id = int(args[1])
            await self.client.send_reliable("CMD_ENCODER_DETACH", {"encoder_id": encoder_id})
            print_success(f"Encoder {encoder_id} detached")
        else:
            print_error(f"Unknown encoder action: {args}")

    # -------------------------------------------------------------------------
    # IMU commands
    # -------------------------------------------------------------------------

    async def cmd_imu(self, args: list[str]) -> None:
        """IMU commands."""
        if not args:
            console.print("Usage:")
            console.print("  imu read                        Read IMU data")
            console.print("  imu calibrate [samples] [delay] Calibrate IMU")
            console.print("  imu bias <ax> <ay> <az> <gx> <gy> <gz>  Set bias")
            console.print("  imu attach <type>               Attach IMU (mpu6050, etc)")
            return
        if not self._require_connection():
            return

        action = args[0].lower()
        if action == "read":
            await self.client.send_reliable("CMD_IMU_READ", {})
            print_info("IMU read requested (check events)")
        elif action == "calibrate":
            samples = int(args[1]) if len(args) > 1 else 100
            delay_ms = int(args[2]) if len(args) > 2 else 10
            await self.client.send_reliable("CMD_IMU_CALIBRATE", {"samples": samples, "delay_ms": delay_ms})
            print_info(f"IMU calibration started ({samples} samples)")
        elif action == "bias" and len(args) >= 7:
            await self.client.send_reliable("CMD_IMU_SET_BIAS", {
                "ax": float(args[1]), "ay": float(args[2]), "az": float(args[3]),
                "gx": float(args[4]), "gy": float(args[5]), "gz": float(args[6]),
            })
            print_success("IMU bias set")
        elif action == "attach" and len(args) >= 2:
            imu_type = args[1]
            await self.client.send_reliable("CMD_IMU_ATTACH", {"type": imu_type})
            print_success(f"IMU {imu_type} attached")
        else:
            print_error(f"Unknown imu action: {args}")

    # -------------------------------------------------------------------------
    # Ultrasonic commands
    # -------------------------------------------------------------------------

    async def cmd_ultrasonic(self, args: list[str]) -> None:
        """Ultrasonic sensor commands."""
        if not args:
            console.print("Usage:")
            console.print("  ultrasonic attach <id> <trig> <echo>  Attach sensor")
            console.print("  ultrasonic read <id>                  Read distance")
            console.print("  ultrasonic detach <id>                Detach sensor")
            return
        if not self._require_connection():
            return

        action = args[0].lower()
        if action == "attach" and len(args) >= 4:
            sensor_id = int(args[1])
            trig_pin = int(args[2])
            echo_pin = int(args[3])
            await self.client.send_reliable("CMD_ULTRASONIC_ATTACH", {"sensor_id": sensor_id, "trig_pin": trig_pin, "echo_pin": echo_pin})
            print_success(f"Ultrasonic {sensor_id} attached (trig={trig_pin}, echo={echo_pin})")
        elif action == "read" and len(args) >= 2:
            sensor_id = int(args[1])
            await self.client.send_reliable("CMD_ULTRASONIC_READ", {"sensor_id": sensor_id})
            print_info(f"Ultrasonic {sensor_id} read requested (check events)")
        elif action == "detach" and len(args) >= 2:
            sensor_id = int(args[1])
            await self.client.send_reliable("CMD_ULTRASONIC_DETACH", {"sensor_id": sensor_id})
            print_success(f"Ultrasonic {sensor_id} detached")
        else:
            print_error(f"Unknown ultrasonic action: {args}")

    # -------------------------------------------------------------------------
    # Camera commands
    # -------------------------------------------------------------------------

    async def cmd_cam(self, args: list[str]) -> None:
        """Camera commands."""
        if not args:
            console.print("Usage:")
            console.print("  cam capture                 Capture frame")
            console.print("  cam stream start/stop       Control streaming")
            console.print("  cam preset <name>           Apply preset")
            console.print("  cam flash on/off            Control flash")
            console.print("  cam resolution <w> <h>      Set resolution")
            return
        if not self._require_connection():
            return

        action = args[0].lower()
        if action == "capture":
            await self.client.send_reliable("CMD_CAM_CAPTURE_FRAME", {})
            print_info("Camera capture requested")
        elif action == "stream" and len(args) >= 2:
            if args[1].lower() == "start":
                await self.client.send_reliable("CMD_CAM_STREAM_START", {})
                print_success("Camera streaming started")
            else:
                await self.client.send_reliable("CMD_CAM_STREAM_STOP", {})
                print_success("Camera streaming stopped")
        elif action == "preset" and len(args) >= 2:
            preset = args[1]
            await self.client.send_reliable("CMD_CAM_APPLY_PRESET", {"preset": preset})
            print_success(f"Camera preset '{preset}' applied")
        elif action == "flash" and len(args) >= 2:
            enable = args[1].lower() in ("on", "1", "true")
            await self.client.send_reliable("CMD_CAM_FLASH", {"enable": enable})
            print_success(f"Camera flash {'on' if enable else 'off'}")
        elif action == "resolution" and len(args) >= 3:
            width = int(args[1])
            height = int(args[2])
            await self.client.send_reliable("CMD_CAM_SET_RESOLUTION", {"width": width, "height": height})
            print_success(f"Camera resolution set to {width}x{height}")
        else:
            print_error(f"Unknown cam action: {args}")

    # -------------------------------------------------------------------------
    # Telemetry commands
    # -------------------------------------------------------------------------

    async def cmd_telem(self, args: list[str]) -> None:
        """Telemetry commands."""
        if not args:
            console.print("Usage:")
            console.print("  telem rate <hz>        Set telemetry rate")
            console.print("  telem interval <ms>    Set telemetry interval")
            return
        if not self._require_connection():
            return

        action = args[0].lower()
        if action == "rate" and len(args) >= 2:
            rate = int(args[1])
            await self.client.send_reliable("CMD_TELEM_SET_RATE", {"rate_hz": rate})
            print_success(f"Telemetry rate set to {rate} Hz")
        elif action == "interval" and len(args) >= 2:
            interval = int(args[1])
            await self.client.send_reliable("CMD_TELEM_SET_INTERVAL", {"interval_ms": interval})
            print_success(f"Telemetry interval set to {interval} ms")
        else:
            print_error(f"Unknown telem action: {args}")

    # -------------------------------------------------------------------------
    # WiFi commands
    # -------------------------------------------------------------------------

    async def cmd_wifi(self, args: list[str]) -> None:
        """WiFi commands."""
        if not args:
            console.print("Usage:")
            console.print("  wifi status            Get WiFi status")
            console.print("  wifi scan              Scan for networks")
            console.print("  wifi join <ssid> <pw>  Connect to network")
            console.print("  wifi disconnect        Disconnect from network")
            return
        if not self._require_connection():
            return

        action = args[0].lower()
        if action == "status":
            await self.client.send_reliable("CMD_WIFI_STATUS", {})
            print_info("WiFi status requested (check events)")
        elif action == "scan":
            await self.client.send_reliable("CMD_WIFI_SCAN", {})
            print_info("WiFi scan started (check events)")
        elif action == "join" and len(args) >= 3:
            ssid = args[1]
            password = args[2]
            await self.client.send_reliable("CMD_WIFI_JOIN", {"ssid": ssid, "password": password})
            print_info(f"Connecting to WiFi '{ssid}'...")
        elif action == "disconnect":
            await self.client.send_reliable("CMD_WIFI_DISCONNECT", {})
            print_success("WiFi disconnected")
        else:
            print_error(f"Unknown wifi action: {args}")

    # -------------------------------------------------------------------------
    # Control graph commands
    # -------------------------------------------------------------------------

    async def cmd_ctrl(self, args: list[str]) -> None:
        """Control graph commands."""
        if not args:
            console.print("Usage:")
            console.print("  ctrl status            Get control graph status")
            console.print("  ctrl enable            Enable control graph")
            console.print("  ctrl disable           Disable control graph")
            console.print("  ctrl clear             Clear control graph")
            return
        if not self._require_connection():
            return

        action = args[0].lower()
        if action == "status":
            await self.client.send_reliable("CMD_CTRL_GRAPH_STATUS", {})
            print_info("Control graph status requested (check events)")
        elif action == "enable":
            await self.client.send_reliable("CMD_CTRL_GRAPH_ENABLE", {})
            print_success("Control graph enabled")
        elif action == "disable":
            await self.client.send_reliable("CMD_CTRL_GRAPH_DISABLE", {})
            print_success("Control graph disabled")
        elif action == "clear":
            await self.client.send_reliable("CMD_CTRL_GRAPH_CLEAR", {})
            print_success("Control graph cleared")
        else:
            print_error(f"Unknown ctrl action: {args}")

    # -------------------------------------------------------------------------
    # Observer commands
    # -------------------------------------------------------------------------

    async def cmd_observer(self, args: list[str]) -> None:
        """Observer commands."""
        if not args:
            console.print("Usage:")
            console.print("  observer status            Get observer status")
            console.print("  observer enable <id>       Enable observer")
            console.print("  observer disable <id>      Disable observer")
            console.print("  observer reset <id>        Reset observer")
            return
        if not self._require_connection():
            return

        action = args[0].lower()
        if action == "status":
            await self.client.send_reliable("CMD_OBSERVER_STATUS", {})
            print_info("Observer status requested (check events)")
        elif action == "enable" and len(args) >= 2:
            observer_id = int(args[1])
            await self.client.send_reliable("CMD_OBSERVER_ENABLE", {"observer_id": observer_id, "enable": True})
            print_success(f"Observer {observer_id} enabled")
        elif action == "disable" and len(args) >= 2:
            observer_id = int(args[1])
            await self.client.send_reliable("CMD_OBSERVER_ENABLE", {"observer_id": observer_id, "enable": False})
            print_success(f"Observer {observer_id} disabled")
        elif action == "reset" and len(args) >= 2:
            observer_id = int(args[1])
            await self.client.send_reliable("CMD_OBSERVER_RESET", {"observer_id": observer_id})
            print_success(f"Observer {observer_id} reset")
        else:
            print_error(f"Unknown observer action: {args}")

    # -------------------------------------------------------------------------
    # Logging commands
    # -------------------------------------------------------------------------

    async def cmd_log(self, args: list[str]) -> None:
        """MCU logging commands."""
        if not args:
            console.print("Usage:")
            console.print("  log level <level>              Set global MCU log level (debug/info/warn/error/off)")
            console.print("  log <subsystem> <level>        Set subsystem log level (e.g., log servo debug)")
            console.print("  log levels                     Get current log levels")
            console.print("  log clear                      Clear subsystem overrides")
            console.print()
            console.print("Subsystems: servo, motor, control, gpio, encoder, imu, safety, telem")
            return
        if not self._require_connection():
            return

        action = args[0].lower()

        # Global level: log level <level>
        if action == "level" and len(args) >= 2:
            level = args[1].lower()
            if level not in ("debug", "info", "warn", "error", "off"):
                print_error(f"Invalid level: {level}. Use: debug, info, warn, error, off")
                return
            await self.client.send_reliable("CMD_SET_LOG_LEVEL", {"level": level})
            print_success(f"MCU global log level set to {level}")

        # Get levels: log levels
        elif action == "levels":
            response_future: asyncio.Future = asyncio.get_event_loop().create_future()

            def on_response(data: dict) -> None:
                if not response_future.done():
                    response_future.set_result(data)

            self.client.bus.subscribe("cmd.CMD_GET_LOG_LEVELS", on_response)

            try:
                ok, err = await self.client.send_reliable("CMD_GET_LOG_LEVELS", {})
                if not ok:
                    print_error(f"Failed to get log levels: {err}")
                    return

                try:
                    data = await asyncio.wait_for(response_future, timeout=2.0)
                    console.print()
                    console.print("[bold]MCU Log Levels:[/bold]")
                    console.print(f"  Global: [green]{data.get('global', '?')}[/green]")
                    subsystems = data.get("subsystems", {})
                    if subsystems:
                        console.print("  Subsystem overrides:")
                        for sub, level in subsystems.items():
                            console.print(f"    {sub}: [cyan]{level}[/cyan]")
                    else:
                        console.print("  [dim]No subsystem overrides[/dim]")
                except asyncio.TimeoutError:
                    print_error("Log levels response timed out")
            finally:
                self.client.bus.unsubscribe("cmd.CMD_GET_LOG_LEVELS", on_response)

        # Clear overrides: log clear
        elif action == "clear":
            await self.client.send_reliable("CMD_CLEAR_SUBSYSTEM_LOG_LEVELS", {})
            print_success("Subsystem log level overrides cleared")

        # Subsystem level: log <subsystem> <level>
        elif len(args) >= 2:
            subsystem = args[0].lower()
            level = args[1].lower()
            if level not in ("debug", "info", "warn", "error", "off"):
                print_error(f"Invalid level: {level}. Use: debug, info, warn, error, off")
                return
            await self.client.send_reliable("CMD_SET_SUBSYSTEM_LOG_LEVEL", {"subsystem": subsystem, "level": level})
            print_success(f"MCU {subsystem} log level set to {level}")

        else:
            print_error(f"Unknown log action: {args}")
