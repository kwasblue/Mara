# mara_host/benchmarks/commands/send_all/cli.py
"""CLI argument parsing and entry points."""
from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from typing import Dict, List

from .commands import (
    ALL_COMMANDS,
    DISRUPTIVE_COMMANDS,
    MOTION_COMMANDS,
    NO_PAYLOAD_OK,
    REQUIRES_IDLE,
    REQUIRES_PAYLOAD,
    get_command_category,
)


def build_argparser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    p = argparse.ArgumentParser(description="Send all available commands to the MCU and record ACK + latency.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--serial", help="Serial port, e.g. /dev/cu.usbserial-0001")
    g.add_argument("--tcp", help="TCP target HOST:PORT, e.g. 10.0.0.60:3333")

    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--payloads", help="JSON file mapping CMD_* -> payload dict (or list[dict])")
    p.add_argument("--only", help="Comma-separated list of commands to run")
    p.add_argument("--skip", help="Comma-separated list of commands to skip")

    p.add_argument("--delay-ms", type=int, default=80, help="Base delay between commands")
    p.add_argument("--control-delay-ms", type=int, default=200, help="Extra delay after CONTROL commands")

    p.add_argument("--retries", type=int, default=2, help="Retries per payload item")
    p.add_argument("--cmd-timeout", type=float, default=2.5, help="General command timeout")
    p.add_argument("--control-timeout", type=float, default=8.0, help="Timeout to use for control commands")
    p.add_argument("--io-timeout", type=float, default=0.25)

    p.add_argument("--unsafe-motion", action="store_true", help="Allow motion commands to be sent")

    p.add_argument("--transport", help="Optional explicit transport class (module:Class or module.Class).")

    p.add_argument("--probe-control", action="store_true", default=True,
                   help="Probe control module early; if unresponsive, skip control commands (default: on).")
    p.add_argument("--no-probe-control", action="store_false", dest="probe_control",
                   help="Disable control module probing.")

    p.add_argument("--soft-skip-control-noack", action="store_true", default=True,
                   help="Treat CONTROL CLEARED/CANCELLED as SKIP unless forced via --only (default: on).")
    p.add_argument("--no-soft-skip-control-noack", action="store_false", dest="soft_skip_control_noack",
                   help="Disable soft-skip for CONTROL no-ack-like errors.")

    p.add_argument("--out", default="logs/artifacts/send_all_commands_results")

    p.add_argument("--list-commands", action="store_true", help="List all available commands and exit")
    p.add_argument("--category",
                   help="Filter by category: safety, rates, control, gpio, pwm, servo, stepper, encoder, dc, telem, logging, motion, led, ultrasonic")
    return p


def list_commands() -> None:
    """Print all available commands grouped by category."""
    by_category: Dict[str, List[str]] = defaultdict(list)
    for cmd in ALL_COMMANDS:
        by_category[get_command_category(cmd)].append(cmd)

    print("\n" + "=" * 60)
    print("AVAILABLE COMMANDS")
    print("=" * 60)

    for cat in sorted(by_category.keys()):
        cmds = by_category[cat]
        print(f"\n[{cat.upper()}] ({len(cmds)} commands)")
        print("-" * 40)
        for cmd in sorted(cmds):
            flags = []
            if cmd in MOTION_COMMANDS:
                flags.append("motion")
            if cmd in DISRUPTIVE_COMMANDS:
                flags.append("disruptive")
            if cmd in REQUIRES_PAYLOAD:
                flags.append("needs payload")
            if cmd in REQUIRES_IDLE:
                flags.append("idle only")
            if cmd in NO_PAYLOAD_OK:
                flags.append("no payload ok")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            print(f"  {cmd}{flag_str}")

    print(f"\nTotal: {len(ALL_COMMANDS)} commands")
    print("=" * 60 + "\n")


def main() -> None:
    """Main entry point."""
    from .run import run
    args = build_argparser().parse_args()
    raise SystemExit(asyncio.run(run(args)))
