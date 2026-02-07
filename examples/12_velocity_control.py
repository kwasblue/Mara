#!/usr/bin/env python3
"""
Velocity Control for Differential Drive Robots

This example shows how to use the VelocityController for
high-rate velocity streaming to differential drive robots.

The VelocityController:
- Uses binary protocol for minimal latency (~9 bytes vs ~50 bytes JSON)
- Is designed for control loops running at 20-100Hz
- Provides immediate velocity commands (fire-and-forget)

Run:
    python examples/12_velocity_control.py
"""

import asyncio
import math
import time
from robot_host import Robot, VelocityController


async def basic_velocity_control():
    """Basic velocity control example."""
    print("\n=== Basic Velocity Control ===\n")

    async with Robot("/dev/cu.usbserial-0001") as robot:
        await robot.arm()
        await robot.activate()

        vel = VelocityController(robot)

        # Drive forward
        print("Driving forward...")
        await vel.set(vx=0.3, omega=0.0)  # 0.3 m/s forward
        await asyncio.sleep(2.0)

        # Turn in place
        print("Turning...")
        await vel.set(vx=0.0, omega=0.5)  # 0.5 rad/s turn
        await asyncio.sleep(2.0)

        # Arc motion
        print("Arc motion...")
        await vel.set(vx=0.2, omega=0.3)  # Forward while turning
        await asyncio.sleep(2.0)

        # Stop
        print("Stopping...")
        await vel.stop()

        await robot.deactivate()
        await robot.disarm()


async def high_rate_control_loop():
    """
    High-rate control loop example.

    This simulates a control loop running at 50Hz,
    which is typical for velocity control.
    """
    print("\n=== High-Rate Control Loop (50Hz) ===\n")

    async with Robot("/dev/cu.usbserial-0001") as robot:
        await robot.arm()
        await robot.activate()

        vel = VelocityController(robot)

        # Control parameters
        LOOP_HZ = 50
        DURATION = 5.0  # seconds

        iterations = int(DURATION * LOOP_HZ)
        start_time = time.monotonic()

        print(f"Running {LOOP_HZ}Hz control loop for {DURATION}s...")
        print("Robot will execute a figure-8 pattern\n")

        for i in range(iterations):
            # Calculate time
            t = i / LOOP_HZ

            # Figure-8 pattern
            # Varying forward speed and turn rate sinusoidally
            vx = 0.2 + 0.1 * math.sin(2 * math.pi * t / 2)  # Varies 0.1-0.3 m/s
            omega = 0.5 * math.sin(2 * math.pi * t / 1)  # Varies -0.5 to 0.5 rad/s

            await vel.set(vx, omega)

            # Maintain loop rate
            elapsed = time.monotonic() - start_time
            target_time = (i + 1) / LOOP_HZ
            sleep_time = target_time - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        # Stop
        await vel.stop()

        elapsed = time.monotonic() - start_time
        actual_hz = iterations / elapsed
        print(f"Completed {iterations} iterations in {elapsed:.2f}s ({actual_hz:.1f}Hz)")

        await robot.deactivate()
        await robot.disarm()


async def teleop_simulation():
    """
    Simulated teleoperation example.

    In a real application, you would get joystick values
    from a gamepad or similar input device.
    """
    print("\n=== Teleop Simulation ===\n")

    async with Robot("/dev/cu.usbserial-0001") as robot:
        await robot.arm()
        await robot.activate()

        vel = VelocityController(robot)

        # Teleoperation parameters
        MAX_SPEED = 0.5  # m/s
        MAX_TURN_RATE = 1.0  # rad/s

        print("Simulating joystick input for 10 seconds...")
        print("(In practice, you'd read from a real joystick)\n")

        start = time.monotonic()
        while time.monotonic() - start < 10.0:
            # Simulate joystick input (replace with real input)
            t = time.monotonic() - start
            joystick_y = math.sin(t * 0.5)  # Forward/backward
            joystick_x = math.sin(t * 0.3) * 0.5  # Turn

            # Map to velocity commands
            vx = joystick_y * MAX_SPEED
            omega = joystick_x * MAX_TURN_RATE

            # Dead zone
            if abs(vx) < 0.05:
                vx = 0.0
            if abs(omega) < 0.05:
                omega = 0.0

            await vel.set(vx, omega)

            # Update at 20Hz
            await asyncio.sleep(0.05)

        await vel.stop()
        await robot.deactivate()
        await robot.disarm()

        print("Teleop simulation complete")


async def main():
    """Run examples."""
    # Uncomment the example you want to run:

    await basic_velocity_control()
    # await high_rate_control_loop()
    # await teleop_simulation()


if __name__ == "__main__":
    asyncio.run(main())
