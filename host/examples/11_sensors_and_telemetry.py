#!/usr/bin/env python3
"""
Working with Sensors and Telemetry

This example demonstrates how to read sensors and
subscribe to telemetry updates using the mara_host library.

The library provides two patterns for accessing sensor data:
1. Property access - synchronous, returns cached data
2. Callbacks - asynchronous, called when new data arrives

Run:
    python examples/11_sensors_and_telemetry.py
"""

import asyncio
from mara_host import Robot, Encoder, IMU, Ultrasonic, EncoderReading, IMUReading


async def encoder_example():
    """Reading encoder data."""
    print("\n=== Encoder Example ===\n")

    async with Robot("/dev/cu.usbserial-0001") as robot:
        # Create encoder instance
        encoder = Encoder(
            robot,
            encoder_id=0,
            pin_a=32,
            pin_b=33,
            counts_per_rev=400,  # For unit conversion
        )

        # Attach the encoder
        await encoder.attach()
        print("Encoder attached")

        # Subscribe to updates with a callback
        def on_encoder_update(reading: EncoderReading):
            print(f"  Encoder: count={reading.count}, velocity={reading.velocity:.1f}")

        encoder.on_update(on_encoder_update)

        # Set telemetry rate
        await robot.set_telemetry_interval(100)  # 10Hz

        # Read for a few seconds
        print("Reading encoder for 5 seconds...")
        for _ in range(10):
            await asyncio.sleep(0.5)

            # Property access to cached data
            print(f"  Position: {encoder.count} ticks, {encoder.revolutions:.2f} revs")

        # Reset encoder count
        await encoder.reset()
        print("Encoder reset to zero")


async def imu_example():
    """Reading IMU data."""
    print("\n=== IMU Example ===\n")

    async with Robot("/dev/cu.usbserial-0001") as robot:
        # Create IMU instance
        imu = IMU(robot)

        # Subscribe to updates
        def on_imu_update(reading: IMUReading):
            print(
                f"  IMU: roll={reading.roll_deg:6.1f}°, "
                f"pitch={reading.pitch_deg:6.1f}°, "
                f"temp={reading.temp_c:.1f}°C"
            )

        imu.on_update(on_imu_update)

        # Set telemetry rate
        await robot.set_telemetry_interval(100)  # 10Hz

        print("Reading IMU for 5 seconds...")
        print("Try tilting the robot!\n")

        for _ in range(50):
            await asyncio.sleep(0.1)

            # Property access
            if imu.is_online:
                ax, ay, az = imu.acceleration
                # print(f"  Accel: x={ax:.2f}g, y={ay:.2f}g, z={az:.2f}g")


async def ultrasonic_example():
    """Reading ultrasonic sensor."""
    print("\n=== Ultrasonic Example ===\n")

    async with Robot("/dev/cu.usbserial-0001") as robot:
        # Create ultrasonic sensor
        sensor = Ultrasonic(robot, sensor_id=0)

        # Attach the sensor
        await sensor.attach()
        print("Ultrasonic sensor attached")

        # Subscribe to updates
        sensor.on_update(
            lambda r: print(f"  Distance: {r.distance_cm:.1f} cm")
        )

        # Set telemetry rate
        await robot.set_telemetry_interval(200)  # 5Hz

        print("Reading distance for 5 seconds...")
        print("Move your hand in front of the sensor!\n")

        for _ in range(25):
            await asyncio.sleep(0.2)

            # Property access
            if sensor.is_in_range:
                print(f"  -> {sensor.distance_cm:.1f} cm ({sensor.distance_m:.2f} m)")


async def event_subscription_example():
    """Direct event bus subscription for custom handling."""
    print("\n=== Event Subscription Example ===\n")

    async with Robot("/dev/cu.usbserial-0001") as robot:
        # Subscribe to raw telemetry
        def on_telemetry(data):
            # You get the full telemetry packet
            ts = data.get("ts_ms", 0)
            print(f"  Telemetry at {ts}ms: {list(data.keys())}")

        robot.on("telemetry", on_telemetry)

        # Subscribe to connection events
        robot.on("heartbeat", lambda _: print("  <heartbeat>"))
        robot.on("connection.lost", lambda _: print("  !!! CONNECTION LOST !!!"))

        await robot.set_telemetry_interval(500)  # 2Hz

        print("Listening for events for 5 seconds...\n")
        await asyncio.sleep(5.0)


async def main():
    """Run examples."""
    # Uncomment the examples you want to run:

    await encoder_example()
    # await imu_example()
    # await ultrasonic_example()
    # await event_subscription_example()


if __name__ == "__main__":
    asyncio.run(main())
