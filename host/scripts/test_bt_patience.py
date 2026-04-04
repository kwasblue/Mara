#!/usr/bin/env python3
"""
Bluetooth test with longer wait times and connection status checking.

On macOS, Bluetooth SPP serial ports sometimes need time to establish
the actual RFCOMM connection after opening.
"""

import sys
import time
import serial
from serial.tools import list_ports

FRAME_START = 0x02
FRAME_END = 0x03
MSG_PING = 0x01
MSG_VERSION_REQUEST = 0x10


def find_bluetooth_port(device_name: str = "ESP32-SPP") -> str | None:
    target = device_name.lower()
    for port in list_ports.comports():
        desc = (port.description or "").lower()
        name = (port.name or "").lower()
        dev = (port.device or "").lower()
        if target in desc or target in name or target in dev:
            if port.device.startswith("/dev/cu."):
                return port.device
    return None


def encode_frame(msg_type: int, payload: bytes = b"") -> bytes:
    length = len(payload) + 1
    return bytes([FRAME_START, length, msg_type]) + payload + bytes([FRAME_END])


def main():
    bt_port = find_bluetooth_port("ESP32-SPP")
    if not bt_port:
        print("ERROR: No Bluetooth port found")
        sys.exit(1)

    print(f"Found Bluetooth port: {bt_port}")
    print("Opening port (this may take a few seconds for RFCOMM connection)...")

    try:
        # Open with longer timeout
        ser = serial.Serial(
            port=bt_port,
            baudrate=921600,
            timeout=10.0,
            write_timeout=10.0,
        )
        print(f"Port opened: {ser.name}")
    except Exception as e:
        print(f"ERROR opening port: {e}")
        sys.exit(1)

    # Wait for RFCOMM connection to establish
    print("Waiting 5 seconds for Bluetooth connection to establish...")
    for i in range(5):
        time.sleep(1)
        print(f"  {i+1}...")
        # Check if any data arrived (heartbeat maybe?)
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            print(f"  Received {len(data)} bytes: {data[:20].hex()}...")

    # Clear buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Test multiple times with delays
    for attempt in range(3):
        print(f"\n--- Attempt {attempt + 1} ---")

        # Send PING
        ping_frame = encode_frame(MSG_PING)
        print(f"Sending PING: {ping_frame.hex()}")
        ser.write(ping_frame)
        ser.flush()

        # Wait for response with polling
        print("Waiting for response (5 seconds)...")
        start = time.time()
        while time.time() - start < 5.0:
            if ser.in_waiting:
                resp = ser.read(ser.in_waiting)
                print(f"✓ Response: {resp.hex()}")
                break
            time.sleep(0.1)
        else:
            print("✗ No response")

        time.sleep(1)

    # Try VERSION_REQUEST
    print("\n--- VERSION_REQUEST ---")
    ver_frame = encode_frame(MSG_VERSION_REQUEST)
    print(f"Sending: {ver_frame.hex()}")
    ser.write(ver_frame)
    ser.flush()

    print("Waiting 10 seconds for response...")
    start = time.time()
    all_data = b""
    while time.time() - start < 10.0:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            all_data += data
            print(f"  Received {len(data)} bytes: {data[:50].hex()}")
        time.sleep(0.1)

    if not all_data:
        print("No response received")

    ser.close()
    print("\nPort closed")


if __name__ == "__main__":
    main()
