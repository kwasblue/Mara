# mara_host/cli/commands/imu.py
"""IMU sensor direct control commands.

Examples:
    mara imu read                     # Read IMU data once
    mara imu calibrate                # Calibrate accelerometer/gyro bias
    mara imu monitor                  # Continuous IMU data stream
    mara imu set-bias --ax 0.1        # Set manual bias correction
"""

import argparse
import asyncio

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
    print_warning,
)
<<<<<<< HEAD
from mara_host.cli.context import CLIContext, run_with_context
=======
from mara_host.cli.cli_config import get_serial_port as _get_port
>>>>>>> 6ae4738 (	modified:   host/mara_host/cli/cli_config.py)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register IMU control commands."""
    imu_parser = subparsers.add_parser(
        "imu",
        help="IMU sensor control",
        description="Control IMU (accelerometer/gyroscope) sensor",
    )

    imu_sub = imu_parser.add_subparsers(
        dest="imu_cmd",
        title="imu commands",
        metavar="<subcommand>",
    )

    def add_port_arg(parser):
        parser.add_argument(
            "-p", "--port",
            default=_get_port(),
            help="Serial port",
        )

    # imu read
    read_p = imu_sub.add_parser(
        "read",
        help="Read IMU data once",
    )
    read_p.add_argument(
        "--format",
        choices=["table", "json", "raw"],
        default="table",
        help="Output format (default: table)",
    )
    add_port_arg(read_p)
    read_p.set_defaults(func=cmd_imu_read)

    # imu calibrate
    cal_p = imu_sub.add_parser(
        "calibrate",
        help="Calibrate accelerometer and gyroscope bias",
    )
    cal_p.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Number of samples for calibration (default: 100)",
    )
    cal_p.add_argument(
        "--delay",
        type=float,
        default=0.01,
        help="Delay between samples in seconds (default: 0.01)",
    )
    add_port_arg(cal_p)
    cal_p.set_defaults(func=cmd_imu_calibrate)

    # imu set-bias
    bias_p = imu_sub.add_parser(
        "set-bias",
        help="Set manual bias correction values",
    )
    bias_p.add_argument("--ax", type=float, default=0.0, help="Accel X bias")
    bias_p.add_argument("--ay", type=float, default=0.0, help="Accel Y bias")
    bias_p.add_argument("--az", type=float, default=0.0, help="Accel Z bias")
    bias_p.add_argument("--gx", type=float, default=0.0, help="Gyro X bias")
    bias_p.add_argument("--gy", type=float, default=0.0, help="Gyro Y bias")
    bias_p.add_argument("--gz", type=float, default=0.0, help="Gyro Z bias")
    add_port_arg(bias_p)
    bias_p.set_defaults(func=cmd_imu_set_bias)

    # imu monitor
    monitor_p = imu_sub.add_parser(
        "monitor",
        help="Continuously monitor IMU data",
    )
    monitor_p.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help="Update interval in seconds (default: 0.1)",
    )
    monitor_p.add_argument(
        "--compact",
        action="store_true",
        help="Compact single-line output",
    )
    add_port_arg(monitor_p)
    monitor_p.set_defaults(func=cmd_imu_monitor)

    # imu zero
    zero_p = imu_sub.add_parser(
        "zero",
        help="Zero current orientation as reference",
    )
    add_port_arg(zero_p)
    zero_p.set_defaults(func=cmd_imu_zero)

    imu_parser.set_defaults(func=lambda args: cmd_help(imu_parser))


def cmd_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


@run_with_context
async def cmd_imu_read(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Read IMU data."""
    result = await ctx.imu_service.read()

    if result.ok:
        print_info("IMU: read request sent")
        console.print("[dim]Check telemetry stream for IMU data[/dim]")
        if args.format == "table":
            console.print()
            console.print("[bold]Expected data:[/bold]")
            console.print("  Acceleration (ax, ay, az): m/s\u00b2")
            console.print("  Gyroscope (gx, gy, gz): rad/s")
            console.print("  Temperature: \u00b0C")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_imu_calibrate(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Calibrate IMU bias."""
    console.print("[bold cyan]IMU Calibration[/bold cyan]")
    console.print()
    print_warning("Place the robot on a flat, stable surface.")
    console.print("Do not move the robot during calibration.")
    console.print()
    console.print(f"  Samples: {args.samples}")
    console.print(f"  Duration: ~{args.samples * args.delay:.1f}s")
    console.print()

    delay_ms = int(args.delay * 1000)
    result = await ctx.imu_service.calibrate(samples=args.samples, delay_ms=delay_ms)

    if result.ok:
        print_success("IMU calibration started")
        console.print("[dim]Calibration will complete automatically[/dim]")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_imu_set_bias(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set IMU bias manually."""
    console.print("[bold cyan]Setting IMU Bias[/bold cyan]")
    console.print(f"  Accel: [{args.ax:.4f}, {args.ay:.4f}, {args.az:.4f}]")
    console.print(f"  Gyro:  [{args.gx:.4f}, {args.gy:.4f}, {args.gz:.4f}]")
    console.print()

    result = await ctx.imu_service.set_bias(
        ax=args.ax,
        ay=args.ay,
        az=args.az,
        gx=args.gx,
        gy=args.gy,
        gz=args.gz,
    )

    if result.ok:
        print_success("IMU bias set")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1


@run_with_context
async def cmd_imu_monitor(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Monitor IMU continuously."""
    console.print("[bold cyan]Monitoring IMU[/bold cyan]")
    console.print(f"  Interval: {args.interval}s")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    try:
        while True:
            await ctx.imu_service.read()
            if args.compact:
                console.print("[dim]IMU: polling...[/dim]", end="\r")
            else:
                console.print(f"[dim]IMU: read request sent[/dim]")
            await asyncio.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Monitoring stopped[/dim]")

    return 0


@run_with_context
async def cmd_imu_zero(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Zero IMU orientation."""
    result = await ctx.imu_service.zero()

    if result.ok:
        print_success("IMU: orientation zeroed")
        return 0
    else:
        print_error(f"Failed: {result.error}")
        return 1
