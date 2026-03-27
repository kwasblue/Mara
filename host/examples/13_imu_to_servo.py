#!/usr/bin/env python3
"""
Tie one IMU tilt axis to servo 0.

This host-side prototype reads the live IMU snapshot path already exposed by
``ImuService.read()``, derives a simple accel-based pitch or roll estimate,
applies optional zeroing, deadband, smoothing, and clamping, then drives servo 0
through the existing servo command path.

Safety notes:
- Start with the servo horn disconnected or with plenty of clearance.
- This script arms the robot, attaches the servo, and will detach + disarm on exit.
- Press Ctrl+C to stop cleanly.

Typical use:
    cd host
    python examples/13_imu_to_servo.py --port /dev/ttyUSB0 --pin 18 --axis pitch

Dry-run without moving the servo:
    python examples/13_imu_to_servo.py --port /dev/ttyUSB0 --pin 18 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import math
import signal
from dataclasses import dataclass
from typing import Optional

from mara_host import Robot
from mara_host.services.control.imu_service import ImuService


DEFAULT_SERVO_PIN = 18  # firmware PinConfig.h -> SERVO1_SIG


@dataclass
class ControllerState:
    zero_deg: float = 0.0
    filtered_angle_deg: Optional[float] = None
    last_command_deg: Optional[float] = None


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def map_range(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    if math.isclose(in_min, in_max):
        raise ValueError("input range must be non-zero")
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)


def accel_axis_deg(axis: str, ax: float, ay: float, az: float) -> float:
    """Compute a simple accel-only tilt estimate in degrees."""
    if axis == "roll":
        return math.degrees(math.atan2(ay, az))
    if axis == "pitch":
        return math.degrees(math.atan2(-ax, math.sqrt(ay ** 2 + az ** 2)))
    raise ValueError(f"unsupported axis: {axis}")


async def wait_for_good_imu(imu_service: ImuService, axis: str, timeout_s: float) -> tuple[float, dict]:
    deadline = asyncio.get_running_loop().time() + timeout_s
    last_error = "timed out waiting for IMU"

    while asyncio.get_running_loop().time() < deadline:
        result = await imu_service.read()
        if result.ok and result.data and result.data.get("online", False):
            data = result.data
            angle_deg = accel_axis_deg(axis, data["ax"], data["ay"], data["az"])
            return angle_deg, data

        last_error = result.error if not result.ok else "IMU reported offline"
        await asyncio.sleep(0.1)

    raise RuntimeError(last_error)


async def cleanup(robot: Robot, servo_id: int) -> None:
    errors: list[str] = []

    try:
        result = await robot.servo_service.detach(servo_id)
        if not result.ok:
            errors.append(f"detach failed: {result.error}")
    except Exception as exc:  # pragma: no cover - best effort cleanup
        errors.append(f"detach exception: {exc}")

    try:
        ok, error = await robot.disarm()
        if not ok:
            errors.append(f"disarm failed: {error}")
    except Exception as exc:  # pragma: no cover - best effort cleanup
        errors.append(f"disarm exception: {exc}")

    if errors:
        print("cleanup warnings:")
        for err in errors:
            print(f"  - {err}")


async def run(args: argparse.Namespace) -> int:
    robot_kwargs = {"host": args.tcp, "tcp_port": args.tcp_port} if args.tcp else {"port": args.port}

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            pass

    state = ControllerState()

    async with Robot(**robot_kwargs) as robot:
        imu_service = ImuService(robot.client)
        print("connected")
        ok, error = await robot.arm()
        if not ok:
            raise RuntimeError(f"failed to arm: {error}")
        print("armed")

        attach_result = await robot.servo_service.attach(
            args.servo_id,
            channel=args.pin,
            min_us=args.min_us,
            max_us=args.max_us,
        )
        if not attach_result.ok:
            raise RuntimeError(f"failed to attach servo: {attach_result.error}")
        print(f"servo {args.servo_id} attached on pin {args.pin}")

        # Move to center first so the starting point is predictable.
        center_result = await robot.servo_service.set_angle(
            args.servo_id,
            args.center_deg,
            duration_ms=args.move_duration_ms,
        )
        if not center_result.ok:
            raise RuntimeError(f"failed to center servo: {center_result.error}")
        await asyncio.sleep(max(0.3, args.move_duration_ms / 1000.0 + 0.1))

        zero_deg, first_sample = await wait_for_good_imu(imu_service, args.axis, args.imu_timeout_s)
        state.zero_deg = zero_deg if args.zero_on_start else 0.0

        print(
            f"imu online: axis={args.axis} raw={zero_deg:+.2f}deg "
            f"zero_ref={state.zero_deg:+.2f}deg accel=({first_sample['ax']:+.3f}, {first_sample['ay']:+.3f}, {first_sample['az']:+.3f})"
        )
        print(
            "controller: "
            f"servo=[{args.min_angle_deg:.1f},{args.max_angle_deg:.1f}] center={args.center_deg:.1f} "
            f"tilt_limit={args.tilt_limit_deg:.1f} deadband={args.deadband_deg:.1f} "
            f"alpha={args.smoothing_alpha:.2f} interval={args.interval_s:.3f}s"
        )
        if args.dry_run:
            print("dry-run enabled: servo commands after centering are suppressed")
        print("press Ctrl+C to stop")

        try:
            while not stop_event.is_set():
                result = await imu_service.read()
                if not result.ok or not result.data:
                    print(f"imu read failed: {result.error}")
                    await asyncio.sleep(args.interval_s)
                    continue

                data = result.data
                if not data.get("online", False):
                    print("imu offline")
                    await asyncio.sleep(args.interval_s)
                    continue

                raw_axis_deg = accel_axis_deg(args.axis, data["ax"], data["ay"], data["az"])
                relative_axis_deg = raw_axis_deg - state.zero_deg

                if abs(relative_axis_deg) < args.deadband_deg:
                    relative_axis_deg = 0.0

                servo_target_deg = map_range(
                    clamp(relative_axis_deg, -args.tilt_limit_deg, args.tilt_limit_deg),
                    -args.tilt_limit_deg,
                    args.tilt_limit_deg,
                    args.center_deg - args.servo_span_deg,
                    args.center_deg + args.servo_span_deg,
                )
                servo_target_deg = clamp(servo_target_deg, args.min_angle_deg, args.max_angle_deg)

                if state.filtered_angle_deg is None:
                    filtered_angle = servo_target_deg
                else:
                    filtered_angle = (
                        args.smoothing_alpha * servo_target_deg
                        + (1.0 - args.smoothing_alpha) * state.filtered_angle_deg
                    )
                state.filtered_angle_deg = filtered_angle

                should_send = (
                    state.last_command_deg is None
                    or abs(filtered_angle - state.last_command_deg) >= args.command_deadband_deg
                )

                if should_send and not args.dry_run:
                    servo_result = await robot.servo_service.set_angle(
                        args.servo_id,
                        filtered_angle,
                        duration_ms=args.move_duration_ms,
                        request_ack=not args.fast_no_ack,
                    )
                    if not servo_result.ok:
                        print(f"servo set failed: {servo_result.error}")
                    else:
                        state.last_command_deg = filtered_angle
                elif should_send:
                    state.last_command_deg = filtered_angle

                print(
                    f"{args.axis:>5} raw={raw_axis_deg:+7.2f}deg rel={relative_axis_deg:+7.2f}deg "
                    f"-> target={servo_target_deg:6.2f}deg filt={filtered_angle:6.2f}deg"
                )
                await asyncio.sleep(args.interval_s)
        finally:
            await cleanup(robot, args.servo_id)
            print("stopped: servo detached, robot disarmed")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Map one IMU accel tilt axis to servo 0",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    conn = parser.add_mutually_exclusive_group(required=False)
    conn.add_argument("-p", "--port", default="/dev/ttyUSB0", help="Serial port")
    conn.add_argument("--tcp", help="TCP host instead of serial")
    parser.add_argument("--tcp-port", type=int, default=3333, help="TCP port when using --tcp")

    parser.add_argument("--servo-id", type=int, default=0, help="Servo ID to drive")
    parser.add_argument("--pin", type=int, default=DEFAULT_SERVO_PIN, help="Servo signal pin/channel")
    parser.add_argument("--min-us", type=int, default=500, help="Servo minimum pulse width")
    parser.add_argument("--max-us", type=int, default=2500, help="Servo maximum pulse width")
    parser.add_argument("--min-angle-deg", type=float, default=60.0, help="Hard minimum commanded servo angle")
    parser.add_argument("--max-angle-deg", type=float, default=120.0, help="Hard maximum commanded servo angle")
    parser.add_argument("--center-deg", type=float, default=90.0, help="Servo center angle")
    parser.add_argument("--servo-span-deg", type=float, default=20.0, help="Maximum +/- travel away from center")
    parser.add_argument("--move-duration-ms", type=int, default=120, help="Per-command servo move duration")

    parser.add_argument("--axis", choices=["pitch", "roll"], default="pitch", help="IMU axis to use")
    parser.add_argument("--tilt-limit-deg", type=float, default=25.0, help="Tilt magnitude that maps to full servo span")
    parser.add_argument("--deadband-deg", type=float, default=2.0, help="Ignore small tilt around zero")
    parser.add_argument("--command-deadband-deg", type=float, default=1.0, help="Minimum servo angle delta before sending another command")
    parser.add_argument("--smoothing-alpha", type=float, default=0.25, help="EMA smoothing coefficient (0..1, higher = more responsive)")
    parser.add_argument("--interval-s", type=float, default=0.20, help="Controller update interval in seconds")
    parser.add_argument("--imu-timeout-s", type=float, default=3.0, help="How long to wait for the first good IMU sample")
    parser.add_argument("--zero-on-start", action=argparse.BooleanOptionalAction, default=True, help="Use the initial IMU angle as zero reference")
    parser.add_argument("--fast-no-ack", action="store_true", help="Use fire-and-forget servo commands after attach")
    parser.add_argument("--dry-run", action="store_true", help="Print computed angles without moving the servo")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.min_angle_deg >= args.max_angle_deg:
        parser.error("--min-angle-deg must be < --max-angle-deg")
    if not (args.min_angle_deg <= args.center_deg <= args.max_angle_deg):
        parser.error("--center-deg must lie inside the servo angle range")
    if args.servo_span_deg <= 0:
        parser.error("--servo-span-deg must be > 0")
    if args.tilt_limit_deg <= 0:
        parser.error("--tilt-limit-deg must be > 0")
    if not (0.0 <= args.smoothing_alpha <= 1.0):
        parser.error("--smoothing-alpha must be in [0, 1]")
    if args.interval_s <= 0.0:
        parser.error("--interval-s must be > 0")

    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
