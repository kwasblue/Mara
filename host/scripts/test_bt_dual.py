#!/usr/bin/env python3
"""
Dual-port Bluetooth diagnostic.

Opens both USB serial (for debug output) and Bluetooth serial simultaneously
to see what the ESP32 reports about Bluetooth connections.
"""

import sys
import time
import threading
import serial
from serial.tools import list_ports

# Protocol constants
FRAME_START = 0x02
FRAME_END = 0x03
MSG_PING = 0x01
MSG_VERSION_REQUEST = 0x10


def find_ports():
    """Find USB and Bluetooth ports."""
    usb_port = None
    bt_port = None

    for port in list_ports.comports():
        dev = port.device.lower()
        desc = (port.description or "").lower()

        # Bluetooth SPP
        if "esp32-spp" in dev or "esp32-spp" in desc:
            bt_port = port.device
        # USB serial (on macOS, usually cu.usbserial or cu.wchusbserial)
        elif "usbserial" in dev or "wchusbserial" in dev or "ttyUSB" in dev:
            usb_port = port.device

    return usb_port, bt_port


def encode_frame(msg_type: int, payload: bytes = b"") -> bytes:
    """Encode a protocol frame."""
    length = len(payload) + 1
    return bytes([FRAME_START, length, msg_type]) + payload + bytes([FRAME_END])


def usb_monitor(ser: serial.Serial, stop_event: threading.Event):
    """Monitor USB serial for debug output."""
    print("[USB] Monitoring for debug output...")
    while not stop_event.is_set():
        try:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                # Try to decode as text (debug output is ASCII)
                try:
                    text = data.decode('utf-8', errors='replace')
                    for line in text.split('\n'):
                        if line.strip():
                            print(f"[USB] {line.strip()}")
                except:
                    print(f"[USB] raw: {data.hex()}")
        except Exception as e:
            print(f"[USB] Error: {e}")
            break
        time.sleep(0.01)


def main():
    usb_port, bt_port = find_ports()

    print("=== Dual Port Bluetooth Diagnostic ===")
    print(f"USB port:       {usb_port or 'NOT FOUND'}")
    print(f"Bluetooth port: {bt_port or 'NOT FOUND'}")
    print()

    if not bt_port:
        print("ERROR: No Bluetooth port found!")
        print("\nAvailable ports:")
        for port in list_ports.comports():
            print(f"  {port.device}: {port.description}")
        sys.exit(1)

    # Open USB port for monitoring (if available)
    usb_ser = None
    usb_thread = None
    stop_event = threading.Event()

    if usb_port:
        try:
            usb_ser = serial.Serial(usb_port, 921600, timeout=0.1)
            print(f"[USB] Opened {usb_port}")
            usb_thread = threading.Thread(target=usb_monitor, args=(usb_ser, stop_event))
            usb_thread.start()
            time.sleep(0.5)  # Let it start
        except Exception as e:
            print(f"[USB] Could not open: {e}")
            usb_ser = None

    # Now try Bluetooth
    print(f"\n[BT] Opening {bt_port} at 921600 baud...")
    try:
        bt_ser = serial.Serial(bt_port, 921600, timeout=3.0, write_timeout=3.0)
        print(f"[BT] Port opened successfully")
    except Exception as e:
        print(f"[BT] ERROR: {e}")
        stop_event.set()
        if usb_thread:
            usb_thread.join(timeout=1.0)
        if usb_ser:
            usb_ser.close()
        sys.exit(1)

    time.sleep(1.0)  # Give time for Bluetooth to establish

    # Clear buffers
    bt_ser.reset_input_buffer()
    bt_ser.reset_output_buffer()

    # Test 1: PING
    print("\n[BT] Sending PING...")
    ping_frame = encode_frame(MSG_PING)
    print(f"[BT] TX: {ping_frame.hex()}")
    bt_ser.write(ping_frame)
    bt_ser.flush()

    time.sleep(2.0)

    if bt_ser.in_waiting:
        resp = bt_ser.read(bt_ser.in_waiting)
        print(f"[BT] RX: {resp.hex()}")
    else:
        print("[BT] No response")

    # Test 2: VERSION_REQUEST
    print("\n[BT] Sending VERSION_REQUEST...")
    ver_frame = encode_frame(MSG_VERSION_REQUEST)
    print(f"[BT] TX: {ver_frame.hex()}")
    bt_ser.write(ver_frame)
    bt_ser.flush()

    time.sleep(2.0)

    if bt_ser.in_waiting:
        resp = bt_ser.read(bt_ser.in_waiting)
        print(f"[BT] RX: {resp.hex()}")
    else:
        print("[BT] No response")

    # Give USB monitor some time to show any output
    print("\n[BT] Waiting 3 more seconds for debug output...")
    time.sleep(3.0)

    # Cleanup
    print("\nCleaning up...")
    stop_event.set()
    bt_ser.close()
    if usb_thread:
        usb_thread.join(timeout=1.0)
    if usb_ser:
        usb_ser.close()

    print("Done")


if __name__ == "__main__":
    main()
