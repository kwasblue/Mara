#!/usr/bin/env python3
"""
Example 07: Encoder Feedback

Demonstrates:
- Attaching encoders to pins
- Reading encoder counts
- Computing velocity from encoder ticks
- Using EncoderHostModule
- Real-time feedback display

Prerequisites:
- ESP32 with quadrature encoders connected
- Encoder pins configured

Usage:
    python 07_encoder_feedback.py /dev/ttyUSB0
    python 07_encoder_feedback.py tcp:192.168.1.100

Note: Update encoder pin definitions for your hardware.
"""
import asyncio
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from mara_host.transport.serial_transport import SerialTransport
from mara_host.transport.tcp_transport import AsyncTcpTransport
from mara_host.command.client import MaraClient
from mara_host.sensor.encoder import EncoderHostModule, EncoderDefaults
from mara_host.telemetry.host_module import TelemetryHostModule
from mara_host.core.event_bus import EventBus


# Configure these for your hardware
# Default encoder pins (update for your setup)
ENCODER_A_PIN = 34  # Encoder A channel
ENCODER_B_PIN = 35  # Encoder B channel
COUNTS_PER_REV = 1000  # Encoder counts per revolution


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


@dataclass
class EncoderState:
    """Track encoder state."""
    ticks: int = 0
    velocity: float = 0.0
    last_ticks: int = 0
    last_time: float = 0.0
    updates: int = 0


async def main():
    if len(sys.argv) < 2:
        print("Usage: python 07_encoder_feedback.py <port_or_tcp>")
        return

    transport = create_transport(sys.argv[1])
    bus = EventBus()
    client = MaraClient(transport=transport, bus=bus)

    print("="*60)
    print("Encoder Feedback Example")
    print("="*60)
    print(f"Encoder pins: A={ENCODER_A_PIN}, B={ENCODER_B_PIN}")
    print(f"Counts per revolution: {COUNTS_PER_REV}")
    print()

    encoder_state = EncoderState()
    encoder_state.last_time = time.monotonic()

    # -------------------------------------------------------
    # Track encoder data from telemetry
    # -------------------------------------------------------
    def on_encoder_telemetry(data):
        encoder_state.updates += 1

        new_ticks = data.get("ticks", 0)
        now = time.monotonic()
        dt = now - encoder_state.last_time

        if dt > 0 and encoder_state.last_time > 0:
            # Compute velocity (ticks/sec -> rev/sec)
            delta_ticks = new_ticks - encoder_state.last_ticks
            ticks_per_sec = delta_ticks / dt
            rev_per_sec = ticks_per_sec / COUNTS_PER_REV
            encoder_state.velocity = rev_per_sec

        encoder_state.ticks = new_ticks
        encoder_state.last_ticks = new_ticks
        encoder_state.last_time = now

    bus.subscribe("telemetry.encoder0", on_encoder_telemetry)

    try:
        await client.start()
        print(f"Connected to {client.robot_name}\n")

        # Create encoder module with custom defaults
        defaults = EncoderDefaults(
            encoder_id=0,
            pin_a=ENCODER_A_PIN,
            pin_b=ENCODER_B_PIN,
        )
        encoder = EncoderHostModule(bus, client, defaults)

        # Create telemetry module
        telemetry = TelemetryHostModule(bus)

        # -------------------------------------------------------
        # 1. Attach encoder
        # -------------------------------------------------------
        print("1. Attaching encoder")
        await encoder.attach()
        print(f"   Encoder attached on pins A={ENCODER_A_PIN}, B={ENCODER_B_PIN}\n")

        await asyncio.sleep(0.5)

        # -------------------------------------------------------
        # 2. Reset encoder
        # -------------------------------------------------------
        print("2. Resetting encoder count")
        await encoder.reset()
        print("   Encoder count reset to 0\n")

        await asyncio.sleep(0.2)

        # -------------------------------------------------------
        # 3. Enable telemetry
        # -------------------------------------------------------
        print("3. Enabling telemetry stream")
        await client.send_reliable("CMD_TELEMETRY_ON", {})
        print("   Telemetry enabled\n")

        # -------------------------------------------------------
        # 4. Monitor encoder (spin wheel manually)
        # -------------------------------------------------------
        print("4. Monitoring encoder")
        print("   Rotate the wheel/encoder shaft to see changes")
        print("   (Press Ctrl+C to stop)")
        print()
        print("   Ticks    | Revolutions | Velocity (rev/s)")
        print("   " + "-"*45)

        last_display = 0
        monitor_duration = 30

        for i in range(monitor_duration * 10):  # 10 Hz display
            await asyncio.sleep(0.1)

            # Also request a read (in case telemetry isn't streaming)
            if i % 5 == 0:  # Every 0.5s
                await encoder.read()

            # Display update
            revolutions = encoder_state.ticks / COUNTS_PER_REV
            print(f"\r   {encoder_state.ticks:8d} | {revolutions:+11.3f} | "
                  f"{encoder_state.velocity:+14.3f}   ", end="", flush=True)

            # Show direction indicator
            if encoder_state.velocity > 0.1:
                print(">>", end="", flush=True)
            elif encoder_state.velocity < -0.1:
                print("<<", end="", flush=True)
            else:
                print("  ", end="", flush=True)

        print("\n")

        # -------------------------------------------------------
        # 5. Summary
        # -------------------------------------------------------
        print("5. Summary")
        print(f"   Total encoder updates: {encoder_state.updates}")
        print(f"   Final ticks: {encoder_state.ticks}")
        print(f"   Final revolutions: {encoder_state.ticks / COUNTS_PER_REV:.3f}")
        print()

        # -------------------------------------------------------
        # 6. Disable telemetry
        # -------------------------------------------------------
        print("6. Disabling telemetry")
        await client.send_reliable("CMD_TELEMETRY_OFF", {})
        print("   Done!\n")

    except KeyboardInterrupt:
        print("\n\nStopped by user")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
