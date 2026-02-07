#!/usr/bin/env python3
"""
Building a Custom Robot Class

This example shows how to build your own robot abstraction
on top of the robot_host library. This is the recommended
pattern for organizing your robot code.

The key idea: robot_host provides building blocks (Robot, Stepper, Servo, etc.)
and YOU create the high-level abstraction for YOUR specific robot.

Run:
    python examples/10_custom_robot.py
"""

import asyncio
from robot_host import Robot, Stepper, Servo, Encoder


class PillDispenser:
    """
    A pill dispenser robot with a stepper-driven carousel.

    This is YOUR robot class - it encapsulates the specific
    hardware configuration and provides a domain-specific API.
    """

    def __init__(self, robot: Robot, slots: int = 5):
        self.robot = robot
        self.slots = slots

        # Hardware configuration
        self.carousel = Stepper(robot, motor_id=0, steps_per_rev=200)
        self.steps_per_slot = self.carousel.steps_per_rev // slots

        # State
        self.current_slot = 0

    async def initialize(self):
        """Set up the dispenser for operation."""
        await self.robot.arm()
        await self.carousel.enable()
        print(f"PillDispenser initialized with {self.slots} slots")

    async def shutdown(self):
        """Clean shutdown."""
        await self.carousel.disable()
        await self.robot.disarm()
        print("PillDispenser shut down")

    async def home(self):
        """Move to slot 0 (home position)."""
        await self.goto_slot(0)

    async def goto_slot(self, slot: int):
        """
        Move to a specific slot.

        Args:
            slot: Target slot (0 to slots-1)
        """
        slot = slot % self.slots
        delta = (slot - self.current_slot) % self.slots

        if delta > 0:
            steps = delta * self.steps_per_slot
            print(f"Moving from slot {self.current_slot} to slot {slot} ({steps} steps)")
            await self.carousel.move(steps, speed_rps=0.5)
            self.current_slot = slot

    async def dispense(self, count: int = 1):
        """
        Dispense pills.

        Args:
            count: Number of pills to dispense
        """
        print(f"Dispensing {count} pill(s)...")

        for i in range(count):
            # Move to next slot
            next_slot = (self.current_slot + 1) % self.slots
            await self.goto_slot(next_slot)

            # Wait for pill to drop
            await asyncio.sleep(0.5)

            print(f"  Dispensed pill {i + 1}/{count}")

        print("Dispensing complete")

    async def full_rotation(self):
        """Spin the carousel one full rotation (for testing)."""
        print("Full rotation test...")
        await self.carousel.move_revolutions(1.0, speed_rps=0.25)


class RobotArm:
    """
    A 3-DOF robot arm with servo joints.

    Another example of a custom robot class.
    """

    def __init__(self, robot: Robot):
        self.robot = robot

        # Hardware configuration - 3 servos for shoulder, elbow, wrist
        self.shoulder = Servo(robot, servo_id=0, channel=0)
        self.elbow = Servo(robot, servo_id=1, channel=1)
        self.wrist = Servo(robot, servo_id=2, channel=2)

    async def initialize(self):
        """Attach all servos and move to home position."""
        await self.robot.arm()
        await self.shoulder.attach()
        await self.elbow.attach()
        await self.wrist.attach()
        await self.home()
        print("RobotArm initialized")

    async def shutdown(self):
        """Return to home and detach."""
        await self.home()
        await self.shoulder.detach()
        await self.elbow.detach()
        await self.wrist.detach()
        await self.robot.disarm()
        print("RobotArm shut down")

    async def home(self):
        """Move all joints to home position."""
        await asyncio.gather(
            self.shoulder.set_angle(90),
            self.elbow.set_angle(90),
            self.wrist.set_angle(90),
        )

    async def move_to(self, shoulder: float, elbow: float, wrist: float, duration_ms: int = 500):
        """
        Move all joints to specified angles.

        Args:
            shoulder: Shoulder angle (degrees)
            elbow: Elbow angle (degrees)
            wrist: Wrist angle (degrees)
            duration_ms: Transition time
        """
        await asyncio.gather(
            self.shoulder.set_angle(shoulder, duration_ms=duration_ms),
            self.elbow.set_angle(elbow, duration_ms=duration_ms),
            self.wrist.set_angle(wrist, duration_ms=duration_ms),
        )

    async def pick_position(self):
        """Move to pick-up position."""
        await self.move_to(45, 135, 90)

    async def place_position(self):
        """Move to place position."""
        await self.move_to(135, 45, 90)


async def demo_pill_dispenser():
    """Demonstrate the pill dispenser."""
    print("\n=== Pill Dispenser Demo ===\n")

    async with Robot("/dev/cu.usbserial-0001") as robot:
        dispenser = PillDispenser(robot, slots=5)

        await dispenser.initialize()

        # Dispense 3 pills
        await dispenser.dispense(3)

        # Return home
        await dispenser.home()

        await dispenser.shutdown()


async def demo_robot_arm():
    """Demonstrate the robot arm."""
    print("\n=== Robot Arm Demo ===\n")

    async with Robot("/dev/cu.usbserial-0001") as robot:
        arm = RobotArm(robot)

        await arm.initialize()

        # Pick and place sequence
        print("Moving to pick position...")
        await arm.pick_position()
        await asyncio.sleep(1.0)

        print("Moving to place position...")
        await arm.place_position()
        await asyncio.sleep(1.0)

        await arm.shutdown()


async def main():
    """Run demos."""
    # Uncomment the demo you want to run:

    await demo_pill_dispenser()
    # await demo_robot_arm()


if __name__ == "__main__":
    asyncio.run(main())
