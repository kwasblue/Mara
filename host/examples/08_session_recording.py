#!/usr/bin/env python3
"""
Example 08: Session Recording

Demonstrates:
- Recording all events during a session
- Recording transport messages (rx/tx)
- Saving sessions for later analysis
- Replaying recorded sessions

Prerequisites:
- ESP32 connected

Usage:
    python 08_session_recording.py /dev/ttyUSB0
    python 08_session_recording.py tcp:192.168.1.100

Output:
    Creates session logs in ./recordings/
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from mara_host.transport.serial_transport import SerialTransport
from mara_host.transport.tcp_transport import AsyncTcpTransport
from mara_host.command.client import AsyncRobotClient
from mara_host.core.event_bus import EventBus
from mara_host.logger.logger import MaraLogBundle
from mara_host.research.recording import RecordingEventBus, RecordingTransport
from mara_host.research.replay import SessionReplay


def create_transport(arg: str):
    if arg.startswith("tcp:"):
        host = arg[4:]
        port = 8080
        if ":" in host:
            host, port_str = host.rsplit(":", 1)
            port = int(port_str)
        return AsyncTcpTransport(host=host, port=port)
    else:
        return SerialTransport(port=arg, baudrate=115200)


async def record_session(transport_arg: str, duration: float = 10.0):
    """Record a session with the robot."""

    # Create output directory
    output_dir = Path("recordings")
    output_dir.mkdir(exist_ok=True)

    # Session name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"session_{timestamp}"

    print("="*60)
    print("Session Recording Example")
    print("="*60)
    print(f"Recording to: {output_dir / session_name}")
    print(f"Duration: {duration} seconds")
    print()

    # Create log bundle for recording
    bundle = MaraLogBundle(
        name=session_name,
        log_dir=str(output_dir),
        console=False,
    )

    # Create base transport and event bus
    base_transport = create_transport(transport_arg)
    base_bus = EventBus()

    # Wrap with recording wrappers
    recording_transport = RecordingTransport(base_transport, bundle)
    recording_bus = RecordingEventBus(base_bus, bundle)

    # Create client with recording wrappers
    client = AsyncRobotClient(
        transport=recording_transport,
        bus=recording_bus,
    )

    try:
        print("Starting session...")
        await client.start()
        print(f"Connected to {client.robot_name}")

        # Record session info
        bundle.events.write("session.start",
            robot=client.robot_name,
            firmware=client.firmware_version,
            protocol=client.protocol_version,
        )

        # Enable telemetry for interesting data
        await client.send_reliable("CMD_TELEMETRY_ON", {})
        bundle.events.write("session.telemetry_enabled")

        # Run some commands during recording
        print("\nRecording session...")
        print("  Sending periodic commands...")

        for i in range(int(duration)):
            await asyncio.sleep(1)

            # Send a ping every second
            await client.send_json_cmd("CMD_PING", {})

            # Every 3 seconds, send a velocity command
            if i % 3 == 0:
                await client.send_reliable("CMD_SET_VEL", {"vx": 0.0, "omega": 0.0})

            print(f"  [{i+1}/{int(duration)}s]")

        # Disable telemetry
        await client.send_reliable("CMD_TELEMETRY_OFF", {})
        bundle.events.write("session.telemetry_disabled")

        bundle.events.write("session.end")

        print("\nSession recorded!")

        # Find the log file
        log_files = list(output_dir.glob(f"{session_name}*.jsonl"))
        if log_files:
            log_path = log_files[0]
            print(f"Log file: {log_path}")
            print(f"File size: {log_path.stat().st_size} bytes")

            # Count events
            with open(log_path) as f:
                event_count = sum(1 for _ in f)
            print(f"Events recorded: {event_count}")

            return str(log_path)

    except Exception as e:
        print(f"Error: {e}")
        bundle.events.write("session.error", error=str(e))
        raise

    finally:
        await client.stop()

    return None


async def analyze_recording(log_path: str):
    """Analyze a recorded session."""

    print()
    print("="*60)
    print("Session Analysis")
    print("="*60)
    print(f"Analyzing: {log_path}")
    print()

    replay = SessionReplay(log_path)

    # Convert to dataframe for analysis
    df = replay.to_dataframe()

    print(f"Total events: {len(df)}")
    print(f"Duration: {(df['ts_ns'].max() - df['ts_ns'].min()) / 1e9:.2f} seconds")
    print()

    # Count event types
    if "event" in df.columns:
        print("Event types:")
        event_counts = df["event"].value_counts()
        for event, count in event_counts.head(10).items():
            print(f"  {event}: {count}")
    print()

    # Analyze transport events
    tx_events = df[df["event"] == "transport.tx"] if "event" in df.columns else []
    rx_events = df[df["event"] == "transport.rx"] if "event" in df.columns else []

    print(f"Transport TX: {len(tx_events)} frames")
    print(f"Transport RX: {len(rx_events)} frames")

    # Bus publish events
    bus_events = df[df["event"] == "bus.publish"] if "event" in df.columns else []
    print(f"Bus publishes: {len(bus_events)}")

    if len(bus_events) > 0 and "topic" in df.columns:
        print("\nBus topics:")
        topic_counts = bus_events["topic"].value_counts()
        for topic, count in topic_counts.head(10).items():
            print(f"  {topic}: {count}")


async def replay_session(log_path: str, speed: float = 2.0):
    """Replay a recorded session at specified speed."""

    print()
    print("="*60)
    print("Session Replay")
    print("="*60)
    print(f"Replaying: {log_path}")
    print(f"Speed: {speed}x")
    print()

    replay = SessionReplay(log_path)

    print("Replaying events...")
    event_count = 0

    async for event in replay.replay(speed=speed):
        event_count += 1
        event_type = event.get("event", "unknown")

        # Show interesting events
        if event_type in ["session.start", "session.end", "transport.rx", "transport.tx"]:
            print(f"  {event_type}")

        # Show progress every 100 events
        if event_count % 100 == 0:
            print(f"  ... {event_count} events replayed")

    print(f"\nReplay complete: {event_count} events")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python 08_session_recording.py <port_or_tcp>")
        print("Example: python 08_session_recording.py /dev/ttyUSB0")
        return

    # Record a session
    log_path = await record_session(sys.argv[1], duration=10.0)

    if log_path:
        # Analyze the recording
        await analyze_recording(log_path)

        # Replay at 2x speed
        await replay_session(log_path, speed=2.0)


if __name__ == "__main__":
    asyncio.run(main())
