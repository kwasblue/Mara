# robot_host/runners/bluetooth_serial_shell.py

from __future__ import annotations

import asyncio
from typing import Callable

from robot_host.command.client import AsyncRobotClient
from robot_host.tools.imu_calibrator import ImuCalibrator  # adjust if needed

from robot_host.transport.bluetooth_transport import (
    BluetoothSerialTransport,
)
# If you want a USB fallback, you could also import:
# from robot_host.transport.serial_transport import SerialTransport


async def ainput(prompt: str = "") -> str:
    """
    Async-friendly input() so Ctrl-C is handled correctly.
    """
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, lambda: input(prompt))
    except KeyboardInterrupt:
        # Propagate so main loop can catch it
        raise


def _print_event(tag: str) -> Callable[[dict], None]:
    def _handler(data: dict) -> None:
        print(f"[{tag}] {data}")
    return _handler


async def main() -> None:
    baudrate = 115200

    # --- Pick Bluetooth SPP serial port automatically ---
    try:
        transport = BluetoothSerialTransport.auto(
            device_name="ESP32-SPP",
            baudrate=baudrate,
        )
    except Exception as e:
        print(f"[Shell] Failed to auto-detect Bluetooth serial device: {e!r}")
        print("")
        print("Hints:")
        print("  • Make sure the ESP32 is powered and advertising as 'ESP32-SPP'.")
        print("  • Pair it once in macOS Bluetooth settings.")
        print("  • Then run:  ls /dev/cu.*  and confirm a /dev/cu.ESP32-* device exists.")
        print("")
        print("[Shell] Exiting because no Bluetooth serial port was found.")
        return

    print(
        f"[Shell] Using BLUETOOTH SERIAL transport on {transport.port} "
        f"@ {baudrate} baud"
    )

    client = AsyncRobotClient(transport=transport)

    # Subscribe to core events
    client.bus.subscribe("heartbeat", _print_event("HEARTBEAT"))
    client.bus.subscribe("pong",      _print_event("PONG"))
    client.bus.subscribe("hello",     _print_event("HELLO"))
    client.bus.subscribe("json",      _print_event("JSON"))
    client.bus.subscribe("raw_frame", _print_event("RAW"))
    client.bus.subscribe("telemetry", _print_event("TELEM"))

    # Telemetry substreams (ultrasonic + IMU pretty-print)
    def _print_ultra(ultra: dict) -> None:
        if not ultra.get("attached"):
            print("[ULTRA] sensor 0 not attached")
            return
        if not ultra.get("ok", False):
            print("[ULTRA] read error / timeout")
            return
        dist = ultra.get("distance_cm")
        if dist is not None:
            print(f"[ULTRA] sensor 0: {dist:.1f} cm")

    def _print_imu(imu: dict) -> None:
        if not imu.get("ok", False):
            return
        roll = imu.get("roll_deg")
        pitch = imu.get("pitch_deg")
        acc_mag = imu.get("acc_mag_g")
        temp = imu.get("temp_c")

        print(
            f"[IMU] roll={roll:7.2f}°, "
            f"pitch={pitch:7.2f}°, "
            f"|a|={acc_mag:5.3f} g, "
            f"T={temp:5.2f} °C"
        )

    client.bus.subscribe("telemetry.ultrasonic", _print_ultra)
    client.bus.subscribe("telemetry.imu", _print_imu)

    await client.start()
    calibrator = ImuCalibrator(client)

    print("")
    print("=== Robot Interactive Shell (Bluetooth Serial) ===")
    print("Available commands:")
    print("  ping                 - send ping")
    print("  whoami               - ask robot identity")
    print("  led on               - turn LED on")
    print("  led off              - turn LED off")
    print("  mode <name>          - set mode (IDLE/ARMED/ACTIVE/CALIB)")
    print("  servo attach         - attach servo on channel 0")
    print("  servo angle <deg>    - move servo 0 to angle")
    print("  servo sweep a b      - sweep servo 0 from a→b smoothly")
    print("  imu calibrate        - run IMU calibration helper")
    print("  ultrasonic attach    - attach ultrasonic sensor 0")
    print("  read ultrasonic      - single ultrasonic read (ACK)")
    print("  q / quit / exit      - quit")
    print("")
    print("  Commands: ping | whoami | led on | led off | mode <name> |")
    print("            servo attach | servo angle <deg> | servo sweep a b |")
    print("            imu calibrate | ultrasonic attach | read ultrasonic | quit")
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
                        await client.smooth_servo_move(
                            servo_id=0,
                            start_deg=start,
                            end_deg=end,
                        )

            # --- IMU calibration ---
            elif lower == "imu calibrate":
                await calibrator.run()

            # --- Ultrasonic commands ---
            elif lower == "ultrasonic attach":
                await client.cmd_ultrasonic_attach()

            elif lower == "read ultrasonic":
                await client.cmd_ultrasonic_read()

            # --- Mode command ---
            elif lower.startswith("mode "):
                _, mode_str = lower.split(maxsplit=1)
                mode = mode_str.upper()  # IDLE/ARMED/ACTIVE/CALIB
                await client.cmd_set_mode(mode=mode)
                print(f"[Shell] Requested mode: {mode}")

            # --- Unknown command ---
            else:
                print(f"[Shell] Unknown command: {line}")
                print("  Commands: ping | whoami | led on | led off | mode <name> |")
                print("            servo attach | servo angle <deg> | servo sweep a b |")
                print("            imu calibrate | ultrasonic attach | read ultrasonic | quit")

    finally:
        print("[Shell] Shutting down client...")
        await client.stop()
        print("[Shell] Done.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Shell] Force-quit.")
