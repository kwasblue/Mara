# mara_host/cli/commands/test/_registry.py
"""Registry for test commands."""

import argparse
from pathlib import Path

from .all import cmd_all
from .connection import cmd_connection
from .motors import cmd_motors
from .encoders import cmd_encoders
from .servos import cmd_servos
from .sensors import cmd_sensors
from .gpio import cmd_gpio
from .latency import cmd_latency
from .stepper import cmd_stepper
from .commands import cmd_commands, DEFAULT_PAYLOADS
from mara_host.cli.cli_config import get_serial_port as _get_port


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
        p.add_argument("-p", "--port", default=_get_port())
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

    # latency
    latency_p = test_sub.add_parser(
        "latency",
        help="Measure ping/pong round-trip latency",
    )
    add_transport_args(latency_p)
    latency_p.add_argument("-n", "--count", type=int, default=30, help="Number of pings (default: 30)")
    latency_p.add_argument("--delay", type=float, default=0.2, help="Delay between pings in seconds (default: 0.2)")
    latency_p.set_defaults(func=cmd_latency)

    # stepper
    stepper_p = test_sub.add_parser(
        "stepper",
        help="Test stepper motors",
    )
    add_transport_args(stepper_p)
    stepper_p.add_argument("--ids", default="0", help="Stepper motor IDs to test (comma-separated)")
    stepper_p.add_argument("--steps", type=int, default=200, help="Steps per move (default: 200)")
    stepper_p.add_argument("--speed", type=float, default=1.0, help="Speed in rev/s (default: 1.0)")
    stepper_p.add_argument("--cycles", type=int, default=3, help="Forward/reverse cycles (default: 3)")
    stepper_p.set_defaults(func=cmd_stepper)

    # commands
    commands_p = test_sub.add_parser(
        "commands",
        help="Test all MCU commands and verify ACKs",
    )
    add_transport_args(commands_p)
    commands_p.add_argument(
        "--category",
        choices=["all", "safety", "gpio", "motor", "servo", "control", "telemetry", "camera", "encoder", "stepper", "dc", "observer"],
        default="all",
        help="Command category to test (default: all)",
    )
    commands_p.add_argument("--timeout", type=float, default=2.0, help="Command timeout in seconds (default: 2.0)")
    commands_p.add_argument(
        "--payloads",
        type=Path,
        default=None,
        help=f"JSON file with command payloads (default: {DEFAULT_PAYLOADS.name})",
    )
    commands_p.add_argument(
        "--skip-motion",
        action="store_true",
        default=True,
        help="Skip motion commands (default: true)",
    )
    commands_p.add_argument(
        "--unsafe-motion",
        action="store_true",
        help="Allow motion commands to be tested",
    )
    commands_p.add_argument(
        "--delay-ms",
        type=int,
        default=50,
        help="Delay between commands in ms (default: 50)",
    )
    commands_p.set_defaults(func=cmd_commands)

    # Default
    test_parser.set_defaults(func=cmd_all)
