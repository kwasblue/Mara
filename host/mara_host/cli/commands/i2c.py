# mara_host/cli/commands/i2c.py
"""I2C bus commands."""

import argparse

from rich.table import Table

from mara_host.cli.console import (
    console,
    print_error,
    print_info,
)
from mara_host.cli.context import CLIContext, run_with_context
from mara_host.cli.commands._common import add_port_arg, cmd_help


# Common I2C device addresses for reference
KNOWN_DEVICES = {
    0x1E: "HMC5883L (Compass)",
    0x20: "PCF8574 (GPIO Expander)",
    0x27: "LCD (PCF8574)",
    0x3C: "SSD1306 (OLED)",
    0x3D: "SSD1306 (OLED Alt)",
    0x40: "INA219 (Current Sensor)",
    0x48: "ADS1115 (ADC)",
    0x50: "AT24C32 (EEPROM)",
    0x53: "ADXL345 (Accelerometer)",
    0x57: "MAX30102 (Pulse Oximeter)",
    0x68: "MPU6050/DS3231 (IMU/RTC)",
    0x69: "MPU6050 Alt (IMU)",
    0x76: "BME280/BMP280 (Env Sensor)",
    0x77: "BME280/BMP280 Alt",
}


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register i2c command group."""
    i2c_parser = subparsers.add_parser(
        "i2c",
        help="I2C bus operations",
        description="Scan and interact with I2C devices on the MCU",
    )

    i2c_sub = i2c_parser.add_subparsers(
        dest="i2c_cmd",
        title="i2c commands",
        metavar="<subcommand>",
    )

    # i2c scan
    scan_p = i2c_sub.add_parser("scan", help="Scan I2C bus for devices")
    scan_p.add_argument(
        "--bus",
        type=int,
        default=0,
        help="I2C bus number (default: 0)",
    )
    add_port_arg(scan_p)
    scan_p.set_defaults(func=cmd_scan)

    # i2c detect
    detect_p = i2c_sub.add_parser(
        "detect", help="Detect and identify known I2C devices"
    )
    add_port_arg(detect_p)
    detect_p.set_defaults(func=cmd_detect)

    # Default handler
    i2c_parser.set_defaults(func=lambda args: cmd_help(i2c_parser))


@run_with_context
async def cmd_scan(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Scan I2C bus for responding devices."""
    print_info("Scanning I2C bus...")

    result = await ctx.i2c_service.scan()

    if result.ok:
        data = result.data or {}
        addresses = data.get("addresses", [])

        if not addresses:
            console.print("No I2C devices found")
            return 0

        # Display as grid (like i2cdetect)
        console.print(f"\nFound {len(addresses)} device(s):\n")

        # Header
        header = "     "
        for i in range(16):
            header += f"{i:02x} "
        console.print(header)

        # Grid
        for row in range(8):
            line = f"{row * 16:02x}: "
            for col in range(16):
                addr = row * 16 + col
                if addr in addresses:
                    line += f"[green]{addr:02x}[/green] "
                elif addr < 0x03 or addr > 0x77:
                    line += "   "  # Reserved addresses
                else:
                    line += "-- "
            console.print(line)

        # Show identified devices
        console.print()
        for addr in addresses:
            name = KNOWN_DEVICES.get(addr, "Unknown device")
            console.print(f"  0x{addr:02X}: {name}")

        return 0
    else:
        print_error(f"Scan failed: {result.error}")
        return 1


@run_with_context
async def cmd_detect(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Scan and identify known I2C devices."""
    print_info("Detecting I2C devices...")

    result = await ctx.i2c_service.scan()

    if result.ok:
        data = result.data or {}
        addresses = data.get("addresses", [])

        if not addresses:
            console.print("No I2C devices found")
            return 0

        table = Table(title="Detected I2C Devices")
        table.add_column("Address", style="cyan", justify="center")
        table.add_column("Device", style="green")

        for addr in sorted(addresses):
            name = KNOWN_DEVICES.get(addr, "[dim]Unknown[/dim]")
            table.add_row(f"0x{addr:02X}", name)

        console.print(table)
        return 0
    else:
        print_error(f"Detection failed: {result.error}")
        return 1
