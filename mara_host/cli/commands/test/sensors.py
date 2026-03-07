# mara_host/cli/commands/test/sensors.py
"""Sensor test command (IMU, ultrasonic)."""

import argparse
import asyncio

from mara_host.cli.console import (
    console,
    print_success,
)
from ._common import TestResult, print_results, create_client_from_args


def cmd_sensors(args: argparse.Namespace) -> int:
    """Test sensors."""
    console.print()
    console.print("[bold cyan]Sensor Test[/bold cyan]")
    console.print()

    return asyncio.run(_test_sensors(args))


async def _test_sensors(args: argparse.Namespace) -> int:
    """Run sensor test."""
    client = create_client_from_args(args)

    imu_data = {}
    ultrasonic_data = {}

    def on_telemetry(data):
        if isinstance(data, dict):
            if "imu" in data:
                imu_data.update(data["imu"])
            if "ultrasonic" in data:
                for us in data["ultrasonic"]:
                    ultrasonic_data[us.get("id", 0)] = us.get("distance_m", 0)

    client.bus.subscribe("telemetry", on_telemetry)

    try:
        await client.start()
        print_success("Connected - reading sensors")
        console.print()

        # Wait for data
        await asyncio.sleep(2)

        results = []

        # Check IMU
        if imu_data:
            ax = imu_data.get("ax", 0)
            ay = imu_data.get("ay", 0)
            az = imu_data.get("az", 0)
            results.append(TestResult("IMU Accelerometer", True, f"ax={ax:.2f} ay={ay:.2f} az={az:.2f}"))
        else:
            results.append(TestResult("IMU Accelerometer", False, "No data received"))

        # Check ultrasonic
        if ultrasonic_data:
            for us_id, dist in ultrasonic_data.items():
                results.append(TestResult(f"Ultrasonic {us_id}", True, f"Distance: {dist:.2f}m"))
        else:
            results.append(TestResult("Ultrasonic", False, "No data received"))

        print_results(results)

    finally:
        await client.stop()

    return 0
