#!/usr/bin/env python3
"""
Upload an IMU→servo control graph and monitor it live.

Usage:
    cd host
    python scripts/monitor_control_graph.py --port /dev/ttyUSB0 --pin 18
    python scripts/monitor_control_graph.py --port /dev/ttyUSB0 --pin 18 --graph examples/control_graphs/imu_pitch_servo_safe.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import time
from pathlib import Path

from mara_host.cli.context import CLIContext
from mara_host.services.control.imu_service import ImuService

DEFAULT_GRAPH = Path(__file__).parent.parent / "examples" / "control_graphs" / "imu_pitch_servo_safe.json"
DEFAULT_PIN = 18
POLL_INTERVAL = 0.5  # seconds between status polls


def _resolve_graph_path(graph_arg: str) -> Path:
    """Resolve graph path, handling various user input formats."""
    graph_path = Path(graph_arg)

    # If it exists as given, use it
    if graph_path.exists():
        return graph_path

    # If starts with "/" but doesn't exist, try as project-relative
    # e.g., "/examples/..." -> "examples/..." relative to script parent
    if graph_arg.startswith("/"):
        project_relative = Path(__file__).parent.parent / graph_arg.lstrip("/")
        if project_relative.exists():
            return project_relative

    # Try relative to script's parent directory (host/)
    script_relative = Path(__file__).parent.parent / graph_arg
    if script_relative.exists():
        return script_relative

    # Return original path (will fail with helpful error)
    return graph_path


async def run(args: argparse.Namespace) -> int:
    graph_path = _resolve_graph_path(args.graph)
    if not graph_path.exists():
        print(f"ERROR: graph file not found: {args.graph}")
        print(f"  Tried: {graph_path}")
        print(f"  Hint: Use relative path like 'examples/control_graphs/...'")
        return 1

    with open(graph_path) as f:
        graph_config = json.load(f)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    print(f"Connecting to {args.port} ...")

    async with CLIContext(port=args.port) as ctx:
        print("Connected and armed.")

        imu_svc = ImuService(ctx.client)

        # Check IMU
        imu_result = await imu_svc.read()
        if not imu_result.ok or not (imu_result.data or {}).get("online"):
            print(f"WARNING: IMU check failed: {imu_result.error or 'offline'}")
            print("  The graph source will fail with 'source_read_failed' if IMU is not online.")
        else:
            d = imu_result.data
            print(f"IMU online: ax={d['ax']:+.3f} ay={d['ay']:+.3f} az={d['az']:+.3f}")

        # Attach servo before uploading the graph (servo_angle sink needs it)
        print(f"Attaching servo 0 on pin {args.pin} ...")
        attach_result = await ctx.servo_service.attach(0, channel=args.pin)
        if not attach_result.ok:
            print(f"ERROR: servo attach failed: {attach_result.error}")
            return 1
        print("Servo attached.")

        # Disarm to enter IDLE (graph upload requires IDLE)
        print("Disarming to IDLE for graph upload ...")
        disarm_result = await ctx.state_service.disarm()
        if not disarm_result.ok:
            print(f"WARNING: disarm failed: {disarm_result.error}")

        # Upload and apply the graph (applies = upload + enable)
        print(f"Uploading graph: {graph_path.name} ...")
        apply_result = await ctx.control_graph_service.apply(graph_config, enable=True)
        if not apply_result.ok:
            print(f"ERROR: graph apply failed: {apply_result.error}")
            return 1

        data = apply_result.data or {}
        print(f"Graph applied: present={data.get('present')} slots={data.get('slot_count')} enabled={data.get('enabled')}")

        # Re-arm after upload
        print("Re-arming ...")
        arm_result = await ctx.state_service.arm()
        if not arm_result.ok:
            print(f"WARNING: arm failed: {arm_result.error}")
        else:
            print("Armed. Graph is running.")

        print()
        print("Monitoring graph (Ctrl+C to stop):")
        print(f"{'Time':>6}  {'Mode':<10}  {'RunCount':>8}  {'Out>90°':>7}  {'Error':<20}  IMU")
        print("-" * 85)

        last_run_count = 0
        start_time = time.time()

        while not stop_event.is_set():
            now = time.time()
            elapsed = now - start_time

            # Poll graph status
            status_result = await ctx.control_graph_service.status()
            imu_result = await imu_svc.read()

            mode_str = "?"
            run_count = 0
            last_run_age_ms = 0
            slot_error = ""
            imu_str = ""

            output_high = None
            if status_result.ok and status_result.data:
                sd = status_result.data
                slots = sd.get("slots", [])
                if slots:
                    s = slots[0]
                    run_count = s.get("run_count", 0)
                    last_run_ms = s.get("last_run_ms", 0)
                    slot_error = s.get("error", "")
                    output_high = s.get("last_output_high")
                    # last_run_age is time since last run in ms (MCU uptime based)
                    last_run_age_ms = last_run_ms

            if imu_result.ok and imu_result.data:
                d = imu_result.data
                online = d.get("online", False)
                if online:
                    imu_str = f"ax={d['ax']:+.2f} ay={d['ay']:+.2f} az={d['az']:+.2f}"
                else:
                    imu_str = "OFFLINE"
            else:
                imu_str = f"read_err: {imu_result.error}"

            # Get mode from state service
            state_result = await ctx.state_service.get_state()
            if state_result.ok and state_result.data:
                mode_str = state_result.data.get("mode", "?")

            delta = run_count - last_run_count
            run_indicator = f"+{delta:d}" if delta > 0 else "STOPPED"
            last_run_count = run_count

            if slot_error:
                error_display = f"\033[31m{slot_error:<20}\033[0m"
            else:
                error_display = f"{'ok':<20}"

            out_str = "YES" if output_high else ("no" if output_high is False else "?")
            print(
                f"{elapsed:6.1f}s  {mode_str:<10}  {run_count:>8} ({run_indicator:>4})  "
                f"{out_str:>7}  {error_display}  {imu_str}"
            )

            await asyncio.sleep(POLL_INTERVAL)

    print("\nStopped.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload IMU→servo control graph and monitor live",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-p", "--port", default="/dev/ttyUSB0", help="Serial port")
    parser.add_argument("--pin", type=int, default=DEFAULT_PIN, help="Servo signal pin")
    parser.add_argument("--graph", default=str(DEFAULT_GRAPH), help="Control graph JSON file")
    args = parser.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
