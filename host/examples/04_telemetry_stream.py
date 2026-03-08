#!/usr/bin/env python3
"""
Example 04: Telemetry Stream

Demonstrates:
- Subscribing to telemetry events
- Processing IMU, encoder, and motor data
- Using the TelemetryHostModule for structured data
- Real-time data visualization (console)

Prerequisites:
- ESP32 with sensors connected (IMU, encoders, etc.)

Usage:
    python 04_telemetry_stream.py /dev/ttyUSB0
    python 04_telemetry_stream.py tcp:192.168.1.100
"""
import asyncio
import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from mara_host.transport.serial_transport import SerialTransport
from mara_host.transport.tcp_transport import AsyncTcpTransport
from mara_host.command.client import MaraClient
from mara_host.telemetry.host_module import TelemetryHostModule
from mara_host.core.event_bus import EventBus


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
class TelemetryStats:
    """Track telemetry statistics."""
    total_packets: int = 0
    imu_packets: int = 0
    encoder_packets: int = 0
    motor_packets: int = 0
    ultrasonic_packets: int = 0


async def main():
    if len(sys.argv) < 2:
        print("Usage: python 04_telemetry_stream.py <port_or_tcp>")
        return

    transport = create_transport(sys.argv[1])
    bus = EventBus()
    client = MaraClient(transport=transport, bus=bus)

    # Create telemetry module for structured data
    telemetry = TelemetryHostModule(bus)

    stats = TelemetryStats()

    # -------------------------------------------------------
    # Subscribe to individual telemetry topics
    # -------------------------------------------------------

    def on_imu(imu_data):
        stats.imu_packets += 1
        # imu_data contains ax, ay, az, gx, gy, gz
        ax = imu_data.get("ax", 0)
        ay = imu_data.get("ay", 0)
        az = imu_data.get("az", 0)
        gx = imu_data.get("gx", 0)
        gy = imu_data.get("gy", 0)
        gz = imu_data.get("gz", 0)
        print(f"  IMU: accel=({ax:+.2f}, {ay:+.2f}, {az:+.2f}) "
              f"gyro=({gx:+.3f}, {gy:+.3f}, {gz:+.3f})")

    def on_encoder(enc_data):
        stats.encoder_packets += 1
        ticks = enc_data.get("ticks", 0)
        velocity = enc_data.get("velocity", 0)
        print(f"  Encoder: ticks={ticks}, velocity={velocity:.2f}")

    def on_motor(motor_data):
        stats.motor_packets += 1
        pwm = motor_data.get("pwm", 0)
        current = motor_data.get("current", 0)
        print(f"  Motor: pwm={pwm}, current={current:.2f}A")

    def on_ultrasonic(us_data):
        stats.ultrasonic_packets += 1
        distance = us_data.get("distance_cm", 0)
        print(f"  Ultrasonic: {distance:.1f} cm")

    def on_telemetry_raw(data):
        stats.total_packets += 1

    # Subscribe to topics
    bus.subscribe("telemetry.imu", on_imu)
    bus.subscribe("telemetry.encoder0", on_encoder)
    bus.subscribe("telemetry.dc_motor0", on_motor)
    bus.subscribe("telemetry.ultrasonic", on_ultrasonic)
    bus.subscribe("telemetry.raw", on_telemetry_raw)

    print("="*60)
    print("Telemetry Stream Example")
    print("="*60)

    try:
        await client.start()
        print(f"Connected to {client.robot_name}")
        print("Waiting for telemetry data...\n")
        print("(Press Ctrl+C to stop)\n")

        # Enable telemetry on MCU
        await client.send_reliable("CMD_TELEMETRY_ON", {})

        # Monitor for 30 seconds
        duration = 30
        for i in range(duration):
            await asyncio.sleep(1)

            # Show summary every 5 seconds
            if (i + 1) % 5 == 0:
                print(f"\n--- Stats at {i+1}s ---")
                print(f"  Total packets: {stats.total_packets}")
                print(f"  IMU: {stats.imu_packets}")
                print(f"  Encoder: {stats.encoder_packets}")
                print(f"  Motor: {stats.motor_packets}")
                print(f"  Ultrasonic: {stats.ultrasonic_packets}")

                # Show latest telemetry packet
                if telemetry.latest:
                    pkt = telemetry.latest
                    print(f"  Latest packet timestamp: {pkt.timestamp_ms}ms")
                print("-" * 25 + "\n")

        # Disable telemetry
        await client.send_reliable("CMD_TELEMETRY_OFF", {})

    except KeyboardInterrupt:
        print("\nStopped by user")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Final stats
        print("\n" + "="*60)
        print("Final Telemetry Statistics")
        print("="*60)
        print(f"  Total packets received: {stats.total_packets}")
        print(f"  IMU packets: {stats.imu_packets}")
        print(f"  Encoder packets: {stats.encoder_packets}")
        print(f"  Motor packets: {stats.motor_packets}")
        print(f"  Ultrasonic packets: {stats.ultrasonic_packets}")

        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
