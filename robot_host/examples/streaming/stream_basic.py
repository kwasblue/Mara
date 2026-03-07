# robot_host/tools/stream_runner.py

from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from typing import Any, Dict, Optional

from robot_host.command.client import AsyncRobotClient

# Import your transports (adjust paths to your repo)
from robot_host.transport.tcp_transport import AsyncTcpTransport
from robot_host.transport.serial_transport import SerialTransport

# Your CommandStreamer (the one you posted / we’re building)
from robot_host.command.command_streamer import CommandStreamer  # adjust module name


Payload = Dict[str, Any]


def _parse_json_payload(s: Optional[str]) -> Payload:
    if not s:
        return {}
    try:
        obj = json.loads(s)
        if not isinstance(obj, dict):
            raise ValueError("payload must be a JSON object")
        return obj
    except Exception as e:
        raise SystemExit(f"Invalid --payload JSON: {e}")


async def run_velocity_example(
    robot: AsyncRobotClient,
    streamer: CommandStreamer,
    *,
    rate_hz: float,
    duration_s: float,
    vx: float,
    omega: float,
    sine: bool,
    amp_vx: float,
    amp_omega: float,
    freq_hz: float,
) -> None:
    """
    Example stream: CMD_SET_VEL at rate_hz.
    Uses a provider to generate payload each tick (no need to call update()).
    """

    t0 = time.monotonic()

    def provider() -> Payload:
        t = time.monotonic() - t0
        if sine:
            return {
                "vx": vx + amp_vx * math.sin(2.0 * math.pi * freq_hz * t),
                "omega": omega + amp_omega * math.sin(2.0 * math.pi * freq_hz * t),
                "frame": "robot",
            }
        return {"vx": vx, "omega": omega, "frame": "robot"}

    await streamer.register(
        name="vel",
        cmd="CMD_SET_VEL",
        rate_hz=rate_hz,
        provider=provider,
        request_ack=False,     # streaming => usually False
        ttl_s=None,
    )

    await streamer.start("vel")
    print(f"[stream_runner] Streaming CMD_SET_VEL at {rate_hz} Hz for {duration_s} s...")

    try:
        await asyncio.sleep(duration_s)
    finally:
        await streamer.stop("vel")
        # Best practice: send a STOP once when you stop streaming motion
        await robot.send_stream("CMD_STOP", {}, request_ack=True)
        print("[stream_runner] Velocity stream stopped. Sent CMD_STOP.")


async def run_generic_command_stream(
    robot: AsyncRobotClient,
    streamer: CommandStreamer,
    *,
    cmd: str,
    payload: Payload,
    rate_hz: float,
    duration_s: float,
    request_ack: bool,
) -> None:
    """
    Generic: stream any command at a fixed rate with a fixed payload.
    """

    def provider() -> Payload:
        return payload

    await streamer.register(
        name="generic",
        cmd=cmd,
        rate_hz=rate_hz,
        provider=provider,
        request_ack=request_ack,
        ttl_s=None,
    )

    await streamer.start("generic")
    print(f"[stream_runner] Streaming {cmd} at {rate_hz} Hz for {duration_s} s...")
    print(f"[stream_runner] payload={payload} ack={request_ack}")

    try:
        await asyncio.sleep(duration_s)
    finally:
        await streamer.stop("generic")
        print("[stream_runner] Generic stream stopped.")


async def main() -> None:
    ap = argparse.ArgumentParser(description="Robot command stream runner")

    # Transport selection
    ap.add_argument("--tcp", action="store_true", help="Use TCP transport")
    ap.add_argument("--host", default="10.0.0.60", help="TCP host (default: 10.0.0.60)")
    ap.add_argument("--port", type=int, default=3333, help="TCP port (default: 3333)")

    ap.add_argument("--serial", action="store_true", help="Use Serial transport")
    ap.add_argument("--serial-port", default="/dev/tty.usbserial-0001", help="Serial device")
    ap.add_argument("--baud", type=int, default=3000000, help="Serial baud rate")

    # Streaming parameters
    ap.add_argument("--rate", type=float, default=20.0, help="Stream rate in Hz")
    ap.add_argument("--duration", type=float, default=5.0, help="Stream duration in seconds")
    ap.add_argument("--ack", action="store_true", help="Request ACKs (not recommended for high-rate streams)")

    # Mode selection
    ap.add_argument("--mode", choices=["vel", "cmd"], default="vel")

    # vel mode
    ap.add_argument("--vx", type=float, default=0.2)
    ap.add_argument("--omega", type=float, default=0.0)
    ap.add_argument("--sine", action="store_true", help="Use sine wave modulation")
    ap.add_argument("--amp-vx", type=float, default=0.15)
    ap.add_argument("--amp-omega", type=float, default=0.5)
    ap.add_argument("--freq", type=float, default=0.5, help="Sine frequency in Hz")

    # cmd mode
    ap.add_argument("--cmd", default="CMD_CTRL_SIGNAL_SET", help="Command to stream")
    ap.add_argument("--payload", default='{"id":110,"value":42.5}', help="JSON payload for --mode cmd")

    args = ap.parse_args()

    if not (args.tcp or args.serial):
        raise SystemExit("Pick a transport: --tcp or --serial")

    # Build transport
    if args.tcp:
        transport = AsyncTcpTransport(args.host, args.port)
    else:
        transport = SerialTransport(args.serial_port, args.baud)

    robot = AsyncRobotClient(
        transport=transport,
        heartbeat_interval_s=0.2,
        connection_timeout_s=1.0,
        command_timeout_s=0.25,
        max_retries=3,
        require_version_match=True,
        handshake_timeout_s=2.0,
    )

    await robot.start()

    streamer = CommandStreamer(robot)

    try:
        # Put robot into a known-safe state, then arm/activate if needed
        # (Optional but recommended for motion streams)
        await robot.send_stream("CMD_CLEAR_ESTOP", {}, request_ack=True)
        await robot.send_stream("CMD_DISARM", {}, request_ack=True)

        if args.mode == "vel":
            # For motion: ensure ACTIVE if your firmware requires it
            await robot.send_stream("CMD_ARM", {}, request_ack=True)
            await robot.send_stream("CMD_ACTIVATE", {}, request_ack=True)

            await run_velocity_example(
                robot, streamer,
                rate_hz=args.rate,
                duration_s=args.duration,
                vx=args.vx,
                omega=args.omega,
                sine=args.sine,
                amp_vx=args.amp_vx,
                amp_omega=args.amp_omega,
                freq_hz=args.freq,
            )

        else:
            payload = _parse_json_payload(args.payload)
            await run_generic_command_stream(
                robot, streamer,
                cmd=args.cmd,
                payload=payload,
                rate_hz=args.rate,
                duration_s=args.duration,
                request_ack=args.ack,
            )

    finally:
        await streamer.stop_all()
        await robot.stop()


if __name__ == "__main__":
    asyncio.run(main())
