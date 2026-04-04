#!/usr/bin/env python3
"""
Raw Bluetooth serial diagnostic test.

Tests basic serial communication over Bluetooth SPP without the full MaraClient.
This helps isolate whether the issue is with:
1. Bluetooth connection itself
2. Protocol framing
3. MaraClient handshake logic
"""

import sys
import time
import serial
from serial.tools import list_ports

# Protocol constants (from Protocol.h)
FRAME_START = 0x02
FRAME_END = 0x03
MSG_PING = 0x01
MSG_PONG = 0x02
MSG_VERSION_REQUEST = 0x10
MSG_VERSION_RESPONSE = 0x11


def find_bluetooth_port(device_name: str = "ESP32-SPP") -> str | None:
    """Find Bluetooth SPP serial port."""
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
    """Encode a protocol frame."""
    length = len(payload) + 1  # +1 for msg_type
    frame = bytes([FRAME_START, length, msg_type]) + payload + bytes([FRAME_END])
    return frame


def main():
    # Find Bluetooth port
    bt_port = find_bluetooth_port("ESP32-SPP")
    if not bt_port:
        print("ERROR: No Bluetooth port found")
        print("\nAvailable ports:")
        for port in list_ports.comports():
            print(f"  {port.device}: {port.description}")
        sys.exit(1)

    print(f"Found Bluetooth port: {bt_port}")

    # Open serial port
    try:
        print(f"Opening port at 921600 baud...")
        ser = serial.Serial(
            port=bt_port,
            baudrate=921600,
            timeout=5.0,
            write_timeout=5.0,
        )
        print(f"Port opened: {ser.name}")
    except Exception as e:
        print(f"ERROR opening port: {e}")
        sys.exit(1)

    # Clear any buffered data
    time.sleep(0.5)
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Test 1: Send PING
    print("\n--- Test 1: PING ---")
    ping_frame = encode_frame(MSG_PING)
    print(f"Sending PING: {ping_frame.hex()}")
    ser.write(ping_frame)
    ser.flush()

    time.sleep(1.0)
    response = ser.read(ser.in_waiting or 1)
    if response:
        print(f"Response: {response.hex()}")
        if MSG_PONG in response:
            print("✓ Got PONG!")
    else:
        print("✗ No response to PING")

    # Test 2: Send VERSION_REQUEST
    print("\n--- Test 2: VERSION_REQUEST ---")
    version_frame = encode_frame(MSG_VERSION_REQUEST)
    print(f"Sending VERSION_REQUEST: {version_frame.hex()}")
    ser.write(version_frame)
    ser.flush()

    time.sleep(2.0)
    response = ser.read(ser.in_waiting or 1)
    if response:
        print(f"Response ({len(response)} bytes): {response[:50].hex()}...")
        if MSG_VERSION_RESPONSE in response:
            print("✓ Got VERSION_RESPONSE!")
            # Try to extract JSON
            try:
                start_idx = response.index(MSG_VERSION_RESPONSE) + 1
                end_idx = response.index(FRAME_END, start_idx)
                json_data = response[start_idx:end_idx]
                print(f"JSON: {json_data.decode('utf-8', errors='replace')}")
            except:
                pass
    else:
        print("✗ No response to VERSION_REQUEST")

    # Test 3: Send raw bytes and listen
    print("\n--- Test 3: Raw listen (5 seconds) ---")
    print("Listening for any incoming data...")
    start = time.time()
    all_data = b""
    while time.time() - start < 5.0:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            all_data += data
            print(f"  Received: {data.hex()}")
        time.sleep(0.1)

    if not all_data:
        print("No data received during listen period")

    print("\n--- Summary ---")
    print(f"Port: {bt_port}")
    print(f"Baud: 921600")
    print(f"Total bytes received: {len(all_data)}")

    ser.close()
    print("Port closed")


if __name__ == "__main__":
    main()
