# mara_host/cli/commands/calibrate/pid.py
"""PID controller tuning wizard."""

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


def cmd_pid(args: argparse.Namespace) -> int:
    """Test and tune PID controller."""
    motor_id = args.motor_id

    console.print()
    console.print(f"[bold cyan]PID Controller Test - Motor {motor_id}[/bold cyan]")
    console.print()

    if args.sweep:
        console.print("Mode: Parameter Sweep")
        console.print("This will test multiple PID gain combinations.")
    else:
        console.print(f"  Kp: {args.kp}")
        console.print(f"  Ki: {args.ki}")
        console.print(f"  Kd: {args.kd}")
        console.print(f"  Targets: {args.targets}")
        console.print(f"  Hold time: {args.hold}s")

    console.print()
    print_warning("Motor will spin! Make sure wheels are off the ground.")

    if not Confirm.ask("Ready to begin?", default=True):
        return 0

    if args.sweep:
        return asyncio.run(_pid_sweep(args))
    else:
        return asyncio.run(_pid_test(args))


async def _pid_test(args: argparse.Namespace) -> int:
    """Run PID controller test with given gains."""
    client = create_client_from_args(args)
    motor_id = args.motor_id

    # Parse velocity targets
    targets = [float(x.strip()) for x in args.targets.split(",")]

    try:
        await client.start()
        print_success("Connected")
        console.print()

        # Initial motor stop
        print_info("Stopping motor...")
        await client.send_json_cmd("CMD_DC_STOP", {"motor_id": motor_id})
        await asyncio.sleep(0.2)

        # Enable PID
        print_info("Enabling velocity PID...")
        await client.send_json_cmd("CMD_DC_VEL_PID_ENABLE", {
            "motor_id": motor_id,
            "enable": True
        })
        await asyncio.sleep(0.2)

        # Set gains
        console.print(f"  Setting gains: Kp={args.kp}, Ki={args.ki}, Kd={args.kd}")
        await client.send_json_cmd("CMD_DC_SET_VEL_GAINS", {
            "motor_id": motor_id,
            "kp": args.kp,
            "ki": args.ki,
            "kd": args.kd,
        })
        await asyncio.sleep(0.2)

        # Step through targets
        console.print()
        console.print("[bold]Stepping through velocity targets:[/bold]")

        table = Table(show_header=True)
        table.add_column("Step", justify="center")
        table.add_column("Target (rad/s)", justify="right")
        table.add_column("Duration", justify="right")

        for i, omega in enumerate(targets, 1):
            console.print(f"  [{i}/{len(targets)}] Target: {omega:.2f} rad/s")

            await client.send_json_cmd("CMD_DC_SET_VEL_TARGET", {
                "motor_id": motor_id,
                "omega": omega,
            })

            # Hold at target and optionally monitor telemetry
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(f"Holding at {omega:.2f} rad/s...", total=int(args.hold * 10))
                for _ in range(int(args.hold * 10)):
                    progress.advance(task)
                    await asyncio.sleep(0.1)

        # Disable PID and stop
        console.print()
        print_info("Disabling PID and stopping motor...")
        await client.send_json_cmd("CMD_DC_VEL_PID_ENABLE", {
            "motor_id": motor_id,
            "enable": False
        })
        await client.send_json_cmd("CMD_DC_STOP", {"motor_id": motor_id})

        print_success("PID test complete")
        console.print()

        print_info("Observe motor behavior and adjust gains as needed:")
        console.print("""
  [cyan]Oscillation/ringing:[/cyan] Reduce Kp or increase Kd
  [cyan]Slow response:[/cyan] Increase Kp
  [cyan]Steady-state error:[/cyan] Increase Ki
  [cyan]Overshoot:[/cyan] Increase Kd or reduce Kp
""")

    except Exception as e:
        print_error(f"Error: {e}")
        return 1

    finally:
        # Safety: ensure motor is stopped
        try:
            await client.send_json_cmd("CMD_DC_STOP", {"motor_id": motor_id})
        except Exception:
            pass  # Best-effort cleanup, errors intentionally ignored
        await client.stop()

    return 0


async def _pid_sweep(args: argparse.Namespace) -> int:
    """Run PID parameter sweep."""
    client = create_client_from_args(args)
    motor_id = args.motor_id

    # Define sweep parameters
    kp_values = [0.4, 0.8, 1.2, 1.6]
    ki_values = [0.0, 0.1, 0.2]
    kd_values = [0.0, 0.05, 0.1]

    test_target = 4.0  # rad/s
    test_duration = 2.0  # seconds

    try:
        await client.start()
        print_success("Connected")
        console.print()

        # Initial motor stop
        await client.send_json_cmd("CMD_DC_STOP", {"motor_id": motor_id})
        await asyncio.sleep(0.2)

        # Enable PID
        await client.send_json_cmd("CMD_DC_VEL_PID_ENABLE", {
            "motor_id": motor_id,
            "enable": True
        })

        console.print("[bold]Running parameter sweep...[/bold]")
        console.print(f"  Test target: {test_target} rad/s")
        console.print(f"  Test duration: {test_duration}s per combination")
        console.print()

        results = []
        total_tests = len(kp_values) * len(ki_values) * len(kd_values)
        test_num = 0

        for kp in kp_values:
            for ki in ki_values:
                for kd in kd_values:
                    test_num += 1
                    console.print(f"  [{test_num}/{total_tests}] Kp={kp}, Ki={ki}, Kd={kd}")

                    # Set gains
                    await client.send_json_cmd("CMD_DC_SET_VEL_GAINS", {
                        "motor_id": motor_id,
                        "kp": kp,
                        "ki": ki,
                        "kd": kd,
                    })
                    await asyncio.sleep(0.1)

                    # Stop first
                    await client.send_json_cmd("CMD_DC_SET_VEL_TARGET", {
                        "motor_id": motor_id,
                        "omega": 0.0,
                    })
                    await asyncio.sleep(0.3)

                    # Set target and observe
                    await client.send_json_cmd("CMD_DC_SET_VEL_TARGET", {
                        "motor_id": motor_id,
                        "omega": test_target,
                    })
                    await asyncio.sleep(test_duration)

                    # Record result (in a real implementation, you'd record actual velocity)
                    results.append({
                        "kp": kp,
                        "ki": ki,
                        "kd": kd,
                    })

                    # Stop between tests
                    await client.send_json_cmd("CMD_DC_SET_VEL_TARGET", {
                        "motor_id": motor_id,
                        "omega": 0.0,
                    })
                    await asyncio.sleep(0.5)

        # Disable and stop
        await client.send_json_cmd("CMD_DC_VEL_PID_ENABLE", {
            "motor_id": motor_id,
            "enable": False
        })
        await client.send_json_cmd("CMD_DC_STOP", {"motor_id": motor_id})

        console.print()
        print_success(f"Sweep complete - tested {len(results)} combinations")
        console.print()

        print_info("Review which combinations felt most responsive and stable.")
        print_info("Re-run with specific gains: mara calibrate pid --kp <val> --ki <val> --kd <val>")

    except Exception as e:
        print_error(f"Error: {e}")
        return 1

    finally:
        try:
            await client.send_json_cmd("CMD_DC_STOP", {"motor_id": motor_id})
        except Exception:
            pass  # Best-effort cleanup, errors intentionally ignored
        await client.stop()

    return 0
