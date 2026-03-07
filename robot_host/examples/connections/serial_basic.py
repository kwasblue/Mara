import asyncio
from robot_host.command.client import AsyncRobotClient
from robot_host.transport.serial_transport import SerialTransport


async def main():
    port = "/dev/cu.usbserial-0001"
    serial_port = SerialTransport(port, baudrate=115200)
    client = AsyncRobotClient(serial_port)

    # subscribe to events
    client.bus.subscribe("heartbeat", lambda data: print(f"[Host] HEARTBEAT {data}"))
    client.bus.subscribe("pong", lambda data: print(f"[Host] PONG {data}"))

    await client.start()

    loop = asyncio.get_running_loop()
    last_ping = loop.time()

    try:
        while True:
            now = loop.time()
            if now - last_ping >= 5.0:
                await client.send_ping()
                last_ping = now

            await asyncio.sleep(0.1)
    finally:
        await client.stop()
        print("[Host] Stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Host] Ctrl+C, exiting...")
