# robot_host/runners/interactive_shell.py

import asyncio
from typing import Callable

from robot_host.command.client import AsyncRobotClient
from robot_host.transport.serial_transport import SerialTransport
# from robot_host.transport.tcp_transport import AsyncTcpTransport  # not needed right now


async def ainput(prompt: str = "") -> str:
    """
    Async-friendly input() so Ctrl-C is handled correctly.
    """
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, lambda: input(prompt))
    except KeyboardInterrupt:
        raise


def _print_event(tag: str) -> Callable[[dict], None]:
    def _handler(data: dict) -> None:
        print(f"[{tag}] {data}")
    return _handler


async def main() -> None:
    # ---- Serial config (Mac) ----
    # Adjust this if your device name is different.
    # You can check with:  ls /dev/cu.*
    serial_dev = "/dev/cu.usbserial-0001" # direct serial connection
    ble_serial = "/dev/cu.ESP32-SPP"     # bluetooth connection
    baudrate = 115200

    serial_choice = ble_serial
    print(f"[Shell] Using SERIAL transport on {serial_choice} @ {baudrate} baud")
    transport = SerialTransport(serial_choice, baudrate=baudrate) # default as bluetooth for now 

    client = AsyncRobotClient(transport=transport)

    # Subscribe to events
    client.bus.subscribe("heartbeat", _print_event("HEARTBEAT"))
    client.bus.subscribe("pong",      _print_event("PONG"))
    client.bus.subscribe("hello",     _print_event("HELLO"))
    client.bus.subscribe("json",      _print_event("JSON"))
    client.bus.subscribe("raw_frame", _print_event("RAW"))

    await client.start()

    print("")
    print("=== Robot Interactive Shell (Serial) ===")
    print("Available commands:")
    print("  ping                 - send ping")
    print("  whoami               - ask robot identity")
    print("  led on               - turn LED on")
    print("  led off              - turn LED off")
    print("  mode <name>          - set mode (IDLE/ARMED/ACTIVE/CALIB)")
    print("  servo attach         - attach servo on channel 0")
    print("  servo angle <deg>    - move servo 0 to angle")
    print("  servo sweep a b      - sweep servo 0 from a→b smoothly")
    print("  q / quit / exit      - quit")
    print("")

    try:
        while True:
            try:
                line = (await ainput("robot> ")).strip()
            except KeyboardInterrupt:
                print("\n[Shell] KeyboardInterrupt — exiting...")
                break

            if not line:
                continue

            lower = line.lower()

            # --- Shell control ---
            if lower in ("quit", "exit", "q"):
                print("[Shell] Exiting...")
                break

            # --- Basic commands ---
            elif lower == "ping":
                await client.send_ping()

            elif lower == "whoami":
                await client.send_whoami()

            elif lower == "led on":
                await client.send_led_on()

            elif lower == "led off":
                await client.send_led_off()

            # --- Servo commands ---
            elif lower == "servo attach":
                await client.send_servo_attach(servo_id=0)

            elif lower.startswith("servo angle"):
                parts = lower.split()
                if len(parts) != 3:
                    print("Usage: servo angle <deg>")
                else:
                    try:
                        angle = float(parts[2])
                    except ValueError:
                        print("Angle must be a number")
                    else:
                        await client.send_servo_angle(servo_id=0, angle_deg=angle)

            elif lower.startswith("servo sweep"):
                parts = lower.split()
                if len(parts) != 4:
                    print("Usage: servo sweep <start_deg> <end_deg>")
                else:
                    try:
                        start = float(parts[2])
                        end = float(parts[3])
                    except ValueError:
                        print("Angles must be numbers")
                    else:
                        await client.smooth_servo_move(servo_id=0, start_deg=start, end_deg=end)

            # --- Mode command ---
            elif lower.startswith("mode "):
                _, mode_str = lower.split(maxsplit=1)
                mode = mode_str.upper()
                await client.cmd_set_mode(mode=mode)
                print(f"[Shell] Requested mode: {mode}")

            else:
                print(f"[Shell] Unknown command: {line}")
                print("  Commands: ping | whoami | led on | led off | mode <name> |")
                print("            servo attach | servo angle <deg> | servo sweep a b | quit")

    finally:
        print("[Shell] Shutting down client...")
        await client.stop()
        print("[Shell] Done.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Shell] Force-quit.")
