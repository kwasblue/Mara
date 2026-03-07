import asyncio
from pathlib import Path

from robot_host.command.client import AsyncRobotClient
from robot_host.core.event_bus import EventBus
from robot_host.research.recording import RecordingTransport, RecordingEventBus
from robot_host.logger.logger import MaraLogBundle
from robot_host.transport.serial_transport import SerialTransport  # or StreamTransport / AsyncTcpTransport

async def main():
    bundle = MaraLogBundle(name="short_session", log_dir="logs", console=True)
    bus = RecordingEventBus(EventBus(), bundle)

    # pick your real transport
    inner = SerialTransport(port="/dev/tty.usbserial-0001", baudrate=115200)
    transport = RecordingTransport(inner, bundle)

    client = AsyncRobotClient(transport=transport, bus=bus)
    client.logs = bundle  # if your client uses self.logs in heartbeat stats snapshots

    await client.start()

    # 10 reliable commands (use whatever is safe)
    for _ in range(10):
        await client.send_reliable("CMD_STOP", {}, wait_for_ack=True)
        await asyncio.sleep(0.05)

    await asyncio.sleep(1.2)  # allow at least one stats snapshot tick
    await client.stop()
    bundle.close()

    print("Wrote:", Path("logs") / "short_session.jsonl")

if __name__ == "__main__":
    asyncio.run(main())
