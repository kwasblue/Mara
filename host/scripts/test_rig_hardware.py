#!/usr/bin/env python3
"""
Test Rig Hardware Validation Script

Tests all hardware components on the test rig via MCP tools:
- Servo (GPIO 18)
- DC Motor (GPIO 25/26/27 via L298N)
- Stepper (GPIO 32/33 via A4988)
- IMU (I2C GPIO 21/22)
- Ultrasonic (GPIO 4 trig, GPIO 5 echo)

Usage:
    python scripts/test_rig_hardware.py [--host 10.0.0.60] [--component servo|motor|stepper|ultrasonic|imu|all]
"""

import asyncio
import argparse
from mara_host.mcp.runtime import MaraRuntime
from mara_host.mcp._generated_tools import dispatch_tool


async def test_servo(runtime: MaraRuntime) -> bool:
    """Test servo by sweeping through range."""
    print("\n=== SERVO TEST ===")
    print("Attaching servo 0 to GPIO 18...")

    result = await dispatch_tool(runtime, "mara_servo_attach", {"servo_id": 0, "pin": 18})
    print(f"  Attach: {result}")

    print("Sweeping 0° → 180° → 0°...")
    for angle in [0, 45, 90, 135, 180, 135, 90, 45, 0]:
        result = await dispatch_tool(runtime, "mara_servo_set", {
            "servo_id": 0, "angle": angle, "duration_ms": 200
        })
        print(f"  {angle}°: {result}")
        await asyncio.sleep(0.3)

    print("Centering servo...")
    await dispatch_tool(runtime, "mara_servo_set", {"servo_id": 0, "angle": 90, "duration_ms": 300})

    print("Detaching servo...")
    await dispatch_tool(runtime, "mara_servo_detach", {"servo_id": 0})

    print("✓ Servo test complete")
    return True


async def test_motor(runtime: MaraRuntime) -> bool:
    """Test DC motor by running forward, reverse, and stopping."""
    print("\n=== DC MOTOR TEST ===")
    print("Motor 0 configured on L298N (ENA=25, IN1=26, IN2=27)")

    print("Running forward at 50%...")
    result = await dispatch_tool(runtime, "mara_motor_set", {"motor_id": 0, "speed": 0.5})
    print(f"  Forward: {result}")
    await asyncio.sleep(1.0)

    print("Running forward at 100%...")
    result = await dispatch_tool(runtime, "mara_motor_set", {"motor_id": 0, "speed": 1.0})
    print(f"  Full forward: {result}")
    await asyncio.sleep(1.0)

    print("Stopping...")
    result = await dispatch_tool(runtime, "mara_motor_stop", {"motor_id": 0})
    print(f"  Stop: {result}")
    await asyncio.sleep(0.5)

    print("Running reverse at 50%...")
    result = await dispatch_tool(runtime, "mara_motor_set", {"motor_id": 0, "speed": -0.5})
    print(f"  Reverse: {result}")
    await asyncio.sleep(1.0)

    print("Stopping...")
    result = await dispatch_tool(runtime, "mara_motor_stop", {"motor_id": 0})
    print(f"  Stop: {result}")

    print("✓ DC Motor test complete")
    return True


async def test_stepper(runtime: MaraRuntime) -> bool:
    """Test stepper by moving forward and back."""
    print("\n=== STEPPER TEST ===")
    print("Stepper 0 configured on A4988 (STEP=32, DIR=33)")

    print("Moving forward 200 steps...")
    result = await dispatch_tool(runtime, "mara_stepper_move", {
        "stepper_id": 0, "steps": 200, "speed": 500
    })
    print(f"  Forward: {result}")
    await asyncio.sleep(1.0)

    print("Moving reverse 200 steps...")
    result = await dispatch_tool(runtime, "mara_stepper_move", {
        "stepper_id": 0, "steps": -200, "speed": 500
    })
    print(f"  Reverse: {result}")
    await asyncio.sleep(1.0)

    print("✓ Stepper test complete")
    return True


async def test_ultrasonic(runtime: MaraRuntime) -> bool:
    """Test ultrasonic sensor by taking distance readings."""
    print("\n=== ULTRASONIC TEST ===")
    print("Attaching ultrasonic 0 (TRIG=4, ECHO=5)...")

    result = await dispatch_tool(runtime, "mara_ultrasonic_attach", {
        "sensor_id": 0, "trig_pin": 4, "echo_pin": 5, "max_distance_cm": 400.0
    })
    print(f"  Attach: {result}")

    print("Taking 5 distance readings...")
    success_count = 0
    for i in range(5):
        result = await dispatch_tool(runtime, "mara_ultrasonic_read", {"sensor_id": 0})
        print(f"  Reading {i+1}: {result}")
        if "FAIL" not in str(result):
            success_count += 1
        await asyncio.sleep(0.5)

    print("Detaching sensor...")
    await dispatch_tool(runtime, "mara_ultrasonic_detach", {"sensor_id": 0})

    if success_count == 0:
        print("✗ Ultrasonic test FAILED - no successful readings (check wiring on echo pin)")
        return False
    print(f"✓ Ultrasonic test complete ({success_count}/5 readings)")
    return True


async def test_imu(runtime: MaraRuntime) -> bool:
    """Test IMU by reading accelerometer and gyroscope data."""
    print("\n=== IMU TEST ===")
    print("Reading IMU (I2C on SDA=21, SCL=22)...")

    print("Taking 5 IMU readings...")
    success_count = 0
    for i in range(5):
        result = await dispatch_tool(runtime, "mara_imu_read", {})
        print(f"  Reading {i+1}: {result}")
        if "FAIL" not in str(result) and "unknown" not in str(result).lower():
            success_count += 1
        await asyncio.sleep(0.5)

    if success_count == 0:
        print("✗ IMU test FAILED - no successful readings (check I2C wiring)")
        return False
    print(f"✓ IMU test complete ({success_count}/5 readings)")
    return True


async def run_tests(host: str, port: int, components: list[str]):
    """Run hardware tests."""
    print(f"Connecting to ESP32 at {host}:{port}...")
    runtime = MaraRuntime(host=host, tcp_port=port)

    # Connect
    result = await dispatch_tool(runtime, "mara_connect", {})
    print(f"Connect: {result}")

    # Arm
    result = await dispatch_tool(runtime, "mara_arm", {})
    print(f"Arm: {result}")

    # Get initial state
    result = await dispatch_tool(runtime, "mara_get_state", {})
    print(f"State: {result}")

    tests = {
        "servo": test_servo,
        "motor": test_motor,
        "stepper": test_stepper,
        "ultrasonic": test_ultrasonic,
        "imu": test_imu,
    }

    results = {}
    for component in components:
        if component in tests:
            try:
                results[component] = await tests[component](runtime)
            except Exception as e:
                print(f"✗ {component} test FAILED: {e}")
                results[component] = False

    # Disarm and disconnect
    print("\n=== CLEANUP ===")
    await dispatch_tool(runtime, "mara_disarm", {})
    await dispatch_tool(runtime, "mara_disconnect", {})

    # Summary
    print("\n" + "=" * 40)
    print("TEST SUMMARY")
    print("=" * 40)
    for component, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {component:12s} {status}")

    return all(results.values())


def main():
    parser = argparse.ArgumentParser(description="Test rig hardware validation")
    parser.add_argument("--host", default="10.0.0.60", help="ESP32 IP address")
    parser.add_argument("--port", type=int, default=3333, help="TCP port")
    parser.add_argument(
        "--component",
        choices=["servo", "motor", "stepper", "ultrasonic", "imu", "all"],
        default="all",
        help="Component to test"
    )
    args = parser.parse_args()

    if args.component == "all":
        components = ["servo", "motor", "stepper", "ultrasonic", "imu"]
    else:
        components = [args.component]

    success = asyncio.run(run_tests(args.host, args.port, components))
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
