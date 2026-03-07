# robot_host/runners/run_tcp_client_async.py

import asyncio

from robot_host.command.client import AsyncRobotClient
from robot_host.transport.tcp_transport import AsyncTcpTransport


async def main() -> None:
    # AP mode IP (RobotAP): 192.168.4.1
    # STA mode IP (home WiFi): whatever the ESP32 prints, e.g. 10.0.0.107
    host_ap  = "192.168.4.1"
    host_sta = "10.0.0.60"
    port = 3333

    transport = AsyncTcpTransport(host=host_sta, port = port)
    client = AsyncRobotClient(transport, connection_timeout_s=6.0)

    # Subscribe to events
    client.bus.subscribe("heartbeat", lambda d: print("[TCP] HEARTBEAT", d))
    client.bus.subscribe("pong",      lambda d: print("[TCP] PONG", d))
    client.bus.subscribe("hello",     lambda info: print("[Bus] HELLO:", info))
    client.bus.subscribe("json",      lambda obj: print("[Bus] JSON:", obj))
    client.bus.subscribe("error",     lambda err: print("[Bus] ERROR:", err))

    await client.start()

    try:
        last_ping = 0.0
        await client.cmd_set_mode('ACTIVE')
        await client.cmd_servo_attach(servo_id=0, channel=0, min_us=500, max_us=2500)
        loop = asyncio.get_running_loop()
        while True:
            now = loop.time()
            if now - last_ping >= 5.0:
                await client.send_ping()
                await client.cmd_led_on()
                await asyncio.sleep(0.1)
                await client.cmd_servo_set_angle(servo_id=0, angle_deg=180, duration_ms=5)
                await asyncio.sleep(0.25)
                await client.cmd_led_off()
                await asyncio.sleep(0.1)
                await client.cmd_servo_set_angle(servo_id=0, angle_deg=0, duration_ms=5)
                await asyncio.sleep(0.25)
                await client.cmd_led_off()
                last_ping = now
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[TCP] Stopping...")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
