# robot_host/runners/ping_latency_test.py

import asyncio
from statistics import mean

from robot_host.core.event_bus import EventBus
from robot_host.command.client import AsyncRobotClient
from robot_host.transport.tcp_transport import AsyncTcpTransport
# from robot_host.transport.serial_transport import SerialTransport
# from robot_host.transport.bluetooth_transport import BluetoothSerialTransport


class PingLatencyMeasurer:
    def __init__(self, bus: EventBus, client: AsyncRobotClient) -> None:
        self._bus = bus
        self._client = client
        self._pending: asyncio.Future[float] | None = None

        # Subscribe to the same topic your client uses for ping responses
        bus.subscribe("pong", self._on_pong)

    def _on_pong(self, msg: dict) -> None:
        """
        Called whenever a PONG frame arrives from the MCU.
        We just use the arrival time on the host.
        """
        if self._pending is None or self._pending.done():
            return

        loop = asyncio.get_running_loop()
        t_arrive = loop.time()
        self._pending.set_result(t_arrive)

    async def measure_once(self, timeout: float = 1.0) -> float | None:
        """
        Send one ping and measure round-trip in milliseconds.
        Returns None on timeout.
        """
        loop = asyncio.get_running_loop()
        self._pending = loop.create_future()

        t0 = loop.time()
        await self._client.send_ping()

        try:
            t1 = await asyncio.wait_for(self._pending, timeout)
        except asyncio.TimeoutError:
            print("[PING] Timeout waiting for pong")
            self._pending = None
            return None

        self._pending = None
        rtt_ms = (t1 - t0) * 1000.0
        return rtt_ms


async def main() -> None:
    # --- Transport setup (same idea as your shell) ---
    host_sta = "10.0.0.60" 
    host_ap  = "192.168.4.1"  # STA IP or AP IP, whatever you're using
    port = 3333

    # For TCP:
    transport = AsyncTcpTransport(host=host_sta, port=port)

    # For serial instead:
    # transport = SerialTransport(port="/dev/cu.usbserial-0001", baudrate=115200)

    # For Bluetooth instead:
    # transport = BluetoothSerialTransport.auto(device_name="ESP32-SPP", baudrate=115200)

    bus = EventBus()
    client = AsyncRobotClient(transport=transport, bus=bus)

    await client.start()
    print("[PINGTEST] Client started, measuring RTT via ping/pong")

    measurer = PingLatencyMeasurer(bus, client)

    N = 30          # number of pings
    DELAY = 0.2     # seconds between pings

    results: list[float] = []

    try:
        for i in range(N):
            rtt = await measurer.measure_once(timeout=1.0)
            if rtt is not None:
                results.append(rtt)
                print(f"[PING {i+1:02d}] RTT = {rtt:.2f} ms")
            else:
                print(f"[PING {i+1:02d}] RTT = TIMEOUT")

            await asyncio.sleep(DELAY)

    finally:
        await client.stop()
        print("[PINGTEST] Client stopped")

    if results:
        print("\n=== Ping latency stats ===")
        print(f"Count: {len(results)}")
        print(f"Min:   {min(results):.2f} ms")
        print(f"Max:   {max(results):.2f} ms")
        print(f"Avg:   {mean(results):.2f} ms")
    else:
        print("[PINGTEST] No successful pings recorded")


if __name__ == "__main__":
    asyncio.run(main())
