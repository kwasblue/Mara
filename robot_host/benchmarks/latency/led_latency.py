import asyncio
import time
from typing import Any, Dict, List, Optional

from robot_host.core.event_bus import EventBus
from robot_host.command.client import AsyncRobotClient
from robot_host.transport.tcp_transport import AsyncTcpTransport

# Topics the client publishes for your LED acks:
#   "cmd.LED_ON_ACK"
#   "cmd.LED_OFF_ACK"


async def main() -> None:
    host_sta = "10.0.0.60"
    host_ap  = "192.168.4.1"
    port = 3333

    bus = EventBus()
    transport = AsyncTcpTransport(host=host_sta, port=port)
    client = AsyncRobotClient(transport, bus=bus)

    # Shared state for waiting on a single ack at a time
    pending: Dict[str, Optional[asyncio.Future]] = {"future": None}

    def on_led_ack(msg: Dict[str, Any]) -> None:
        """
        Called when we get *either* LED_ON_ACK or LED_OFF_ACK.
        Completes the currently pending RTT future (if any).
        """
        print(f"[LED-ACK] {msg}")  # debug so you can see the incoming ack

        fut = pending["future"]
        if fut is not None and not fut.done():
            fut.set_result(msg)

    # Subscribe to both ack topics the client generates
    bus.subscribe("cmd.LED_ON_ACK", on_led_ack)
    bus.subscribe("cmd.LED_OFF_ACK", on_led_ack)

    print("[LED-PING] Starting client...")
    await client.start()

    NUM_SAMPLES = 30
    TIMEOUT_SEC = 0.5
    samples: List[float] = []

    try:
        # Optional: set a known starting state
        if hasattr(client, "send_led_off"):
            await client.send_led_off()
            await asyncio.sleep(0.1)

        print("[LED-PING] Measuring LED command latency via cmd.LED_ON_ACK / cmd.LED_OFF_ACK")

        loop = asyncio.get_running_loop()

        for i in range(1, NUM_SAMPLES + 1):
            turn_on = (i % 2 == 1)
            state_str = "ON" if turn_on else "OFF"

            # New future for this sample
            fut: asyncio.Future = loop.create_future()
            pending["future"] = fut

            t0 = time.perf_counter()

            # --- Send LED command ---
            try:
                if hasattr(client, "send_led_on") and hasattr(client, "send_led_off"):
                    if turn_on:
                        await client.send_led_on()
                    else:
                        await client.send_led_off()
                else:
                    # Fallback: raw JSON command name, in case helpers are different
                    cmd_type = "CMD_LED_ON" if turn_on else "CMD_LED_OFF"
                    await client.send_json_cmd(cmd_type, {})
            except Exception as e:
                print(f"[LED-PING {i:02d}] Error sending LED {state_str}: {e!r}")
                pending["future"] = None
                continue

            # --- Wait for LED_*_ACK on the cmd.* topics ---
            try:
                _ack = await asyncio.wait_for(fut, timeout=TIMEOUT_SEC)
                t1 = time.perf_counter()
                rtt_ms = (t1 - t0) * 1000.0
                samples.append(rtt_ms)
                print(f"[LED-PING {i:02d}] state={state_str} RTT = {rtt_ms:.2f} ms")
            except asyncio.TimeoutError:
                print(f"[LED-PING {i:02d}] state={state_str} RTT = TIMEOUT")
            finally:
                pending["future"] = None
                await asyncio.sleep(0.2)

    finally:
        print("[LED-PING] Client stopping...")
        await client.stop()
        print("[LED-PING] Client stopped")

        print("\n=== LED Command latency stats ===")
        print(f"Count: {len(samples)} (out of {NUM_SAMPLES})")
        if samples:
            print(f"Min:   {min(samples):.2f} ms")
            print(f"Max:   {max(samples):.2f} ms")
            avg = sum(samples) / len(samples)
            print(f"Avg:   {avg:.2f} ms")
        else:
            print("No successful samples (all timeouts).")


if __name__ == "__main__":
    asyncio.run(main())
