#!/usr/bin/env python3
"""
Monitor USB serial while attempting Bluetooth pairing.
Shows ESP32 Bluetooth events during pairing process.
"""

import sys
import time
import subprocess
import threading
import serial
from serial.tools import list_ports


def find_usb_port() -> str | None:
    for port in list_ports.comports():
        dev = port.device.lower()
        if "usbserial" in dev or "wchusbserial" in dev:
            return port.device
    return None


def monitor_usb(ser: serial.Serial, stop_event: threading.Event):
    """Monitor USB serial for debug output."""
    print("[USB] Monitoring...")
    while not stop_event.is_set():
        try:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                text = data.decode('utf-8', errors='replace')
                for line in text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    # Filter out garbled boot messages
                    if all(c in '�.' for c in line):
                        continue
                    # Highlight BT-related messages
                    if any(kw in line.lower() for kw in ['bt', 'ble', 'bluetooth', 'spp', 'gap', 'pair', 'connect']):
                        print(f"[USB] >>> {line}")
                    elif '[' in line:
                        print(f"[USB]     {line}")
        except:
            pass
        time.sleep(0.01)


def main():
    usb_port = find_usb_port()
    if not usb_port:
        print("ERROR: No USB serial port found")
        sys.exit(1)

    print(f"Opening USB port: {usb_port}")
    ser = serial.Serial(usb_port, 921600, timeout=0.1)

    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_usb, args=(ser, stop_event))
    monitor_thread.start()

    print("\nLet the ESP32 boot and stabilize for 5 seconds...")
    time.sleep(5)

    # Get current Bluetooth state
    print("\n=== Current Bluetooth State ===")
    result = subprocess.run(['blueutil', '--inquiry', '3'], capture_output=True, text=True, timeout=10)
    for line in result.stdout.strip().split('\n'):
        if 'esp' in line.lower():
            print(f"Found: {line}")

    # Try to connect
    print("\n=== Attempting Bluetooth Connect ===")
    result = subprocess.run(
        ['blueutil', '--connect', '08-b6-1f-b9-50-2a'],
        capture_output=True,
        text=True,
        timeout=15
    )
    print(f"Connect result: {result.returncode}")
    if result.stdout:
        print(f"stdout: {result.stdout}")
    if result.stderr:
        print(f"stderr: {result.stderr}")

    # Wait to see any events
    print("\n=== Waiting 5 seconds for ESP32 events ===")
    time.sleep(5)

    # Check connection status
    print("\n=== Check Connection Status ===")
    result = subprocess.run(['blueutil', '--is-connected', '08-b6-1f-b9-50-2a'], capture_output=True, text=True)
    print(f"Is connected: {result.stdout.strip()}")

    # Cleanup
    stop_event.set()
    monitor_thread.join(timeout=1)
    ser.close()
    print("\nDone")


if __name__ == "__main__":
    main()
