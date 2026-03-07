#!/usr/bin/env python3
"""
Example 06: Motor Control

Demonstrates:
- Robot state machine (ARM -> ACTIVATE)
- Setting velocity commands
- Emergency stop (ESTOP)
- Using MotionHostModule
- Velocity ramping

Prerequisites:
- ESP32 with DC motors connected
- Motor driver configured in firmware
- SAFE TESTING ENVIRONMENT (robot may move!)

Usage:
    python 06_motor_control.py /dev/ttyUSB0
    python 06_motor_control.py tcp:192.168.1.100

WARNING: Robot will move! Ensure safe testing environment.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mara_host.transport.serial_transport import SerialTransport
from mara_host.transport.tcp_transport import AsyncTcpTransport
from mara_host.command.client import MaraClient
from mara_host.motor.motion import MotionHostModule
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


async def main():
    if len(sys.argv) < 2:
        print("Usage: python 06_motor_control.py <port_or_tcp>")
        return

    transport = create_transport(sys.argv[1])
    bus = EventBus()
    client = MaraClient(transport=transport, bus=bus)

    print("="*60)
    print("Motor Control Example")
    print("="*60)
    print()
    print("WARNING: Robot will move! Ensure safe testing environment.")
    print("Press Enter to continue or Ctrl+C to abort...")

    try:
        input()
    except KeyboardInterrupt:
        print("Aborted.")
        return

    try:
        await client.start()
        print(f"Connected to {client.robot_name}\n")

        # Create motion module
        motion = MotionHostModule(bus, client)

        # -------------------------------------------------------
        # 1. Safe baseline
        # -------------------------------------------------------
        print("1. Establishing safe baseline")
        await client.ensure_safe_baseline()
        print("   Robot in DISARMED state\n")

        # -------------------------------------------------------
        # 2. ARM and ACTIVATE
        # -------------------------------------------------------
        print("2. Arming and activating robot")

        success, error = await client.arm()
        if not success:
            print(f"   ARM failed: {error}")
            return
        print("   Robot ARMED")

        success, error = await client.activate()
        if not success:
            print(f"   ACTIVATE failed: {error}")
            await client.disarm()
            return
        print("   Robot ACTIVATED - motors ready!")
        print()

        # -------------------------------------------------------
        # 3. Simple velocity command
        # -------------------------------------------------------
        print("3. Simple velocity command")
        print("   Setting vx=0.2 m/s for 2 seconds...")

        await motion.set_velocity(vx=0.2, omega=0.0)
        await asyncio.sleep(2.0)
        await motion.stop()
        print("   Stopped\n")

        await asyncio.sleep(0.5)

        # -------------------------------------------------------
        # 4. Rotation
        # -------------------------------------------------------
        print("4. Rotation test")
        print("   Rotating omega=0.5 rad/s for 2 seconds...")

        await motion.set_velocity(vx=0.0, omega=0.5)
        await asyncio.sleep(2.0)
        await motion.stop()
        print("   Stopped\n")

        await asyncio.sleep(0.5)

        # -------------------------------------------------------
        # 5. Velocity ramping
        # -------------------------------------------------------
        print("5. Velocity ramping")
        print("   Ramping up to 0.3 m/s...")

        for v in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]:
            await motion.set_velocity(vx=v, omega=0.0)
            print(f"   vx = {v:.2f} m/s")
            await asyncio.sleep(0.5)

        print("   Ramping down...")
        for v in [0.25, 0.2, 0.15, 0.1, 0.05, 0.0]:
            await motion.set_velocity(vx=v, omega=0.0)
            print(f"   vx = {v:.2f} m/s")
            await asyncio.sleep(0.5)

        await motion.stop()
        print("   Ramp complete\n")

        await asyncio.sleep(0.5)

        # -------------------------------------------------------
        # 6. Arc motion
        # -------------------------------------------------------
        print("6. Arc motion (combined linear and angular)")
        print("   vx=0.2 m/s, omega=0.3 rad/s for 3 seconds...")

        await motion.set_velocity(vx=0.2, omega=0.3)
        await asyncio.sleep(3.0)
        await motion.stop()
        print("   Stopped\n")

        await asyncio.sleep(0.5)

        # -------------------------------------------------------
        # 7. Emergency stop test
        # -------------------------------------------------------
        print("7. Emergency stop test")
        print("   Starting motion...")
        await motion.set_velocity(vx=0.2, omega=0.0)
        await asyncio.sleep(0.5)

        print("   ESTOP!")
        await motion.estop()
        print("   Robot in ESTOP state\n")

        await asyncio.sleep(0.5)

        # -------------------------------------------------------
        # 8. Recovery from ESTOP
        # -------------------------------------------------------
        print("8. Recovery from ESTOP")
        print("   Clearing ESTOP...")
        await motion.clear_estop()

        print("   Re-activating...")
        await client.activate()

        print("   Brief motion test...")
        await motion.set_velocity(vx=0.1, omega=0.0)
        await asyncio.sleep(1.0)
        await motion.stop()
        print("   Recovery successful!\n")

        # -------------------------------------------------------
        # 9. Deactivate and disarm
        # -------------------------------------------------------
        print("9. Shutdown sequence")
        await client.deactivate()
        print("   Robot DEACTIVATED")

        await client.disarm()
        print("   Robot DISARMED")
        print()

        print("All motor control tests complete!")

    except KeyboardInterrupt:
        print("\n\nInterrupted! Emergency stopping...")
        try:
            await motion.estop()
        except:
            pass

    except Exception as e:
        print(f"\nError: {e}")
        print("Emergency stopping...")
        try:
            await motion.estop()
        except:
            pass

    finally:
        # Always try to safely stop
        try:
            await client.ensure_safe_baseline()
        except:
            pass
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
