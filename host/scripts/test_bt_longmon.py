#!/usr/bin/env python3
"""
Long-running USB serial monitor to catch boot messages.
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
        sys.exit(1)

    print(f"Opening USB port: {usb_port}")

    try:
        ser = serial.Serial(usb_port, 921600, timeout=0.1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print("Monitoring for 30 seconds (to catch boot + crash cycles)...")
    print("=" * 70)

    start = time.time()
    while time.time() - start < 30:
        if ser.in_waiting:
            try:
                data = ser.read(ser.in_waiting)
                text = data.decode('utf-8', errors='replace')
                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    # Filter out garbled boot loader messages
                    if all(c in '�.' for c in line):
                        continue
                    # Highlight important messages
                    if 'ble' in line.lower() or 'bluetooth' in line.lower():
                        print(f">>> {line}")
                    elif 'abort' in line.lower() or 'crash' in line.lower() or 'backtrace' in line.lower():
                        print(f"!!! {line}")
                    elif 'boot' in line.lower() or 'mcu' in line.lower():
                        print(f"--- {line}")
                    elif '[' in line:
                        print(f"    {line}")
            except:
                pass
        time.sleep(0.01)

    print("=" * 70)
    ser.close()
    print("Done")


if __name__ == "__main__":
    main()
