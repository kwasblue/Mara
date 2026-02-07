#!/usr/bin/env python3
"""
Getting Started with Robot Host

This example demonstrates the basics of connecting to a robot
and controlling actuators using the robot_host library.

Prerequisites:
    - ESP32 running the MCU Host firmware
    - Connected via USB serial or WiFi

Run:
    python examples/00_getting_started.py
"""

import asyncio
from robot_host import Robot, Stepper


async def main():
    # Connect to robot via serial port
    # Replace with your actual port (e.g., "COM3" on Windows)
    async with Robot("/dev/cu.usbserial-0001") as robot:
        print(f"Connected to: {robot.name}")
        print(f"Firmware: {robot.firmware_version}")
        print(f"Capabilities: {robot.capabilities}")

        # Arm the robot (enable actuators)
        ok, error = await robot.arm()
        if not ok:
            print(f"Failed to arm: {error}")
            return

        print("Robot armed!")

        # Create a stepper motor controller
        motor = Stepper(robot, motor_id=0, steps_per_rev=200)

        # Enable the motor
        await motor.enable()
        print("Motor enabled")

        # Move 100 steps at 0.5 revolutions per second
        print("Moving motor...")
        await motor.move(steps=100, speed_rps=0.5)

        # Wait for move to complete
        await asyncio.sleep(1.0)

        # Move back
        print("Moving back...")
        await motor.move(steps=-100, speed_rps=0.5)

        await asyncio.sleep(1.0)

        # Disable motor
        await motor.disable()

        # Disarm robot
        await robot.disarm()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
