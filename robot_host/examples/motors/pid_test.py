import asyncio
import time
from typing import Any, Dict, List, Optional

from robot_host.core.event_bus import EventBus
from robot_host.command.client import AsyncRobotClient
from robot_host.transport.tcp_transport import AsyncTcpTransport


async def main() -> None:
    host_sta = "10.0.0.60"
    host_ap  = "192.168.4.1"
    port = 3333

    bus = EventBus()
    transport = AsyncTcpTransport(host=host_sta, port=port)
    client = AsyncRobotClient(transport, bus=bus)

    motor_id = 0  # DC motor index you attached on the MCU

    # Shared state for waiting on one ACK at a time
    pending: Dict[str, Optional[asyncio.Future]] = {"future": None}

    def on_dc_ack(msg: Dict[str, Any]) -> None:
        """
        Called when we get any of the DC_*_ACK messages.
        Completes the currently pending future (if any).
        """
        print(f"[DC-PID-ACK] {msg}")

        fut = pending["future"]
        if fut is not None and not fut.done():
            fut.set_result(msg)

    # Subscribe to DC PID-related ACK topics (as published by AsyncRobotClient)
    bus.subscribe("cmd.DC_VEL_PID_ENABLE_ACK", on_dc_ack)
    bus.subscribe("cmd.DC_SET_VEL_GAINS_ACK", on_dc_ack)
    bus.subscribe("cmd.DC_SET_VEL_TARGET_ACK", on_dc_ack)
    bus.subscribe("cmd.DC_STOP_ACK", on_dc_ack)

    print("[DC-PID-TEST] Starting client...")
    await client.start()
    await asyncio.sleep(0.1)

    loop = asyncio.get_running_loop()

    async def send_cmd_and_wait(cmd_type: str,
                                payload: Dict[str, Any],
                                timeout: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        Helper: send a CMD_* message and wait for the next DC_*_ACK.
        """
        fut: asyncio.Future = loop.create_future()
        pending["future"] = fut

        t0 = time.perf_counter()
        try:
            await client.send_json_cmd(cmd_type, payload)
        except Exception as e:
            print(f"[DC-PID-TEST] Error sending {cmd_type}: {e!r}")
            pending["future"] = None
            return None

        try:
            ack = await asyncio.wait_for(fut, timeout=timeout)
            t1 = time.perf_counter()
            rtt_ms = (t1 - t0) * 1000.0
            print(f"[DC-PID-TEST] {cmd_type} RTT = {rtt_ms:.2f} ms")
            return ack
        except asyncio.TimeoutError:
            print(f"[DC-PID-TEST] {cmd_type} -> TIMEOUT waiting for ACK")
            return None
        finally:
            pending["future"] = None

    try:
        # ------------------------------------------------------------------
        # Optional: make sure motor is stopped first
        # ------------------------------------------------------------------
        print("[DC-PID-TEST] Sending initial DC_STOP...")
        await send_cmd_and_wait(
            "CMD_DC_STOP",
            {"motor_id": motor_id},
            timeout=1.0,
        )
        await asyncio.sleep(0.2)

        # ------------------------------------------------------------------
        # Enable PID
        # ------------------------------------------------------------------
        print("[DC-PID-TEST] Enabling velocity PID on motor", motor_id)
        await send_cmd_and_wait(
            "CMD_DC_VEL_PID_ENABLE",
            {"motor_id": motor_id, "enable": True},
            timeout=1.0,
        )
        await asyncio.sleep(0.2)

        # ------------------------------------------------------------------
        # Set PID gains
        # ------------------------------------------------------------------
        kp = 0.8
        ki = 0.1
        kd = 0.05
        print(f"[DC-PID-TEST] Setting PID gains kp={kp}, ki={ki}, kd={kd}")
        await send_cmd_and_wait(
            "CMD_DC_SET_VEL_GAINS",
            {
                "motor_id": motor_id,
                "kp": kp,
                "ki": ki,
                "kd": kd,
            },
            timeout=1.0,
        )
        await asyncio.sleep(0.2)

        # ------------------------------------------------------------------
        # Step through some target angular velocities
        # ------------------------------------------------------------------
        targets = [2.0, 4.0, 6.0, 3.0, 0.0]  # rad/s, sign = direction
        hold_sec = 2.0

        print("[DC-PID-TEST] Stepping through omega targets:", targets)
        for i, omega in enumerate(targets, start=1):
            print(f"[DC-PID-TEST {i:02d}] Setting omega={omega:.2f} rad/s")
            await send_cmd_and_wait(
                "CMD_DC_SET_VEL_TARGET",
                {
                    "motor_id": motor_id,
                    "omega": omega,
                },
                timeout=1.0,
            )
            # Let it run at this target so you can watch behavior
            await asyncio.sleep(hold_sec)

        # ------------------------------------------------------------------
        # Disable PID and stop
        # ------------------------------------------------------------------
        print("[DC-PID-TEST] Disabling velocity PID...")
        await send_cmd_and_wait(
            "CMD_DC_VEL_PID_ENABLE",
            {"motor_id": motor_id, "enable": False},
            timeout=1.0,
        )

        print("[DC-PID-TEST] Sending final DC_STOP...")
        await send_cmd_and_wait(
            "CMD_DC_STOP",
            {"motor_id": motor_id},
            timeout=1.0,
        )

        print("[DC-PID-TEST] Done.")

    finally:
        print("[DC-PID-TEST] Client stopping...")
        await client.stop()
        print("[DC-PID-TEST] Client stopped")


if __name__ == "__main__":
    asyncio.run(main())
