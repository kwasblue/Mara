"""
dc_pid_sine_sweep.py

Drive the DC motor with a sine-wave velocity command and sweep through
a list of frequencies. The MCU runs the actual PID loop locally; this
script just updates target omega (rad/s).

Usage:
    python3 -m robot_host.runners.dc_pid_sine_sweep
"""

import asyncio
import math
import time
from typing import Any, Dict

from robot_host.core.event_bus import EventBus
from robot_host.command.client import AsyncRobotClient
from robot_host.transport.tcp_transport import AsyncTcpTransport


async def main() -> None:
    host_sta = "10.0.0.60"
    host_ap  = "192.168.4.1"
    port = 3333

    # Choose which IP you're actually using
    host = host_sta  # or host_ap if you're on the RobotAP network

    bus = EventBus()
    transport = AsyncTcpTransport(host=host, port=port)
    client = AsyncRobotClient(transport, bus=bus)

    motor_id = 0

    print("[SWEEP] Starting client...")
    await client.start()

    # Optional: set telemetry interval (adjust cmd name if different)
    try:
        await client.send_json_cmd(
            "CMD_TELEM_SET_INTERVAL",
            {"interval_ms": 50},   # 20 Hz telemetry
        )
        print("[SWEEP] Telemetry interval set to 50 ms")
    except Exception as e:
        print("[SWEEP] Could not set telemetry interval (maybe not wired yet):", e)

    # Helper to wait for a single ACK if we want it (for config steps only)
    pending: Dict[str, asyncio.Future] = {}

    def make_ack_waiter(topic: str):
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        pending["future"] = fut

        def _cb(msg: Dict[str, Any]) -> None:
            print(f"[SWEEP-ACK] {msg}")
            if not fut.done():
                fut.set_result(msg)

        bus.subscribe(topic, _cb)
        return fut

    async def wait_for_ack_on(topic: str, timeout: float = 1.0):
        fut = make_ack_waiter(topic)
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            print(f"[SWEEP] Timeout waiting for {topic}")
            return None
        finally:
            pending.pop("future", None)

    try:
        # ------------------------------------------------------------------
        # Initial stop (don't care if it times out early during connect)
        # ------------------------------------------------------------------
        print("[SWEEP] Sending initial DC_STOP...")
        try:
            await client.send_json_cmd("CMD_DC_STOP", {"motor_id": motor_id})
        except Exception as e:
            print("[SWEEP] Initial DC_STOP send error (ignoring):", e)
        await asyncio.sleep(0.2)

        # ------------------------------------------------------------------
        # Enable PID (with ACK)
        # ------------------------------------------------------------------
        print("[SWEEP] Enabling velocity PID on motor", motor_id)
        ack_fut = wait_for_ack_on("cmd.DC_VEL_PID_ENABLE_ACK")
        await client.send_json_cmd(
            "CMD_DC_VEL_PID_ENABLE",
            {"motor_id": motor_id, "enable": True},
        )
        await ack_fut

        # ------------------------------------------------------------------
        # Set PID gains (with ACK)
        # ------------------------------------------------------------------
        kp = 0.8
        ki = 0.1
        kd = 0.05
        print(f"[SWEEP] Setting PID gains kp={kp}, ki={ki}, kd={kd}")
        ack_fut = wait_for_ack_on("cmd.DC_SET_VEL_GAINS_ACK")
        await client.send_json_cmd(
            "CMD_DC_SET_VEL_GAINS",
            {
                "motor_id": motor_id,
                "kp": kp,
                "ki": ki,
                "kd": kd,
            },
        )
        await ack_fut

        # ------------------------------------------------------------------
        # Sine sweep: omega(t) = A * sin(2π f t)
        # ------------------------------------------------------------------
        # You can tweak these as you learn more about your motor
        amplitude = 6.0  # rad/s peak
        frequencies = [0.1, 0.2, 0.5, 1.0, 1.5]  # Hz
        dt_cmd = 0.1  # seconds between host updates (~20 Hz)

        print(f"[SWEEP] Starting sine sweep: A={amplitude} rad/s, dt_cmd={dt_cmd}s")
        for f in frequencies:
            # Run for at least a few periods at each frequency
            periods = 4.0
            duration = max(5.0, periods / f)
            steps = int(duration / dt_cmd)

            print(f"\n[SWEEP] f={f:.3f} Hz, duration={duration:.1f}s, steps={steps}")

            t_start = time.perf_counter()
            for k in range(steps):
                t = time.perf_counter() - t_start
                omega = amplitude * math.sin(2.0 * math.pi * f * t)

                # Fire-and-forget: we don't wait for individual ACKs here
                await client.send_json_cmd(
                    "CMD_DC_SET_VEL_TARGET",
                    {"motor_id": motor_id, "omega": omega},
                )

                await asyncio.sleep(dt_cmd)

            # Brief pause between frequencies
            print(f"[SWEEP] Done f={f:.3f} Hz, letting motor settle...")
            await client.send_json_cmd(
                "CMD_DC_SET_VEL_TARGET",
                {"motor_id": motor_id, "omega": 0.0},
            )
            await asyncio.sleep(2.0)

        # ------------------------------------------------------------------
        # Disable PID and stop
        # ------------------------------------------------------------------
        print("\n[SWEEP] Disabling PID and stopping motor...")
        ack_fut = wait_for_ack_on("cmd.DC_VEL_PID_ENABLE_ACK")
        await client.send_json_cmd(
            "CMD_DC_VEL_PID_ENABLE",
            {"motor_id": motor_id, "enable": False},
        )
        await ack_fut

        await client.send_json_cmd("CMD_DC_STOP", {"motor_id": motor_id})
        await asyncio.sleep(0.2)

        print("[SWEEP] Done.")

    finally:
        print("[SWEEP] Client stopping...")
        await client.stop()
        print("[SWEEP] Client stopped")


if __name__ == "__main__":
    asyncio.run(main())
