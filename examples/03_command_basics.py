#!/usr/bin/env python3
"""
Example 03: Command Basics

Demonstrates:
- Sending commands to the ESP32
- Reliable command delivery with ACKs
- Error handling
- Robot state machine (ARM/ACTIVATE/DISARM)

Prerequisites:
- ESP32 connected via USB or TCP

Usage:
    python 03_command_basics.py /dev/ttyUSB0
    python 03_command_basics.py --tcp 192.168.1.100
"""
import asyncio
import sys

from robot_host import Robot


def parse_args():
    """Parse command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python 03_command_basics.py <port>")
        print("       python 03_command_basics.py --tcp <ip_address> [port]")
        print("Examples:")
        print("  python 03_command_basics.py /dev/ttyUSB0")
        print("  python 03_command_basics.py --tcp 192.168.1.100")
        return None

    if sys.argv[1] == "--tcp":
        if len(sys.argv) < 3:
            print("Error: --tcp requires an IP address")
            return None
        host = sys.argv[2]
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 3333
        return {"host": host, "tcp_port": port}
    else:
        return {"port": sys.argv[1], "baudrate": 115200}


async def main():
    conn_args = parse_args()
    if conn_args is None:
        return

    print("="*50)
    print("Command Basics Example")
    print("="*50)

    async with Robot(**conn_args) as robot:
        print(f"Connected to {robot.name}\n")

        # -------------------------------------------------------
        # 1. Robot state machine commands
        # -------------------------------------------------------
        print("1. Robot state machine")

        # Start in safe state
        print("   Ensuring safe baseline...")
        await robot.disarm()
        await asyncio.sleep(0.1)

        # ARM the robot
        print("   Arming robot...")
        success, error = await robot.arm()
        if success:
            print("   Robot ARMED")
        else:
            print(f"   ARM failed: {error}")

        # ACTIVATE the robot
        print("   Activating robot...")
        success, error = await robot.activate()
        if success:
            print("   Robot ACTIVATED - motors enabled")
        else:
            print(f"   ACTIVATE failed: {error}")

        await asyncio.sleep(0.5)

        # DEACTIVATE
        print("   Deactivating robot...")
        success, error = await robot.deactivate()
        if success:
            print("   Robot DEACTIVATED")
        else:
            print(f"   DEACTIVATE failed: {error}")

        # DISARM
        print("   Disarming robot...")
        success, error = await robot.disarm()
        if success:
            print("   Robot DISARMED")
        else:
            print(f"   DISARM failed: {error}")
        print()

        # -------------------------------------------------------
        # 2. Motion command
        # -------------------------------------------------------
        print("2. Motion command (set velocity)")

        # Need to arm first
        await robot.arm()
        await robot.activate()

        success, error = await robot.motion.set_velocity(vx=0.0, omega=0.0)
        if success:
            print("   SET_VEL(0, 0) acknowledged")
        else:
            print(f"   SET_VEL failed: {error}")

        await robot.deactivate()
        await robot.disarm()
        print()

        # -------------------------------------------------------
        # 3. Error handling - invalid state transition
        # -------------------------------------------------------
        print("3. Error handling - invalid state transition")
        # Try to activate without arming (should fail)
        success, error = await robot.activate()
        if success:
            print("   Unexpected success!")
            await robot.deactivate()
        else:
            print(f"   Expected failure: {error}")
        print()

        # -------------------------------------------------------
        # 4. Connection statistics
        # -------------------------------------------------------
        print("4. Connection statistics")
        print(f"   Connected: {robot.is_connected}")
        print(f"   Firmware: {robot.firmware_version}")
        print(f"   Capabilities: {robot.capabilities}")
        print()

        print("All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())
