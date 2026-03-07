# robot_host/runners/interactive_shell.py

import asyncio
from typing import Callable, Iterable

from robot_host.command.client import AsyncRobotClient
from robot_host.transport.tcp_transport import AsyncTcpTransport
from robot_host.transport.serial_transport import SerialTransport
from robot_host.tools.imu_calibrator import ImuCalibrator  # adjust import path as needed



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


async def pick_reachable_host(
    hosts: Iterable[str],
    port: int,
    timeout: float = 10,
) -> str:
    """
    Try each host in order, return the first that accepts a TCP connection.

    This does an actual TCP connect probe and immediately closes it.
    Raises RuntimeError if no hosts are reachable.
    """
    for host in hosts:
        try:
            print(f"[Shell] Probing {host}:{port} ...")
            conn_coro = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn_coro, timeout=timeout)
            # We just probed connectivity – close this test connection.
            writer.close()
            await writer.wait_closed()
            print(f"[Shell] Selected host: {host}:{port}")
            return host
        except Exception as e:
            print(f"[Shell] Host {host}:{port} not reachable: {e!r}")

    raise RuntimeError("[Shell] No reachable robot host (STA or AP).")


async def main() -> None:
    # --- Network configuration ---
    host_sta = "10.0.0.60"     # ESP32 in STA mode on home Wi-Fi
    host_ap  = "192.168.4.1"    # ESP32 AP IP (RobotAP)
    port = 3333

    # Optional serial fallback (leave commented if you don't want it yet)
    serial_dev = "/dev/cu.usbserial-0001"

    # --- Choose transport: prefer STA, fall back to AP, then optional serial ---
    try:
        selected_host = await pick_reachable_host([host_sta, host_ap], port, timeout=1.0)
        transport = AsyncTcpTransport(selected_host, port)
        print(f"[Shell] Using TCP transport on {selected_host}:{port}")
    except RuntimeError as e:
        # GRACEFUL EXIT: no traceback, just a clear message
        print(str(e))
        print("")
        print("Hints:")
        print("  • Make sure the robot is powered on.")
        print("  • For STA: robot and laptop must be on the same Wi-Fi (host_sta).")
        print("  • For AP: connect to the robot's Wi-Fi (RobotAP) so 192.168.4.1 is reachable.")
        print("")
        print("[Shell] Exiting because no robot could be found.")
        return  # <- just end main(), no error

    client = AsyncRobotClient(transport=transport)

    # Subscribe to events
    client.bus.subscribe("heartbeat", _print_event("HEARTBEAT"))
    client.bus.subscribe("pong",      _print_event("PONG"))
    client.bus.subscribe("hello",     _print_event("HELLO"))
    client.bus.subscribe("json",      _print_event("JSON"))
    client.bus.subscribe("raw_frame", _print_event("RAW"))
    client.bus.subscribe("telemetry", _print_event("TELEM"))

    await client.start()
    calibrator = ImuCalibrator(client)

    print("")
    print("=== Robot Interactive Shell ===")
    print("Available commands:")
    print("  ping                 - send ping")
    print("  whoami               - ask robot identity")
    print("  led on               - turn LED on")
    print("  led off              - turn LED off")
    print("  mode <name>          - set mode (IDLE/ARMED/ACTIVE/CALIB)")
    print("  servo attach         - attach servo on channel 0")
    print("  servo angle <deg>    - move servo 0 to angle")
    print("  servo sweep a b      - sweep servo 0 from a→b smoothly")
    print("  ultrasonic attach     - attach ultrasonic sensor 0")
    print("  read ultrasonic       - single ultrasonic read (ACK)")
    print("  q / quit / exit      - quit")
    print("  Commands: ping | whoami | led on | led off | mode <name> |")
    print("            servo attach | servo angle <deg> | servo sweep a b |")
    print("            ultrasonic attach | read ultrasonic | quit")

    print("")
    
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
            # IMU offline or bad sample; you can make this quieter if you want
            # print("[IMU] offline or bad sample")
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
                # Uses default min/max from the client-side helper
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
                # e.g. "servo sweep 0 180"
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
            # imu calibration:
            elif lower == "imu calibrate":
                # This will block the shell until samples are collected
                await calibrator.run()
            
            elif lower == "ultrasonic attach":
                await client.cmd_ultrasonic_attach()
            
            elif lower == "read ultrasonic":
                await client.cmd_ultrasonic_read()

            # --- Mode command ---
            elif lower.startswith("mode "):
                # e.g. "mode active"
                _, mode_str = lower.split(maxsplit=1)
                mode = mode_str.upper()  # IDLE/ARMED/ACTIVE/CALIB
                await client.cmd_set_mode(mode=mode)
                print(f"[Shell] Requested mode: {mode}")

            # --- Unknown command ---
            else:
                print(f"[Shell] Unknown command: {line}")
                print("  Commands: ping | whoami | led on | led off | mode <name> |")
                print("            servo attach | servo angle <deg> | servo sweep a b | quit")

    finally:
        # Ensure transport shuts down cleanly
        print("[Shell] Shutting down client...")
        await client.stop()
        print("[Shell] Done.")


if __name__ == "__main__":
    # Protect asyncio.run() from showing nasty tracebacks on Ctrl-C
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Shell] Force-quit.")

