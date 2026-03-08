# mara_host/cli/commands/test/commands.py
"""Command validation test."""

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Optional, Any

from mara_host.cli.console import (
    console,
    print_error,
    print_info,
    print_warning,
)
from ._common import TestResult, print_results, create_client_from_args

# Default payloads file location
DEFAULT_PAYLOADS = Path(__file__).parent.parent.parent.parent / "config" / "test_payloads.json"

# Command category mappings
COMMAND_CATEGORY_MAP = {
    "safety": [
        "CMD_HEARTBEAT", "CMD_ARM", "CMD_DISARM", "CMD_ACTIVATE", "CMD_DEACTIVATE",
        "CMD_ESTOP", "CMD_CLEAR_ESTOP", "CMD_STOP", "CMD_SET_MODE",
    ],
    "gpio": [
        # GPIO REGISTER must run before WRITE/READ/TOGGLE, and before LED commands
        "CMD_GPIO_REGISTER_CHANNEL", "CMD_GPIO_WRITE", "CMD_GPIO_READ", "CMD_GPIO_TOGGLE",
        "CMD_LED_ON", "CMD_LED_OFF", "CMD_PWM_SET",
    ],
    "motor": [
        "CMD_DC_SET_SPEED", "CMD_DC_STOP", "CMD_DC_VEL_PID_ENABLE",
        "CMD_DC_SET_VEL_TARGET", "CMD_DC_SET_VEL_GAINS", "CMD_SET_VEL",
    ],
    "servo": [
        "CMD_SERVO_ATTACH", "CMD_SERVO_SET_ANGLE", "CMD_SERVO_DETACH",
    ],
    "stepper": [
        "CMD_STEPPER_ENABLE", "CMD_STEPPER_MOVE_REL", "CMD_STEPPER_STOP",
    ],
    "encoder": [
        "CMD_ENCODER_ATTACH", "CMD_ENCODER_READ", "CMD_ENCODER_RESET",
        "CMD_ULTRASONIC_ATTACH", "CMD_ULTRASONIC_READ",
    ],
    "control": [
        "CMD_GET_IDENTITY", "CMD_GET_RATES", "CMD_CTRL_SET_RATE", "CMD_SAFETY_SET_RATE",
        "CMD_CTRL_SIGNAL_DEFINE", "CMD_CTRL_SIGNAL_SET", "CMD_CTRL_SIGNAL_GET",
        "CMD_CTRL_SIGNAL_DELETE", "CMD_CTRL_SIGNALS_LIST", "CMD_CTRL_SIGNALS_CLEAR",
        "CMD_CTRL_SLOT_CONFIG", "CMD_CTRL_SLOT_ENABLE", "CMD_CTRL_SLOT_RESET",
        "CMD_CTRL_SLOT_STATUS", "CMD_CTRL_SLOT_SET_PARAM", "CMD_CTRL_SLOT_SET_PARAM_ARRAY",
        "CMD_CTRL_SLOT_GET_PARAM",
    ],
    "observer": [
        "CMD_OBSERVER_CONFIG", "CMD_OBSERVER_ENABLE", "CMD_OBSERVER_RESET",
        "CMD_OBSERVER_STATUS", "CMD_OBSERVER_SET_PARAM", "CMD_OBSERVER_SET_PARAM_ARRAY",
    ],
    "telemetry": [
        "CMD_TELEM_SET_INTERVAL", "CMD_TELEM_SET_RATE", "CMD_SET_LOG_LEVEL",
    ],
    "camera": [
        "CMD_CAM_GET_STATUS", "CMD_CAM_GET_CONFIG", "CMD_CAM_CAPTURE_FRAME",
        "CMD_CAM_START_CAPTURE", "CMD_CAM_STOP_CAPTURE", "CMD_CAM_START_RECORDING",
        "CMD_CAM_STOP_RECORDING", "CMD_CAM_SET_RESOLUTION", "CMD_CAM_SET_QUALITY",
        "CMD_CAM_SET_BRIGHTNESS", "CMD_CAM_SET_CONTRAST", "CMD_CAM_SET_SATURATION",
        "CMD_CAM_SET_SHARPNESS", "CMD_CAM_SET_GAIN", "CMD_CAM_SET_EXPOSURE",
        "CMD_CAM_SET_AWB", "CMD_CAM_SET_FLIP", "CMD_CAM_SET_MOTION_DETECTION",
        "CMD_CAM_FLASH", "CMD_CAM_APPLY_PRESET",
    ],
}

# Feature to command prefix mapping (for firmware feature filtering)
FEATURE_COMMAND_MAP = {
    "camera": "CMD_CAM_",
    "dc_motor": "CMD_DC_",
    "servo": "CMD_SERVO_",
    "stepper": "CMD_STEPPER_",
    "encoder": "CMD_ENCODER_",
    "control_kernel": "CMD_CTRL_",
    "signal_bus": "CMD_CTRL_SIGNAL_",
    "gpio": "CMD_GPIO_",
}

# Commands that require armed state
REQUIRES_ARMED = {
    "CMD_ACTIVATE", "CMD_DC_SET_SPEED", "CMD_DC_SET_VEL_TARGET",
    "CMD_SERVO_SET_ANGLE", "CMD_STEPPER_MOVE_REL",
}

# Commands that cause motion (skip by default)
MOTION_COMMANDS = {
    "CMD_ACTIVATE", "CMD_SET_VEL", "CMD_DC_SET_SPEED", "CMD_DC_SET_VEL_TARGET",
    "CMD_SERVO_SET_ANGLE", "CMD_STEPPER_MOVE_REL", "CMD_STEPPER_ENABLE",
    "CMD_CTRL_SLOT_ENABLE",
}

# Disruptive commands (always skip unless forced)
DISRUPTIVE_COMMANDS = {"CMD_ESTOP"}

# Expected failure reasons (not real failures)
EXPECTED_NACK_REASONS = {
    "unknown_command",      # Feature not in firmware
    "not_supported",        # Command exists but not implemented
    "read_failed",          # Hardware not attached (ultrasonic, etc.)
    "not_armed",            # State machine: requires armed state
    "invalid_transition",   # State machine: can't transition from current state
    "not_active",           # State machine: requires active state
    "not_idle",             # State machine: command requires idle state
    "signal_not_found",     # Signal not defined (dependency issue)
    "slot_not_configured",  # Slot not configured (dependency issue)
    "set_param_array_failed",  # PID doesn't support array params (use STATE_SPACE)
    "invalid_channel",      # GPIO channel not configured/supported in firmware
    "None",                 # Null error (usually dependency issue)
}

# Setup commands to run first (before anything else)
SETUP_COMMANDS = ["CMD_CLEAR_ESTOP", "CMD_SET_MODE"]

# Commands that MUST run in IDLE state (before ARM/ACTIVATE)
REQUIRES_IDLE = {
    "CMD_CTRL_SET_RATE", "CMD_SAFETY_SET_RATE", "CMD_TELEM_SET_RATE",
    "CMD_CTRL_SIGNAL_DEFINE", "CMD_CTRL_SLOT_CONFIG", "CMD_OBSERVER_CONFIG",
    # GPIO registration must happen in IDLE state, and WRITE/READ/TOGGLE depend on it
    "CMD_GPIO_REGISTER_CHANNEL", "CMD_GPIO_WRITE", "CMD_GPIO_READ", "CMD_GPIO_TOGGLE",
}

# Commands that depend on signals being defined
REQUIRES_SIGNALS = {
    "CMD_CTRL_SIGNAL_SET", "CMD_CTRL_SIGNAL_GET", "CMD_CTRL_SIGNAL_DELETE",
    "CMD_CTRL_SLOT_CONFIG", "CMD_CTRL_SLOT_ENABLE", "CMD_CTRL_SLOT_RESET",
    "CMD_CTRL_SLOT_STATUS", "CMD_CTRL_SLOT_SET_PARAM", "CMD_CTRL_SLOT_SET_PARAM_ARRAY",
    "CMD_CTRL_SLOT_GET_PARAM",
}

# Teardown commands to run last
TEARDOWN_COMMANDS = ["CMD_STOP", "CMD_DEACTIVATE", "CMD_DISARM"]


def _load_payloads(path: Optional[Path]) -> dict[str, Any]:
    """Load command payloads from JSON file."""
    if path is None:
        path = DEFAULT_PAYLOADS

    if not path.exists():
        print_warning(f"Payloads file not found: {path}")
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Filter out comments
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception as e:
        print_error(f"Failed to load payloads: {e}")
        return {}


def _get_category(cmd: str) -> str:
    """Get category for a command."""
    for cat, cmds in COMMAND_CATEGORY_MAP.items():
        if cmd in cmds:
            return cat
    return "other"


def _get_commands_for_category(category: str, payloads: dict[str, Any]) -> list[str]:
    """Get commands to test for a category."""
    if category == "all":
        # Return all commands from payloads file
        return list(payloads.keys())

    return [cmd for cmd in COMMAND_CATEGORY_MAP.get(category, []) if cmd in payloads]


def _filter_by_features(commands: list[str], features: list[str]) -> tuple[list[str], list[str]]:
    """Filter commands by firmware features. Returns (supported, unsupported)."""
    supported = []
    unsupported = []

    for cmd in commands:
        # Check if command requires a feature not in firmware
        is_supported = True
        for feature, prefix in FEATURE_COMMAND_MAP.items():
            if cmd.startswith(prefix) and feature not in features:
                is_supported = False
                break

        if is_supported:
            supported.append(cmd)
        else:
            unsupported.append(cmd)

    return supported, unsupported


def _reorder_commands(commands: list[str], include_motion: bool) -> list[str]:
    """Reorder commands for proper state machine flow.

    Order:
    1. Setup (CLEAR_ESTOP, SET_MODE)
    2. IDLE-only commands (rate config, signal define, slot config, observer config)
    3. ARM (if motion commands included)
    4. ACTIVATE (if motion commands included)
    5. Everything else
    6. Teardown (STOP, DEACTIVATE, DISARM)
    """
    commands_set = set(commands)

    # Separate into groups
    setup = [c for c in SETUP_COMMANDS if c in commands_set]
    teardown = [c for c in TEARDOWN_COMMANDS if c in commands_set]

    # IDLE-only commands must run before ARM
    idle_only = [c for c in commands if c in REQUIRES_IDLE]

    # ARM/ACTIVATE for motion
    arm_cmds = ["CMD_ARM"] if "CMD_ARM" in commands_set else []
    activate_cmds = ["CMD_ACTIVATE"] if "CMD_ACTIVATE" in commands_set and include_motion else []

    # Everything else (not in setup, teardown, idle-only, or state transitions)
    excluded = set(setup + teardown + idle_only + arm_cmds + activate_cmds + ["CMD_DISARM", "CMD_DEACTIVATE"])
    middle = [c for c in commands if c not in excluded]

    # If we have motion commands that require armed state, ensure ARM comes before them
    has_armed_required = any(c in REQUIRES_ARMED for c in middle)

    if include_motion and has_armed_required:
        # Order: setup -> idle-only -> arm -> activate -> middle -> teardown
        ordered = setup + idle_only + arm_cmds + activate_cmds + middle + teardown
    else:
        # Order: setup -> idle-only -> middle -> teardown (no arm needed)
        ordered = setup + idle_only + middle + teardown

    return ordered


def _is_expected_failure(error: str) -> bool:
    """Check if a NACK reason is expected (not a real failure)."""
    if not error:
        return False
    # Extract the reason from "NACK: reason"
    reason = error.replace("NACK: ", "").strip()
    return reason in EXPECTED_NACK_REASONS


def cmd_commands(args: argparse.Namespace) -> int:
    """Test MCU commands."""
    console.print()
    console.print("[bold cyan]Command Validation Test[/bold cyan]")
    console.print(f"  Category: {args.category}")
    console.print(f"  Timeout: {args.timeout}s")

    payloads_path = args.payloads or DEFAULT_PAYLOADS
    console.print(f"  Payloads: {payloads_path}")
    console.print()

    return asyncio.run(_test_commands(args))


async def _test_commands(args: argparse.Namespace) -> int:
    """Run command validation test."""
    # Load payloads
    payloads = _load_payloads(args.payloads)
    if not payloads:
        print_error("No payloads loaded - cannot run command test")
        return 1

    # Get commands to test
    commands_to_test = _get_commands_for_category(args.category, payloads)
    include_motion = getattr(args, 'unsafe_motion', False)

    # Filter motion commands unless --unsafe-motion
    if not include_motion:
        skipped_motion = [c for c in commands_to_test if c in MOTION_COMMANDS]
        commands_to_test = [c for c in commands_to_test if c not in MOTION_COMMANDS]
        if skipped_motion:
            print_info(f"Skipping {len(skipped_motion)} motion commands (use --unsafe-motion to include)")

    # Always skip disruptive commands
    commands_to_test = [c for c in commands_to_test if c not in DISRUPTIVE_COMMANDS]

    if not commands_to_test:
        print_warning("No commands to test after filtering")
        return 0

    # Create client
    client = create_client_from_args(args)
    results: list[TestResult] = []
    delay_s = getattr(args, 'delay_ms', 50) / 1000.0
    firmware_features: list[str] = []

    try:
        start = time.time()
        await client.start()
        results.append(TestResult(
            "Connection",
            True,
            "Connected",
            (time.time() - start) * 1000,
            status="pass"
        ))

        # Get firmware features from client if available
        if hasattr(client, 'features') and client.features:
            firmware_features = client.features
            console.print(f"  Firmware features: {', '.join(firmware_features)}")

    except Exception as e:
        results.append(TestResult("Connection", False, str(e), status="fail"))
        print_results(results)
        return 1

    # Filter by firmware features
    if firmware_features:
        commands_to_test, unsupported = _filter_by_features(commands_to_test, firmware_features)
        if unsupported:
            print_info(f"Skipping {len(unsupported)} commands (features not in firmware)")
            for cmd in unsupported:
                results.append(TestResult(
                    cmd,
                    False,
                    "Feature not in firmware",
                    0,
                    status="skipped"
                ))

    # Reorder for proper state machine flow
    commands_to_test = _reorder_commands(commands_to_test, include_motion)

    console.print(f"  Testing {len(commands_to_test)} commands")
    console.print()

    # Track if we're armed (for smart state management)
    is_armed = False

    # Group commands by category for display
    current_category = None

    try:
        for cmd_type in commands_to_test:
            # Print category header
            category = _get_category(cmd_type)
            if category != current_category:
                current_category = category
                console.print(f"\n  [cyan]{category.upper()}[/cyan]")

            # Smart state management: ARM before commands that need it
            if cmd_type in REQUIRES_ARMED and not is_armed and include_motion:
                # Send ARM first
                try:
                    ok, _ = await asyncio.wait_for(
                        client.send_reliable("CMD_ARM", {}),
                        timeout=args.timeout
                    )
                    if ok:
                        is_armed = True
                except Exception:
                    pass
                await asyncio.sleep(delay_s)

            # Get payload(s) for this command
            payload_spec = payloads.get(cmd_type, {})

            # Handle list of payloads (e.g., CMD_CTRL_SIGNAL_DEFINE)
            if isinstance(payload_spec, list):
                payload_items = payload_spec
            else:
                payload_items = [payload_spec]

            for payload in payload_items:
                start = time.time()

                try:
                    # Send command using reliable method if available
                    if hasattr(client, 'send_reliable'):
                        ok, error = await asyncio.wait_for(
                            client.send_reliable(cmd_type, payload),
                            timeout=args.timeout
                        )
                        elapsed = (time.time() - start) * 1000

                        if ok:
                            # Track ARM state
                            if cmd_type == "CMD_ARM":
                                is_armed = True
                            elif cmd_type == "CMD_DISARM":
                                is_armed = False

                            results.append(TestResult(
                                cmd_type,
                                True,
                                "ACK OK",
                                elapsed,
                                status="pass"
                            ))
                        else:
                            # Check if this is an expected failure
                            if _is_expected_failure(f"NACK: {error}"):
                                results.append(TestResult(
                                    cmd_type,
                                    False,
                                    f"NACK: {error}",
                                    elapsed,
                                    status="expected"
                                ))
                            else:
                                results.append(TestResult(
                                    cmd_type,
                                    False,
                                    f"NACK: {error}",
                                    elapsed,
                                    status="fail"
                                ))
                    else:
                        # Fall back to JSON command
                        await client.send_json_cmd(cmd_type, payload)
                        await asyncio.sleep(0.1)
                        results.append(TestResult(
                            cmd_type,
                            True,
                            "Sent (no ACK verification)",
                            (time.time() - start) * 1000,
                            status="pass"
                        ))

                except asyncio.TimeoutError:
                    results.append(TestResult(cmd_type, False, "Timeout", status="fail"))
                except Exception as e:
                    results.append(TestResult(cmd_type, False, str(e), status="fail"))

                # Delay between commands
                await asyncio.sleep(delay_s)

        # Cleanup: ensure we disarm at the end
        if is_armed:
            try:
                await client.send_reliable("CMD_DISARM", {})
            except Exception:
                pass

    finally:
        await client.stop()

    # Print results
    print_results(results)

    passed = sum(1 for r in results if r.status == "pass")
    expected = sum(1 for r in results if r.status == "expected")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "fail")

    console.print()
    console.print(f"[bold]Summary:[/bold] {passed} passed, {expected} expected, {skipped} skipped, {failed} failed")

    if failed > 0:
        console.print()
        console.print("[bold red]Unexpected failures:[/bold red]")
        for r in results:
            if r.status == "fail":
                console.print(f"  [red]x[/red] {r.name}: {r.message}")

    # Return success if no unexpected failures
    return 0 if failed == 0 else 1
