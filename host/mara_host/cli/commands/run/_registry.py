# mara_host/cli/commands/run/_registry.py
"""Registry for run commands."""

import argparse

from ._common import add_logging_args, show_transports
from .serial import cmd_serial
from .ble import cmd_ble
from .tcp import cmd_tcp
from .can import cmd_can
from .mqtt import cmd_mqtt
from .shell import cmd_shell
from mara_host.cli.cli_config import get_serial_port as _get_port
from mara_host.core._generated_config import DEFAULT_BAUD_RATE as DEFAULT_BAUDRATE


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
        default=_get_port(),
        help="Serial port (default: %(default)s)",
    )
    serial_p.add_argument(
        "-b", "--baudrate",
        type=int,
        default=DEFAULT_BAUDRATE,
        help="Baud rate (default: %(default)s)",
    )
    serial_p.add_argument(
        "--shell",
        action="store_true",
        help="Launch interactive shell",
    )
    add_logging_args(serial_p)
    serial_p.set_defaults(func=cmd_serial)

    # ble
    ble_p = run_sub.add_parser(
        "ble",
        help="Connect via Bluetooth Classic SPP",
    )
    ble_p.add_argument(
        "--ble-name",
        default="ESP32-SPP",
        help="Bluetooth SPP device name to auto-discover (default: %(default)s)",
    )
    ble_p.add_argument(
        "-b", "--baudrate",
        type=int,
        default=DEFAULT_BAUDRATE,
        help="Baud rate hint (default: 921600)",
    )
    ble_p.add_argument(
        "--shell",
        action="store_true",
        help="Launch interactive shell",
    )
    add_logging_args(ble_p)
    ble_p.set_defaults(func=cmd_ble)

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
    add_logging_args(tcp_p)
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
    add_logging_args(can_p)
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
    add_logging_args(mqtt_p)
    mqtt_p.set_defaults(func=cmd_mqtt)

    # shell (interactive mode for any transport)
    shell_p = run_sub.add_parser(
        "shell",
        help="Interactive command shell",
    )
    shell_p.add_argument(
        "-t", "--transport",
        choices=["serial", "ble", "tcp"],
        default="serial",
        help="Transport type (default: serial)",
    )
    shell_p.add_argument(
        "-p", "--port",
        default=_get_port(),
        help="Serial port (for serial transport)",
    )
    shell_p.add_argument(
        "-b", "--baudrate",
        type=int,
        default=DEFAULT_BAUDRATE,
        help="Baud rate for serial/BLE transport (default: 921600)",
    )
    shell_p.add_argument(
        "--ble-name",
        default="ESP32-SPP",
        help="Bluetooth SPP device name (for BLE transport)",
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
    add_logging_args(shell_p)
    shell_p.set_defaults(func=cmd_shell)

    # Default handler
    run_parser.set_defaults(func=lambda args: show_transports())
