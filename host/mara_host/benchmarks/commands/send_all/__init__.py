# mara_host/benchmarks/commands/send_all/__init__.py
"""
Send all available commands to the MCU and record ACK + latency.

Upgrades vs previous version (targets your "CLEARED on control" issue):
- ✅ Probe control module first (CMD_CTRL_SIGNALS_LIST) and if it returns
  CLEARED/CANCELLED, mark control module unavailable and SKIP all control cmds.
- ✅ Dependency-aware skipping:
    - If signal define doesn't succeed, skip signal get/set + slot config/enable/reset.
    - If slot config doesn't succeed, skip slot enable/reset (and optionally status/param).
- ✅ Per-call timeout support:
    - If MaraClient.send_reliable supports a timeout argument, pass it.
    - Otherwise, set client command_timeout_s to max(cmd_timeout, control_timeout).
- ✅ Control pacing:
    - Adds --control-delay-ms (extra delay around control commands).
    - Sends a HEARTBEAT recovery ping after CLEARED/CANCELLED before retry.
- ✅ Validation-friendly defaults:
    - soft-skip control no-ack-like errors by default.

Usage:
  python -m mara_host.benchmarks.commands.send_all --serial /dev/cu.usbserial-0001 --baud 115200
  python -m mara_host.benchmarks.commands.send_all --serial /dev/cu.usbserial-0001 --payloads payloads.json
  python -m mara_host.benchmarks.commands.send_all --serial /dev/cu.usbserial-0001 --only CMD_ARM,CMD_DISARM
  python -m mara_host.benchmarks.commands.send_all --serial /dev/cu.usbserial-0001 --category control
"""

# Re-export main entry points
from .cli import main, build_argparser, list_commands
from .run import run
from .client import build_client, warmup_client, send_cmd
from .types import CmdResult, RunContext, Payload, PayloadSpec, PayloadMap
from .commands import (
    ALL_COMMANDS,
    CONTROL_COMMANDS,
    MOTION_COMMANDS,
    DISRUPTIVE_COMMANDS,
    get_command_category,
    filter_commands,
)

__all__ = [
    # Entry points
    "main",
    "build_argparser",
    "list_commands",
    "run",
    # Client
    "build_client",
    "warmup_client",
    "send_cmd",
    # Types
    "CmdResult",
    "RunContext",
    "Payload",
    "PayloadSpec",
    "PayloadMap",
    # Commands
    "ALL_COMMANDS",
    "CONTROL_COMMANDS",
    "MOTION_COMMANDS",
    "DISRUPTIVE_COMMANDS",
    "get_command_category",
    "filter_commands",
]
