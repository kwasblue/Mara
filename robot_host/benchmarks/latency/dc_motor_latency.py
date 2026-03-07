# robot_host/runners/dc_ping_latency.py

import asyncio
import time
from statistics import mean
from typing import Any, Dict, Optional

from robot_host.core.event_bus import EventBus
from robot_host.command.client import AsyncRobotClient
from robot_host.transport.tcp_transport import AsyncTcpTransport
# from robot_host.transport.serial_transport import SerialTransport
# from robot_host.transport.bluetooth_transport import BluetoothSerialTransport


class DcAckWaiter:
    """
    Waits for DC motor ACKs from the MCU.

    Listens directly to:
      - "cmd.DC_SET_SPEED_ACK"
      - "cmd.DC_STOP_ACK"

    Those are the topics published by AsyncRobotClient._handle_json_payload()
    when it sees:
      {"src": "mcu", "cmd": "DC_SET_SPEED_ACK", ...}
      {"src": "mcu", "cmd": "DC_STOP_ACK", ...}
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._future: Optional[asyncio.Future[Dict[str, Any]]] = None

        # Subscribe directly to the command ACK topics
        bus.subscribe("cmd.DC_SET_SPEED_ACK", self._on_ack)
        bus.subscribe("cmd.DC_STOP_ACK", self._on_ack)

    def _on_ack(self, msg: Any) -> None:
        """
        Called when a DC_*_ACK is published on the bus.
        The msg is already a dict from RobotClient._handle_json_payload().
        """
        if self._future is None or self._future.done():
            return

        if not isinstance(msg, dict):
            return

        # Optional: debug log to see what we captured
        print(f"[DC-ACK] {msg}")

        self._future.set_result(msg)

    async def wait_for_ack(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Arm the waiter and block until a DC_*_ACK arrives or timeout.
        """
        loop = asyncio.get_running_loop()
        self._future = loop.create_future()

        try:
            return await asyncio.wait_for(self._future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._future = None


async def main() -> None:
    bus = EventBus()

    # --- Transport selection ---
    host_ap  = "192.168.4.1" # onboard wifi from esp32
    host_sta = "10.0.0.60"
    transport = AsyncTcpTransport(host=host_sta, port=3333)
    # Or use Serial if you prefer:
    # transport = SerialTransport(port="/dev/cu.usbserial-0001", baudrate=115200)

    client = AsyncRobotClient(transport=transport, bus=bus)
    waiter = DcAckWaiter(bus)

    await client.start()
    print("[DC-PINGTEST] Client started, measuring RTT via DC_SET_SPEED/ACK")

    # Optional: slow telemetry so it doesn't drown logs
    try:
        await client.send_json_cmd("CMD_TELEM_SET_INTERVAL", {"interval_ms": 1000})
    except Exception:
        pass

    NUM_PINGS = 30
    MOTOR_ID = 0
    SPEED = 1.0  # full speed forward

    rtts: list[float] = []

    try:
        for i in range(1, NUM_PINGS + 1):
            # 1) Arm waiter BEFORE sending, to avoid race
            wait_task = asyncio.create_task(waiter.wait_for_ack(timeout=1.0))

            # 2) Send speed command
            t0 = time.perf_counter()
            await client.send_json_cmd(
                "CMD_DC_SET_SPEED",
                {"motor_id": MOTOR_ID, "speed": SPEED},
            )

            # 3) Wait for ACK
            ack = await wait_task
            t1 = time.perf_counter()

            if ack is None:
                print(f"[DC-PING {i:02d}] RTT = TIMEOUT")
            else:
                rtt_ms = (t1 - t0) * 1000.0
                rtts.append(rtt_ms)
                print(f"[DC-PING {i:02d}] RTT = {rtt_ms:.2f} ms (ack={ack})")

            # 4) Stop motor and wait for its ACK, but we don't measure RTT here
            stop_wait = asyncio.create_task(waiter.wait_for_ack(timeout=1.0))
            await client.send_json_cmd(
                "CMD_DC_STOP",
                {"motor_id": MOTOR_ID},
            )
            await stop_wait

            await asyncio.sleep(0.2)

    finally:
        print("[DC-PINGTEST] Client stopping...")
        await client.stop()
        print("[DC-PINGTEST] Client stopped\n")

    valid = [x for x in rtts if x is not None]
    print("=== DC Ping latency stats ===")
    print(f"Count: {len(valid)} (out of {NUM_PINGS})")
    if valid:
        print(f"Min:   {min(valid):.2f} ms")
        print(f"Max:   {max(valid):.2f} ms")
        print(f"Avg:   {mean(valid):.2f} ms")


if __name__ == "__main__":
    asyncio.run(main())
