# mara_host/cli/commands/calibrate/imu.py
"""IMU calibration wizard."""

import argparse
import asyncio

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Confirm
from rich.table import Table

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
    print_warning,
)
from ._common import create_client_from_args


def cmd_imu(args: argparse.Namespace) -> int:
    """Calibrate IMU."""
    console.print()
    console.print("[bold cyan]IMU Calibration[/bold cyan]")
    console.print()
    console.print("This wizard will calibrate gyroscope and accelerometer offsets.")
    console.print()
    console.print("[yellow]Important:[/yellow] Place the robot on a flat, stable surface")
    console.print("and keep it completely still during calibration.")
    console.print()

    if not Confirm.ask("Ready to begin?", default=True):
        return 0

    return asyncio.run(_calibrate_imu(args))


async def _calibrate_imu(args: argparse.Namespace) -> int:
    """Run IMU calibration."""
    client = create_client_from_args(args)

    accel_samples = []
    gyro_samples = []

    def on_telemetry(data):
        if isinstance(data, dict) and "imu" in data:
            imu = data["imu"]
            accel_samples.append((imu.get("ax", 0), imu.get("ay", 0), imu.get("az", 0)))
            gyro_samples.append((imu.get("gx", 0), imu.get("gy", 0), imu.get("gz", 0)))

    client.bus.subscribe("telemetry", on_telemetry)

    try:
        await client.start()
        print_success("Connected")
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    try:
        console.print()
        print_info("Collecting samples... Keep the robot still!")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Sampling IMU...", total=100)

            for i in range(100):
                progress.update(task, advance=1, description=f"Sampling IMU... ({len(accel_samples)} samples)")
                await asyncio.sleep(0.05)

        if len(accel_samples) < 10:
            print_warning("Not enough samples received. Check telemetry settings.")
            return 1

        # Calculate averages
        ax_avg = sum(s[0] for s in accel_samples) / len(accel_samples)
        ay_avg = sum(s[1] for s in accel_samples) / len(accel_samples)
        az_avg = sum(s[2] for s in accel_samples) / len(accel_samples)

        gx_avg = sum(s[0] for s in gyro_samples) / len(gyro_samples)
        gy_avg = sum(s[1] for s in gyro_samples) / len(gyro_samples)
        gz_avg = sum(s[2] for s in gyro_samples) / len(gyro_samples)

        # Accelerometer should read ~(0, 0, 1g) when flat
        # Gyroscope should read ~(0, 0, 0) when still

        console.print()
        console.print("[bold cyan]Calibration Results[/bold cyan]")
        console.print()

        table = Table(show_header=True)
        table.add_column("Axis")
        table.add_column("Accel Offset")
        table.add_column("Gyro Offset")

        table.add_row("X", f"{ax_avg:.4f}", f"{gx_avg:.2f}")
        table.add_row("Y", f"{ay_avg:.4f}", f"{gy_avg:.2f}")
        table.add_row("Z", f"{az_avg - 1.0:.4f} (gravity adjusted)", f"{gz_avg:.2f}")

        console.print(table)
        console.print()

        print_info("Add to your robot configuration:")
        console.print(f"""
[dim]imu:
  accel_offset: [{ax_avg:.4f}, {ay_avg:.4f}, {az_avg - 1.0:.4f}]
  gyro_offset: [{gx_avg:.2f}, {gy_avg:.2f}, {gz_avg:.2f}][/dim]
""")

    finally:
        await client.stop()

    return 0
