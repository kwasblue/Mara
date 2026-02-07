#!/usr/bin/env python3
"""
Example 01: Serial Connection

Demonstrates:
- Finding available serial ports
- Connecting to ESP32 via USB serial
- Performing version handshake
- Basic lifecycle (start/stop)

Prerequisites:
- ESP32 with robot_host firmware connected via USB
- pyserial installed: pip install pyserial

Usage:
    python 01_serial_connection.py
    python 01_serial_connection.py /dev/ttyUSB0  # specify port
"""
import asyncio
import sys

from robot_host import Robot


def find_serial_ports():
    """List available serial ports."""
    import serial.tools.list_ports

    ports = serial.tools.list_ports.comports()
    usb_ports = []

    print("Available serial ports:")
    for port in ports:
        # Filter for likely ESP32 ports
        is_esp32 = any(x in port.description.lower() for x in ["usb", "uart", "serial", "cp210", "ch340", "ftdi"])
        marker = " <-- likely ESP32" if is_esp32 else ""
        print(f"  {port.device}: {port.description}{marker}")
        if is_esp32:
            usb_ports.append(port.device)

    return usb_ports


async def main():
    # Find or use specified port
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        ports = find_serial_ports()
        if not ports:
            print("\nNo USB serial ports found. Connect ESP32 and try again.")
            return
        port = ports[0]
        print(f"\nUsing first detected port: {port}")

    print(f"\n{'='*50}")
    print(f"Connecting to ESP32 on {port}")
    print(f"{'='*50}")

    # Connect using Robot class - the canonical entry point
    async with Robot(port=port, baudrate=115200) as robot:
        # Display connection info
        print(f"\nConnection established!")
        print(f"  Robot name: {robot.name}")
        print(f"  Board: {robot.board}")
        print(f"  Firmware version: {robot.firmware_version}")
        print(f"  Protocol version: {robot.protocol_version}")
        print(f"  Connected: {robot.is_connected}")

        # Keep running for a few seconds to see heartbeats
        print("\nMonitoring connection for 5 seconds...")
        for i in range(5):
            await asyncio.sleep(1)
            print(f"  [{i+1}s] Connected: {robot.is_connected}")

        print("\nConnection test successful!")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
