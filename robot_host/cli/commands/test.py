# robot_host/cli/commands/test.py
"""Robot self-test commands for MARA CLI."""

import argparse
import asyncio
import time
from typing import Optional
from dataclasses import dataclass

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.prompt import Confirm

from robot_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
    print_warning,
)


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    message: str
    duration_ms: float = 0


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register test commands."""
    test_parser = subparsers.add_parser(
        "test",
        help="Run robot self-tests",
        description="Run self-tests to verify robot functionality",
    )

    test_sub = test_parser.add_subparsers(
        dest="test_cmd",
        title="tests",
        metavar="<test>",
    )

    # Common args
    def add_transport_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("-p", "--port", default="/dev/cu.usbserial-0001")
        p.add_argument("--tcp", metavar="HOST", help="Use TCP instead of serial")

    # all - run all tests
    all_p = test_sub.add_parser(
        "all",
        help="Run all self-tests",
    )
    add_transport_args(all_p)
    all_p.set_defaults(func=cmd_all)

    # connection
    conn_p = test_sub.add_parser(
        "connection",
        help="Test connection and communication",
    )
    add_transport_args(conn_p)
    conn_p.set_defaults(func=cmd_connection)

    # motors
    motors_p = test_sub.add_parser(
        "motors",
        help="Test motors",
    )
    add_transport_args(motors_p)
    motors_p.add_argument("--ids", default="0,1", help="Motor IDs to test (comma-separated)")
    motors_p.set_defaults(func=cmd_motors)

    # encoders
    encoders_p = test_sub.add_parser(
        "encoders",
        help="Test encoders",
    )
    add_transport_args(encoders_p)
    encoders_p.add_argument("--ids", default="0,1", help="Encoder IDs to test")
    encoders_p.set_defaults(func=cmd_encoders)

    # servos
    servos_p = test_sub.add_parser(
        "servos",
        help="Test servos",
    )
    add_transport_args(servos_p)
    servos_p.add_argument("--ids", default="0", help="Servo IDs to test")
    servos_p.set_defaults(func=cmd_servos)

    # sensors
    sensors_p = test_sub.add_parser(
        "sensors",
        help="Test sensors (IMU, ultrasonic)",
    )
    add_transport_args(sensors_p)
    sensors_p.set_defaults(func=cmd_sensors)

    # gpio
    gpio_p = test_sub.add_parser(
        "gpio",
        help="Test GPIO pins",
    )
    add_transport_args(gpio_p)
    gpio_p.set_defaults(func=cmd_gpio)

    # Default
    test_parser.set_defaults(func=cmd_all)


def cmd_all(args: argparse.Namespace) -> int:
    """Run all self-tests."""
    console.print()
    console.print("[bold cyan]Robot Self-Test Suite[/bold cyan]")
    console.print()

    return asyncio.run(_run_all_tests(args))


async def _run_all_tests(args: argparse.Namespace) -> int:
    """Run all tests."""
    from robot_host.command.client import AsyncRobotClient

    # Create transport
    if getattr(args, 'tcp', None):
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)

    client = AsyncRobotClient(transport, connection_timeout_s=6.0)
    results: list[TestResult] = []

    try:
        # Test 1: Connection
        start = time.time()
        try:
            await client.start()
            results.append(TestResult(
                "Connection",
                True,
                "Connected successfully",
                (time.time() - start) * 1000
            ))
        except Exception as e:
            results.append(TestResult("Connection", False, str(e)))
            _print_results(results)
            return 1

        # Test 2: Ping/Pong
        start = time.time()
        pong_received = asyncio.Event()

        def on_pong(data):
            pong_received.set()

        client.bus.subscribe("pong", on_pong)
        await client.send_ping()

        try:
            await asyncio.wait_for(pong_received.wait(), timeout=2.0)
            results.append(TestResult(
                "Ping/Pong",
                True,
                "Response received",
                (time.time() - start) * 1000
            ))
        except asyncio.TimeoutError:
            results.append(TestResult("Ping/Pong", False, "Timeout - no response"))

        # Test 3: Arm/Disarm
        start = time.time()
        try:
            await client.cmd_arm()
            await asyncio.sleep(0.1)
            await client.cmd_disarm()
            results.append(TestResult(
                "Arm/Disarm",
                True,
                "State transitions OK",
                (time.time() - start) * 1000
            ))
        except Exception as e:
            results.append(TestResult("Arm/Disarm", False, str(e)))

        # Test 4: Mode switching
        start = time.time()
        try:
            await client.cmd_set_mode("IDLE")
            await asyncio.sleep(0.1)
            await client.cmd_set_mode("ACTIVE")
            await asyncio.sleep(0.1)
            await client.cmd_set_mode("IDLE")
            results.append(TestResult(
                "Mode Switch",
                True,
                "IDLE -> ACTIVE -> IDLE OK",
                (time.time() - start) * 1000
            ))
        except Exception as e:
            results.append(TestResult("Mode Switch", False, str(e)))

        # Test 5: LED
        start = time.time()
        try:
            await client.cmd_led_on()
            await asyncio.sleep(0.2)
            await client.cmd_led_off()
            results.append(TestResult(
                "LED Control",
                True,
                "On/Off commands sent",
                (time.time() - start) * 1000
            ))
        except Exception as e:
            results.append(TestResult("LED Control", False, str(e)))

        # Test 6: Heartbeat reception
        start = time.time()
        heartbeat_received = asyncio.Event()

        def on_heartbeat(data):
            heartbeat_received.set()

        client.bus.subscribe("heartbeat", on_heartbeat)

        try:
            await asyncio.wait_for(heartbeat_received.wait(), timeout=3.0)
            results.append(TestResult(
                "Heartbeat",
                True,
                "Receiving heartbeats",
                (time.time() - start) * 1000
            ))
        except asyncio.TimeoutError:
            results.append(TestResult("Heartbeat", False, "No heartbeat received"))

    finally:
        await client.stop()

    _print_results(results)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    return 0 if failed == 0 else 1


def _print_results(results: list[TestResult]) -> None:
    """Print test results table."""
    console.print()

    table = Table(title="Test Results", show_header=True)
    table.add_column("Test", style="cyan")
    table.add_column("Result", justify="center")
    table.add_column("Time", justify="right")
    table.add_column("Message")

    for r in results:
        result_str = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        time_str = f"{r.duration_ms:.0f}ms" if r.duration_ms > 0 else "-"
        if r.passed:
            msg = r.message
        else:
            msg = f"[red]{r.message}[/red]"
        table.add_row(r.name, result_str, time_str, msg)

    console.print(table)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    console.print()
    if failed == 0:
        print_success(f"All {passed} tests passed")
    else:
        print_error(f"{failed} of {len(results)} tests failed")


def cmd_connection(args: argparse.Namespace) -> int:
    """Test connection only."""
    console.print()
    console.print("[bold cyan]Connection Test[/bold cyan]")
    console.print()

    return asyncio.run(_test_connection(args))


async def _test_connection(args: argparse.Namespace) -> int:
    """Run connection test."""
    from robot_host.command.client import AsyncRobotClient

    if getattr(args, 'tcp', None):
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
        console.print(f"  Transport: TCP ({args.tcp}:3333)")
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)
        console.print(f"  Transport: Serial ({args.port})")

    console.print()

    client = AsyncRobotClient(transport, connection_timeout_s=6.0)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Connecting...", total=None)

        start = time.time()
        try:
            await client.start()
            elapsed = (time.time() - start) * 1000
            progress.update(task, description="Testing ping...")

            # Test ping
            pong = asyncio.Event()
            client.bus.subscribe("pong", lambda d: pong.set())
            await client.send_ping()

            try:
                await asyncio.wait_for(pong.wait(), timeout=2.0)
                print_success(f"Connected and responsive (latency: {elapsed:.0f}ms)")
            except asyncio.TimeoutError:
                print_warning("Connected but no ping response")

        except Exception as e:
            print_error(f"Connection failed: {e}")
            return 1
        finally:
            await client.stop()

    return 0


def cmd_motors(args: argparse.Namespace) -> int:
    """Test motors."""
    motor_ids = [int(x.strip()) for x in args.ids.split(",")]

    console.print()
    console.print("[bold cyan]Motor Test[/bold cyan]")
    console.print(f"  Motors: {motor_ids}")
    console.print()

    print_warning("Motors will spin briefly. Make sure wheels are off the ground!")

    if not Confirm.ask("Continue?", default=True):
        return 0

    return asyncio.run(_test_motors(args, motor_ids))


async def _test_motors(args: argparse.Namespace, motor_ids: list[int]) -> int:
    """Run motor test."""
    from robot_host.command.client import AsyncRobotClient

    if getattr(args, 'tcp', None):
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)

    client = AsyncRobotClient(transport)
    results = []

    try:
        await client.start()
        await client.cmd_arm()
        await client.cmd_set_mode("ACTIVE")

        for motor_id in motor_ids:
            console.print(f"  Testing motor {motor_id}...")

            try:
                # Forward
                await client.cmd_dc_set_speed(motor_id, 0.3)
                await asyncio.sleep(0.5)

                # Reverse
                await client.cmd_dc_set_speed(motor_id, -0.3)
                await asyncio.sleep(0.5)

                # Stop
                await client.cmd_dc_set_speed(motor_id, 0)

                results.append(TestResult(f"Motor {motor_id}", True, "Forward/Reverse OK"))

            except Exception as e:
                results.append(TestResult(f"Motor {motor_id}", False, str(e)))
                await client.cmd_dc_set_speed(motor_id, 0)

    finally:
        await client.cmd_disarm()
        await client.stop()

    _print_results(results)
    return 0 if all(r.passed for r in results) else 1


def cmd_encoders(args: argparse.Namespace) -> int:
    """Test encoders."""
    console.print()
    console.print("[bold cyan]Encoder Test[/bold cyan]")
    console.print()
    print_info("Rotate the wheels manually to verify encoder readings")

    return asyncio.run(_test_encoders(args))


async def _test_encoders(args: argparse.Namespace) -> int:
    """Run encoder test."""
    from robot_host.command.client import AsyncRobotClient

    if getattr(args, 'tcp', None):
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)

    client = AsyncRobotClient(transport)
    encoder_data = {}

    def on_telemetry(data):
        if isinstance(data, dict) and "encoders" in data:
            for enc in data["encoders"]:
                enc_id = enc.get("id", 0)
                encoder_data[enc_id] = enc.get("counts", 0)

    client.bus.subscribe("telemetry", on_telemetry)

    try:
        await client.start()
        print_success("Connected - monitoring encoders")
        console.print()
        console.print("[dim]Rotate wheels to see encoder counts change[/dim]")
        console.print("[dim]Press Ctrl+C when done[/dim]")
        console.print()

        while True:
            if encoder_data:
                line = "  Encoders: " + " | ".join(
                    f"[{eid}]={cnt}" for eid, cnt in sorted(encoder_data.items())
                )
                console.print(line, end="\r")
            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        console.print()

    finally:
        await client.stop()

    if encoder_data:
        print_success(f"Detected {len(encoder_data)} encoder(s)")
    else:
        print_warning("No encoder data received")

    return 0


def cmd_servos(args: argparse.Namespace) -> int:
    """Test servos."""
    servo_ids = [int(x.strip()) for x in args.ids.split(",")]

    console.print()
    console.print("[bold cyan]Servo Test[/bold cyan]")
    console.print(f"  Servos: {servo_ids}")
    console.print()

    return asyncio.run(_test_servos(args, servo_ids))


async def _test_servos(args: argparse.Namespace, servo_ids: list[int]) -> int:
    """Run servo test."""
    from robot_host.command.client import AsyncRobotClient

    if getattr(args, 'tcp', None):
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)

    client = AsyncRobotClient(transport)
    results = []

    try:
        await client.start()
        await client.cmd_arm()

        for servo_id in servo_ids:
            console.print(f"  Testing servo {servo_id}...")

            try:
                # Center
                await client.cmd_servo_set_angle(servo_id, 90, 500)
                await asyncio.sleep(0.6)

                # Min
                await client.cmd_servo_set_angle(servo_id, 0, 500)
                await asyncio.sleep(0.6)

                # Max
                await client.cmd_servo_set_angle(servo_id, 180, 500)
                await asyncio.sleep(0.6)

                # Center
                await client.cmd_servo_set_angle(servo_id, 90, 500)

                results.append(TestResult(f"Servo {servo_id}", True, "Sweep 0-90-180-90 OK"))

            except Exception as e:
                results.append(TestResult(f"Servo {servo_id}", False, str(e)))

    finally:
        await client.cmd_disarm()
        await client.stop()

    _print_results(results)
    return 0 if all(r.passed for r in results) else 1


def cmd_sensors(args: argparse.Namespace) -> int:
    """Test sensors."""
    console.print()
    console.print("[bold cyan]Sensor Test[/bold cyan]")
    console.print()

    return asyncio.run(_test_sensors(args))


async def _test_sensors(args: argparse.Namespace) -> int:
    """Run sensor test."""
    from robot_host.command.client import AsyncRobotClient

    if getattr(args, 'tcp', None):
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)

    client = AsyncRobotClient(transport)

    imu_data = {}
    ultrasonic_data = {}

    def on_telemetry(data):
        if isinstance(data, dict):
            if "imu" in data:
                imu_data.update(data["imu"])
            if "ultrasonic" in data:
                for us in data["ultrasonic"]:
                    ultrasonic_data[us.get("id", 0)] = us.get("distance_m", 0)

    client.bus.subscribe("telemetry", on_telemetry)

    try:
        await client.start()
        print_success("Connected - reading sensors")
        console.print()

        # Wait for data
        await asyncio.sleep(2)

        results = []

        # Check IMU
        if imu_data:
            ax = imu_data.get("ax", 0)
            ay = imu_data.get("ay", 0)
            az = imu_data.get("az", 0)
            results.append(TestResult("IMU Accelerometer", True, f"ax={ax:.2f} ay={ay:.2f} az={az:.2f}"))
        else:
            results.append(TestResult("IMU Accelerometer", False, "No data received"))

        # Check ultrasonic
        if ultrasonic_data:
            for us_id, dist in ultrasonic_data.items():
                results.append(TestResult(f"Ultrasonic {us_id}", True, f"Distance: {dist:.2f}m"))
        else:
            results.append(TestResult("Ultrasonic", False, "No data received"))

        _print_results(results)

    finally:
        await client.stop()

    return 0


def cmd_gpio(args: argparse.Namespace) -> int:
    """Test GPIO."""
    console.print()
    console.print("[bold cyan]GPIO Test[/bold cyan]")
    console.print()
    print_info("Testing LED GPIO (channel 0)")

    return asyncio.run(_test_gpio(args))


async def _test_gpio(args: argparse.Namespace) -> int:
    """Run GPIO test."""
    from robot_host.command.client import AsyncRobotClient

    if getattr(args, 'tcp', None):
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)

    client = AsyncRobotClient(transport)

    try:
        await client.start()

        console.print("  Blinking LED 3 times...")
        for _ in range(3):
            await client.cmd_led_on()
            await asyncio.sleep(0.2)
            await client.cmd_led_off()
            await asyncio.sleep(0.2)

        print_success("GPIO test complete")

    finally:
        await client.stop()

    return 0
