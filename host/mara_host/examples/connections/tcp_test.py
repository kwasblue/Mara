# mara_host/runners/test_tcp.py
"""
Simple TCP test - sends a heartbeat command and prints response.

Usage:
    python -m mara_host.runners.test_tcp
    python -m mara_host.runners.test_tcp --host 192.168.4.1 --port 3333
"""

import argparse
import json
import socket


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple TCP test")
    parser.add_argument("--host", default="10.0.0.60", help="MCU host IP")
    parser.add_argument("--port", type=int, default=3333, help="MCU port")
    parser.add_argument("--timeout", type=float, default=5.0, help="Socket timeout")
    args = parser.parse_args()

    # Connect to MCU
    print(f"[TCP-TEST] Connecting to {args.host}:{args.port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(args.timeout)

    try:
        sock.connect((args.host, args.port))
        print("[TCP-TEST] Connected")

        # Send a heartbeat command
        cmd = json.dumps({"kind": "cmd", "type": "CMD_HEARTBEAT", "seq": 1})
        payload = cmd.encode('utf-8')

        # Frame it
        HEADER = 0xAA
        MSG_CMD_JSON = 0x50
        length = 1 + len(payload)
        len_hi = (length >> 8) & 0xFF
        len_lo = length & 0xFF
        checksum = (length + MSG_CMD_JSON + sum(payload)) & 0xFF

        frame = bytes([HEADER, len_hi, len_lo, MSG_CMD_JSON]) + payload + bytes([checksum])
        print(f"[TCP-TEST] Sending: {frame.hex()}")
        sock.send(frame)

        # Receive response
        response = sock.recv(1024)
        print(f"[TCP-TEST] Received: {response.hex()}")
        print(f"[TCP-TEST] Decoded: {response}")

    except socket.timeout:
        print("[TCP-TEST] Timeout waiting for response")
    except ConnectionRefusedError:
        print(f"[TCP-TEST] Connection refused to {args.host}:{args.port}")
    except OSError as e:
        print(f"[TCP-TEST] Connection error: {e}")
    finally:
        sock.close()
        print("[TCP-TEST] Socket closed")


if __name__ == "__main__":
    main()
