"""
Servo test runner - test servo motor control via serial or TCP.

Example usage:
    # Serial (default)
    python -m robot_host.runners.servo_test --angle 90

    # TCP
    python -m robot_host.runners.servo_test --transport tcp --angle 45

    # Sweep test
    python -m robot_host.runners.servo_test --sweep --min-angle 0 --max-angle 180
"""

from __future__ import annotations

import asyncio
import argparse

from robot_host.robot import Robot
from robot_host.api.servo import Servo


# === Defaults ===

DEFAULT_SERIAL_PORT = "/dev/cu.usbserial-0001"
DEFAULT_BAUD = 115200

DEFAULT_TCP_HOST = "10.0.0.60"
DEFAULT_TCP_PORT = 3333


async def tcp_preflight(host: str, port: int, timeout: float = 1.0) -> bool:
    """
    Try a one-shot TCP connection to verify the host:port is reachable.
    """
    print(f"[ServoTest] Preflight TCP check to {host}:{port} ...")
    try:
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
    except Exception as e:
        print(f"[ServoTest] Preflight FAILED: {e!r}")
        return False
    else:
        print("[ServoTest] Preflight SUCCESS, endpoint reachable")
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True


async def run_servo_test(
    transport_type: str,
    tcp_host: str,
    tcp_port: int,
    serial_port: str,
    baudrate: int,
    servo_id: int,
    channel: int,
    angle: float,
    sweep: bool,
    min_angle: float,
    max_angle: float,
    step: float,
    dwell: float,
    duration_ms: int,
):
    """Run servo test with specified parameters."""

    # --- Transport selection ---
    if transport_type == "tcp":
        ok = await tcp_preflight(tcp_host, tcp_port, timeout=1.0)
        if not ok:
            print("[ServoTest] Aborting: TCP endpoint not reachable")
            return

        print(f"[ServoTest] Using TCP transport to {tcp_host}:{tcp_port}")
        robot = Robot(host=tcp_host, tcp_port=tcp_port)

    elif transport_type == "serial":
        print(f"[ServoTest] Using SERIAL transport on {serial_port} @ {baudrate}")
        robot = Robot(port=serial_port, baudrate=baudrate)

    else:
        raise ValueError(f"Unknown transport type: {transport_type}")

    # --- Connect and run ---
    try:
        print("[ServoTest] Connecting...")
        await robot.connect()
        print("[ServoTest] Connected")

        # Small settle delay
        await asyncio.sleep(0.1)

        # Arm the robot
        print("[ServoTest] Arming robot...")
        success, err = await robot.arm()
        if not success:
            print(f"[ServoTest] Failed to arm: {err}")
            return

        print("[ServoTest] Activating robot...")
        success, err = await robot.activate()
        if not success:
            print(f"[ServoTest] Failed to activate: {err}")
            return

        # Create servo instance
        servo = Servo(
            robot,
            servo_id=servo_id,
            channel=channel,
            min_angle=min_angle,
            max_angle=max_angle,
        )

        print(f"[ServoTest] Attaching servo (id={servo_id}, channel={channel})")
        await servo.attach()

        if sweep:
            # Sweep mode: move through full range
            print(f"[ServoTest] Starting sweep from {min_angle}° to {max_angle}°")

            # Forward sweep
            current = min_angle
            while current <= max_angle:
                print(f"[ServoTest] -> {current:.1f}°")
                await servo.set_angle(current, duration_ms=duration_ms)
                await asyncio.sleep(dwell)
                current += step

            # Reverse sweep
            print(f"[ServoTest] Reversing sweep from {max_angle}° to {min_angle}°")
            current = max_angle
            while current >= min_angle:
                print(f"[ServoTest] -> {current:.1f}°")
                await servo.set_angle(current, duration_ms=duration_ms)
                await asyncio.sleep(dwell)
                current -= step

            # Return to center
            center = (min_angle + max_angle) / 2
            print(f"[ServoTest] Returning to center ({center:.1f}°)")
            await servo.set_angle(center, duration_ms=duration_ms)

        else:
            # Single angle mode
            print(f"[ServoTest] Setting angle to {angle}°")
            await servo.set_angle(angle, duration_ms=duration_ms)
            print(f"[ServoTest] Servo set to {angle}°")

        # Hold position briefly
        await asyncio.sleep(0.5)

        # Detach servo
        print("[ServoTest] Detaching servo")
        await servo.detach()

        print("[ServoTest] Test complete")

    except Exception as e:
        print(f"[ServoTest] Error: {e!r}")
        raise

    finally:
        print("[ServoTest] Disconnecting...")
        await robot.disconnect()
        print("[ServoTest] Disconnected")


def main():
    parser = argparse.ArgumentParser(
        description="Servo test runner (TCP or Serial)"
    )

    # Transport options
    parser.add_argument(
        "--transport",
        choices=["tcp", "serial"],
        default="serial",
        help="Transport type (default: serial)",
    )

    # TCP options
    parser.add_argument(
        "--tcp-host",
        default=DEFAULT_TCP_HOST,
        help=f"TCP host/IP (default: {DEFAULT_TCP_HOST})",
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=DEFAULT_TCP_PORT,
        help=f"TCP port (default: {DEFAULT_TCP_PORT})",
    )

    # Serial options
    parser.add_argument(
        "--serial-port",
        default=DEFAULT_SERIAL_PORT,
        help=f"Serial device (default: {DEFAULT_SERIAL_PORT})",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=DEFAULT_BAUD,
        help=f"Serial baudrate (default: {DEFAULT_BAUD})",
    )

    # Servo configuration
    parser.add_argument(
        "--servo-id",
        type=int,
        default=0,
        help="Servo ID (default: 0)",
    )
    parser.add_argument(
        "--channel",
        type=int,
        default=0,
        help="PWM channel (default: 0)",
    )

    # Angle control
    parser.add_argument(
        "--angle",
        type=float,
        default=90.0,
        help="Target angle in degrees (default: 90)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        dest="duration_ms",
        help="Transition duration in ms (default: 0 = immediate)",
    )

    # Sweep mode
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Enable sweep mode (move through full range)",
    )
    parser.add_argument(
        "--min-angle",
        type=float,
        default=0.0,
        help="Minimum angle for sweep (default: 0)",
    )
    parser.add_argument(
        "--max-angle",
        type=float,
        default=180.0,
        help="Maximum angle for sweep (default: 180)",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=10.0,
        help="Angle step for sweep (default: 10)",
    )
    parser.add_argument(
        "--dwell",
        type=float,
        default=0.3,
        help="Pause between moves in seconds (default: 0.3)",
    )

    args = parser.parse_args()

    asyncio.run(
        run_servo_test(
            transport_type=args.transport,
            tcp_host=args.tcp_host,
            tcp_port=args.tcp_port,
            serial_port=args.serial_port,
            baudrate=args.baud,
            servo_id=args.servo_id,
            channel=args.channel,
            angle=args.angle,
            sweep=args.sweep,
            min_angle=args.min_angle,
            max_angle=args.max_angle,
            step=args.step,
            dwell=args.dwell,
            duration_ms=args.duration_ms,
        )
    )


if __name__ == "__main__":
    main()
