#!/usr/bin/env python3
"""
Monitor USB serial for Bluetooth-related messages.
"""

import sys
import time
import serial
from serial.tools import list_ports


def find_usb_port() -> str | None:
    """Find USB serial port."""
    for port in list_ports.comports():
        dev = port.device.lower()
        if "usbserial" in dev or "wchusbserial" in dev or "ttyUSB" in dev:
            return port.device
    return None


def main():
    usb_port = find_usb_port()
    if not usb_port:
        print("ERROR: No USB serial port found")
        print("\nAvailable ports:")
        for port in list_ports.comports():
            print(f"  {port.device}: {port.description}")
        sys.exit(1)

    print(f"Opening USB port: {usb_port}")

    try:
        ser = serial.Serial(usb_port, 921600, timeout=0.5)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print("Monitoring for 10 seconds...")
    print("-" * 60)

    start = time.time()
    while time.time() - start < 10:
        if ser.in_waiting:
            try:
                data = ser.read(ser.in_waiting)
                text = data.decode('utf-8', errors='replace')
                for line in text.split('\n'):
                    if line.strip():
                        # Highlight BLE/Bluetooth related lines
                        if 'ble' in line.lower() or 'bluetooth' in line.lower() or 'bt' in line.lower():
                            print(f">>> {line.strip()}")
                        else:
                            print(f"    {line.strip()}")
            except:
                pass
        time.sleep(0.01)

    print("-" * 60)
    ser.close()
    print("Done")


if __name__ == "__main__":
    main()
