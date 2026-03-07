# robot_host/cli/commands/calibrate.py
"""Calibration wizards for MARA CLI."""

import argparse
import asyncio
import time
from typing import Optional

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.table import Table

from robot_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
    print_warning,
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register calibrate commands."""
    cal_parser = subparsers.add_parser(
        "calibrate",
        help="Calibration wizards",
        description="Calibrate motors, encoders, and sensors",
    )

    cal_sub = cal_parser.add_subparsers(
        dest="cal_cmd",
        title="calibration",
        metavar="<component>",
    )

    # Common transport args
    def add_transport_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("-p", "--port", default="/dev/cu.usbserial-0001")
        p.add_argument("--tcp", metavar="HOST", help="Use TCP instead of serial")

    # motor
    motor_p = cal_sub.add_parser(
        "motor",
        help="Calibrate DC motor",
    )
    motor_p.add_argument("motor_id", type=int, nargs="?", default=0, help="Motor ID")
    add_transport_args(motor_p)
    motor_p.set_defaults(func=cmd_motor)

    # encoder
    encoder_p = cal_sub.add_parser(
        "encoder",
        help="Calibrate encoder",
    )
    encoder_p.add_argument("encoder_id", type=int, nargs="?", default=0, help="Encoder ID")
    add_transport_args(encoder_p)
    encoder_p.set_defaults(func=cmd_encoder)

    # imu
    imu_p = cal_sub.add_parser(
        "imu",
        help="Calibrate IMU",
    )
    add_transport_args(imu_p)
    imu_p.set_defaults(func=cmd_imu)

    # servo
    servo_p = cal_sub.add_parser(
        "servo",
        help="Calibrate servo range",
    )
    servo_p.add_argument("servo_id", type=int, nargs="?", default=0, help="Servo ID")
    add_transport_args(servo_p)
    servo_p.set_defaults(func=cmd_servo)

    # wheels
    wheels_p = cal_sub.add_parser(
        "wheels",
        help="Calibrate wheel diameter and base",
    )
    add_transport_args(wheels_p)
    wheels_p.set_defaults(func=cmd_wheels)

    # Default
    cal_parser.set_defaults(func=lambda args: show_calibrations())


def show_calibrations() -> int:
    """Show available calibrations."""
    console.print()
    console.print("[bold cyan]Available Calibrations[/bold cyan]")
    console.print()
    console.print("  [green]motor[/green]    Calibrate DC motor (dead zone, max speed)")
    console.print("  [green]encoder[/green]  Calibrate encoder (ticks per revolution)")
    console.print("  [green]imu[/green]      Calibrate IMU (gyro/accel offsets)")
    console.print("  [green]servo[/green]    Calibrate servo range (min/max angles)")
    console.print("  [green]wheels[/green]   Calibrate wheel diameter and base width")
    console.print()
    console.print("[dim]Usage: mara calibrate <component> [options][/dim]")
    return 0


def cmd_motor(args: argparse.Namespace) -> int:
    """Calibrate DC motor."""
    motor_id = args.motor_id

    console.print()
    console.print(f"[bold cyan]Motor {motor_id} Calibration[/bold cyan]")
    console.print()
    console.print("This wizard will help you find:")
    console.print("  1. Dead zone (minimum PWM to start moving)")
    console.print("  2. Maximum usable speed")
    console.print("  3. Direction verification")
    console.print()

    if not Confirm.ask("Ready to begin?", default=True):
        return 0

    return asyncio.run(_calibrate_motor(args))


async def _calibrate_motor(args: argparse.Namespace) -> int:
    """Run motor calibration."""
    from robot_host.command.client import AsyncRobotClient

    # Create transport
    if args.tcp:
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)

    client = AsyncRobotClient(transport)

    try:
        await client.start()
        print_success("Connected")
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    motor_id = args.motor_id

    try:
        # Arm and set active
        await client.cmd_arm()
        await client.cmd_set_mode("ACTIVE")

        console.print()
        console.print("[bold]Step 1: Finding dead zone[/bold]")
        console.print("[dim]The motor will slowly increase speed until it moves[/dim]")
        console.print()

        dead_zone = 0.0
        for pwm in range(5, 100, 5):
            speed = pwm / 100.0
            await client.cmd_dc_motor_set_speed(motor_id, speed)
            console.print(f"  PWM: {pwm}%", end="\r")
            await asyncio.sleep(0.5)

            if Confirm.ask(f"  PWM {pwm}%: Is the motor moving?", default=False):
                dead_zone = speed
                break

        await client.cmd_dc_motor_set_speed(motor_id, 0)
        print_success(f"Dead zone: {dead_zone * 100:.0f}%")

        console.print()
        console.print("[bold]Step 2: Direction check[/bold]")
        print_info("Motor will run forward briefly")

        await client.cmd_dc_motor_set_speed(motor_id, 0.3)
        await asyncio.sleep(1)
        await client.cmd_dc_motor_set_speed(motor_id, 0)

        inverted = not Confirm.ask("Did the motor spin in the expected direction?", default=True)

        console.print()
        console.print("[bold]Step 3: Maximum speed test[/bold]")
        print_info("Motor will run at full speed briefly")

        if Confirm.ask("Ready for full speed test?", default=True):
            await client.cmd_dc_motor_set_speed(motor_id, 1.0 if not inverted else -1.0)
            await asyncio.sleep(2)
            await client.cmd_dc_motor_set_speed(motor_id, 0)

        # Summary
        console.print()
        console.print("[bold cyan]Calibration Results[/bold cyan]")
        console.print()
        console.print(f"  Motor ID: {motor_id}")
        console.print(f"  Dead zone: {dead_zone * 100:.0f}%")
        console.print(f"  Inverted: {inverted}")
        console.print()

        print_info("Add these to your robot configuration:")
        console.print(f"""
[dim]motors:
  motor_{motor_id}:
    dead_zone: {dead_zone}
    inverted: {str(inverted).lower()}[/dim]
""")

    finally:
        await client.cmd_dc_motor_set_speed(motor_id, 0)
        await client.cmd_disarm()
        await client.stop()

    return 0


def cmd_encoder(args: argparse.Namespace) -> int:
    """Calibrate encoder."""
    encoder_id = args.encoder_id

    console.print()
    console.print(f"[bold cyan]Encoder {encoder_id} Calibration[/bold cyan]")
    console.print()
    console.print("This wizard will help you determine ticks per revolution.")
    console.print()
    console.print("You will need to:")
    console.print("  1. Mark a starting position on the wheel")
    console.print("  2. Rotate the wheel exactly one revolution")
    console.print()

    if not Confirm.ask("Ready to begin?", default=True):
        return 0

    return asyncio.run(_calibrate_encoder(args))


async def _calibrate_encoder(args: argparse.Namespace) -> int:
    """Run encoder calibration."""
    from robot_host.command.client import AsyncRobotClient

    if args.tcp:
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)

    client = AsyncRobotClient(transport)
    encoder_counts = [0]

    def on_telemetry(data):
        if isinstance(data, dict) and "encoders" in data:
            for enc in data["encoders"]:
                if enc.get("id") == args.encoder_id:
                    encoder_counts[0] = enc.get("counts", 0)

    client.bus.subscribe("telemetry", on_telemetry)

    try:
        await client.start()
        print_success("Connected")
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    try:
        console.print()
        console.print("[bold]Step 1: Zero position[/bold]")
        print_info("Mark a starting position on your wheel")

        Prompt.ask("Press Enter when ready")

        start_counts = encoder_counts[0]
        console.print(f"  Starting count: {start_counts}")

        console.print()
        console.print("[bold]Step 2: Rotate one revolution[/bold]")
        print_info("Slowly rotate the wheel exactly one full revolution")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Monitoring encoder...", total=None)

            while True:
                current = encoder_counts[0]
                diff = abs(current - start_counts)
                progress.update(task, description=f"Counts: {current} (diff: {diff})")
                await asyncio.sleep(0.1)

                # Check for Enter key (non-blocking would need special handling)
                # For now, use a simple approach
                try:
                    import sys
                    import select
                    if select.select([sys.stdin], [], [], 0)[0]:
                        sys.stdin.readline()
                        break
                except:
                    await asyncio.sleep(0.5)
                    if Confirm.ask("Done rotating?", default=False):
                        break

        end_counts = encoder_counts[0]
        ticks_per_rev = abs(end_counts - start_counts)

        console.print()
        console.print("[bold cyan]Calibration Results[/bold cyan]")
        console.print()
        console.print(f"  Encoder ID: {args.encoder_id}")
        console.print(f"  Start counts: {start_counts}")
        console.print(f"  End counts: {end_counts}")
        console.print(f"  [green]Ticks per revolution: {ticks_per_rev}[/green]")
        console.print()

        print_info("Add to your robot configuration:")
        console.print(f"""
[dim]encoders:
  encoder_{args.encoder_id}:
    ticks_per_rev: {ticks_per_rev}[/dim]
""")

    finally:
        await client.stop()

    return 0


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
    from robot_host.command.client import AsyncRobotClient

    if args.tcp:
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)

    client = AsyncRobotClient(transport)

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


def cmd_servo(args: argparse.Namespace) -> int:
    """Calibrate servo range."""
    servo_id = args.servo_id

    console.print()
    console.print(f"[bold cyan]Servo {servo_id} Calibration[/bold cyan]")
    console.print()
    console.print("This wizard will help you find the safe operating range.")
    console.print()

    if not Confirm.ask("Ready to begin?", default=True):
        return 0

    return asyncio.run(_calibrate_servo(args))


async def _calibrate_servo(args: argparse.Namespace) -> int:
    """Run servo calibration."""
    from robot_host.command.client import AsyncRobotClient

    if args.tcp:
        from robot_host.transport.tcp_transport import AsyncTcpTransport
        transport = AsyncTcpTransport(host=args.tcp, port=3333)
    else:
        from robot_host.transport.serial_transport import SerialTransport
        transport = SerialTransport(args.port, baudrate=115200)

    client = AsyncRobotClient(transport)

    try:
        await client.start()
        print_success("Connected")
        await client.cmd_arm()
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return 1

    servo_id = args.servo_id

    try:
        # Center servo first
        console.print()
        print_info("Moving servo to center (90 degrees)...")
        await client.cmd_servo_set_angle(servo_id, 90, 500)
        await asyncio.sleep(1)

        # Find minimum
        console.print()
        console.print("[bold]Step 1: Find minimum angle[/bold]")
        print_info("Use arrow keys or enter angles to find minimum safe position")

        min_angle = 0
        current = 90

        while True:
            angle_input = Prompt.ask(f"  Current: {current}. Enter new angle (or 'done')", default="done")
            if angle_input.lower() == "done":
                min_angle = current
                break
            try:
                current = int(angle_input)
                await client.cmd_servo_set_angle(servo_id, current, 200)
                await asyncio.sleep(0.3)
            except ValueError:
                print_error("Enter a number or 'done'")

        # Find maximum
        console.print()
        console.print("[bold]Step 2: Find maximum angle[/bold]")
        await client.cmd_servo_set_angle(servo_id, 90, 500)
        await asyncio.sleep(0.5)

        max_angle = 180
        current = 90

        while True:
            angle_input = Prompt.ask(f"  Current: {current}. Enter new angle (or 'done')", default="done")
            if angle_input.lower() == "done":
                max_angle = current
                break
            try:
                current = int(angle_input)
                await client.cmd_servo_set_angle(servo_id, current, 200)
                await asyncio.sleep(0.3)
            except ValueError:
                print_error("Enter a number or 'done'")

        # Return to center
        await client.cmd_servo_set_angle(servo_id, (min_angle + max_angle) // 2, 500)

        console.print()
        console.print("[bold cyan]Calibration Results[/bold cyan]")
        console.print()
        console.print(f"  Servo ID: {servo_id}")
        console.print(f"  [green]Min angle: {min_angle}[/green]")
        console.print(f"  [green]Max angle: {max_angle}[/green]")
        console.print(f"  Center: {(min_angle + max_angle) // 2}")
        console.print()

        print_info("Add to your robot configuration:")
        console.print(f"""
[dim]servos:
  servo_{servo_id}:
    min_angle: {min_angle}
    max_angle: {max_angle}
    center_angle: {(min_angle + max_angle) // 2}[/dim]
""")

    finally:
        await client.cmd_disarm()
        await client.stop()

    return 0


def cmd_wheels(args: argparse.Namespace) -> int:
    """Calibrate wheel parameters."""
    console.print()
    console.print("[bold cyan]Wheel Calibration[/bold cyan]")
    console.print()
    console.print("This wizard will help you calibrate:")
    console.print("  1. Wheel diameter")
    console.print("  2. Wheel base (distance between wheels)")
    console.print()
    console.print("You will need:")
    console.print("  - A tape measure")
    console.print("  - Clear floor space (~2 meters)")
    console.print()

    if not Confirm.ask("Ready to begin?", default=True):
        return 0

    # Manual measurement approach
    console.print()
    console.print("[bold]Step 1: Measure wheel diameter[/bold]")
    diameter = FloatPrompt.ask("Enter wheel diameter in millimeters", default=65.0)
    diameter_m = diameter / 1000.0

    console.print()
    console.print("[bold]Step 2: Measure wheel base[/bold]")
    print_info("Measure the distance between the center of the two wheels")
    wheel_base = FloatPrompt.ask("Enter wheel base in millimeters", default=150.0)
    wheel_base_m = wheel_base / 1000.0

    # Summary
    console.print()
    console.print("[bold cyan]Calibration Results[/bold cyan]")
    console.print()
    console.print(f"  Wheel diameter: {diameter_m * 1000:.1f} mm ({diameter_m:.4f} m)")
    console.print(f"  Wheel base: {wheel_base_m * 1000:.1f} mm ({wheel_base_m:.4f} m)")
    console.print()

    print_info("Add to your robot configuration:")
    console.print(f"""
[dim]drive:
  wheel_diameter_m: {diameter_m}
  wheel_base_m: {wheel_base_m}[/dim]
""")

    return 0
