"""
Send all available commands to the MCU and record ACK + latency.

Upgrades vs previous version (targets your "CLEARED on control" issue):
- ✅ Probe control module first (CMD_CTRL_SIGNALS_LIST) and if it returns
  CLEARED/CANCELLED, mark control module unavailable and SKIP all control cmds.
- ✅ Dependency-aware skipping:
    - If signal define doesn't succeed, skip signal get/set + slot config/enable/reset.
    - If slot config doesn't succeed, skip slot enable/reset (and optionally status/param).
- ✅ Per-call timeout support:
    - If AsyncRobotClient.send_reliable supports a timeout argument, pass it.
    - Otherwise, set client command_timeout_s to max(cmd_timeout, control_timeout).
- ✅ Control pacing:
    - Adds --control-delay-ms (extra delay around control commands).
    - Sends a HEARTBEAT recovery ping after CLEARED/CANCELLED before retry.
- ✅ Validation-friendly defaults:
    - soft-skip control no-ack-like errors by default.

Usage:
  python -m robot_host.runners.send_all_commands --serial /dev/cu.usbserial-0001 --baud 115200
  python -m robot_host.runners.send_all_commands --serial /dev/cu.usbserial-0001 --payloads payloads.json
  python -m robot_host.runners.send_all_commands --serial /dev/cu.usbserial-0001 --only CMD_ARM,CMD_DISARM
  python -m robot_host.runners.send_all_commands --serial /dev/cu.usbserial-0001 --category control
"""

from __future__ import annotations

import argparse
import asyncio
import ast
import csv
import json
import time
import importlib
import inspect
import contextlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ---- Commands ---------------------------------------------------------------

# Safety / State Machine
CMD_HEARTBEAT = "CMD_HEARTBEAT"
CMD_ARM = "CMD_ARM"
CMD_DISARM = "CMD_DISARM"
CMD_ACTIVATE = "CMD_ACTIVATE"
CMD_DEACTIVATE = "CMD_DEACTIVATE"
CMD_ESTOP = "CMD_ESTOP"
CMD_CLEAR_ESTOP = "CMD_CLEAR_ESTOP"
CMD_STOP = "CMD_STOP"

# Loop Rates
CMD_GET_RATES = "CMD_GET_RATES"
CMD_CTRL_SET_RATE = "CMD_CTRL_SET_RATE"
CMD_SAFETY_SET_RATE = "CMD_SAFETY_SET_RATE"
CMD_TELEM_SET_RATE = "CMD_TELEM_SET_RATE"

# Control Kernel - Slots
CMD_CTRL_SLOT_CONFIG = "CMD_CTRL_SLOT_CONFIG"
CMD_CTRL_SLOT_ENABLE = "CMD_CTRL_SLOT_ENABLE"
CMD_CTRL_SLOT_RESET = "CMD_CTRL_SLOT_RESET"
CMD_CTRL_SLOT_SET_PARAM = "CMD_CTRL_SLOT_SET_PARAM"
CMD_CTRL_SLOT_STATUS = "CMD_CTRL_SLOT_STATUS"

# Control Kernel - Signals
CMD_CTRL_SIGNAL_DEFINE = "CMD_CTRL_SIGNAL_DEFINE"
CMD_CTRL_SIGNAL_SET = "CMD_CTRL_SIGNAL_SET"
CMD_CTRL_SIGNAL_GET = "CMD_CTRL_SIGNAL_GET"
CMD_CTRL_SIGNALS_LIST = "CMD_CTRL_SIGNALS_LIST"

# Legacy / Mode
CMD_SET_MODE = "CMD_SET_MODE"

# Motion
CMD_SET_VEL = "CMD_SET_VEL"

# LED
CMD_LED_ON = "CMD_LED_ON"
CMD_LED_OFF = "CMD_LED_OFF"

# GPIO
CMD_GPIO_WRITE = "CMD_GPIO_WRITE"
CMD_GPIO_READ = "CMD_GPIO_READ"
CMD_GPIO_TOGGLE = "CMD_GPIO_TOGGLE"
CMD_GPIO_REGISTER_CHANNEL = "CMD_GPIO_REGISTER_CHANNEL"

# PWM
CMD_PWM_SET = "CMD_PWM_SET"

# Servo
CMD_SERVO_ATTACH = "CMD_SERVO_ATTACH"
CMD_SERVO_DETACH = "CMD_SERVO_DETACH"
CMD_SERVO_SET_ANGLE = "CMD_SERVO_SET_ANGLE"

# Stepper
CMD_STEPPER_ENABLE = "CMD_STEPPER_ENABLE"
CMD_STEPPER_MOVE_REL = "CMD_STEPPER_MOVE_REL"
CMD_STEPPER_STOP = "CMD_STEPPER_STOP"

# Ultrasonic
CMD_ULTRASONIC_ATTACH = "CMD_ULTRASONIC_ATTACH"
CMD_ULTRASONIC_READ = "CMD_ULTRASONIC_READ"

# Telemetry
CMD_TELEM_SET_INTERVAL = "CMD_TELEM_SET_INTERVAL"

# Logging
CMD_SET_LOG_LEVEL = "CMD_SET_LOG_LEVEL"

# Encoders
CMD_ENCODER_ATTACH = "CMD_ENCODER_ATTACH"
CMD_ENCODER_READ = "CMD_ENCODER_READ"
CMD_ENCODER_RESET = "CMD_ENCODER_RESET"

# DC Motor
CMD_DC_SET_SPEED = "CMD_DC_SET_SPEED"
CMD_DC_STOP = "CMD_DC_STOP"
CMD_DC_VEL_PID_ENABLE = "CMD_DC_VEL_PID_ENABLE"
CMD_DC_SET_VEL_TARGET = "CMD_DC_SET_VEL_TARGET"
CMD_DC_SET_VEL_GAINS = "CMD_DC_SET_VEL_GAINS"


ALL_COMMANDS = [
    # Safety / State Machine
    CMD_HEARTBEAT,
    CMD_ARM,
    CMD_DISARM,
    CMD_ACTIVATE,
    CMD_DEACTIVATE,
    CMD_ESTOP,
    CMD_CLEAR_ESTOP,
    CMD_STOP,

    # Loop Rates
    CMD_GET_RATES,
    CMD_CTRL_SET_RATE,
    CMD_SAFETY_SET_RATE,
    CMD_TELEM_SET_RATE,

    # Control Kernel - Signals
    CMD_CTRL_SIGNAL_DEFINE,
    CMD_CTRL_SIGNAL_SET,
    CMD_CTRL_SIGNAL_GET,
    CMD_CTRL_SIGNALS_LIST,

    # Control Kernel - Slots
    CMD_CTRL_SLOT_CONFIG,
    CMD_CTRL_SLOT_ENABLE,
    CMD_CTRL_SLOT_RESET,
    CMD_CTRL_SLOT_SET_PARAM,
    CMD_CTRL_SLOT_STATUS,

    # Legacy / Mode
    CMD_SET_MODE,

    # Motion
    CMD_SET_VEL,

    # LED
    CMD_LED_ON,
    CMD_LED_OFF,

    # GPIO
    CMD_GPIO_WRITE,
    CMD_GPIO_READ,
    CMD_GPIO_TOGGLE,
    CMD_GPIO_REGISTER_CHANNEL,

    # PWM
    CMD_PWM_SET,

    # Servo
    CMD_SERVO_ATTACH,
    CMD_SERVO_DETACH,
    CMD_SERVO_SET_ANGLE,

    # Stepper
    CMD_STEPPER_ENABLE,
    CMD_STEPPER_MOVE_REL,
    CMD_STEPPER_STOP,

    # Ultrasonic
    CMD_ULTRASONIC_ATTACH,
    CMD_ULTRASONIC_READ,

    # Telemetry
    CMD_TELEM_SET_INTERVAL,

    # Logging
    CMD_SET_LOG_LEVEL,

    # Encoders
    CMD_ENCODER_ATTACH,
    CMD_ENCODER_READ,
    CMD_ENCODER_RESET,

    # DC Motor
    CMD_DC_SET_SPEED,
    CMD_DC_STOP,
    CMD_DC_VEL_PID_ENABLE,
    CMD_DC_SET_VEL_TARGET,
    CMD_DC_SET_VEL_GAINS,
]


MOTION_COMMANDS = {
    CMD_ACTIVATE,
    CMD_SET_VEL,
    CMD_DC_SET_SPEED,
    CMD_DC_SET_VEL_TARGET,
    CMD_SERVO_SET_ANGLE,
    CMD_STEPPER_MOVE_REL,
    CMD_STEPPER_ENABLE,
    CMD_CTRL_SLOT_ENABLE,
}

DISRUPTIVE_COMMANDS = {CMD_ESTOP}

REQUIRES_PAYLOAD = {
    CMD_GPIO_REGISTER_CHANNEL, CMD_GPIO_READ, CMD_GPIO_WRITE, CMD_GPIO_TOGGLE,
    CMD_SET_MODE,
    CMD_SET_VEL,
    CMD_PWM_SET,
    CMD_SERVO_ATTACH, CMD_SERVO_DETACH, CMD_SERVO_SET_ANGLE,
    CMD_STEPPER_ENABLE, CMD_STEPPER_MOVE_REL, CMD_STEPPER_STOP,
    CMD_ULTRASONIC_ATTACH, CMD_ULTRASONIC_READ,
    CMD_ENCODER_ATTACH, CMD_ENCODER_READ, CMD_ENCODER_RESET,
    CMD_DC_SET_SPEED, CMD_DC_STOP, CMD_DC_VEL_PID_ENABLE, CMD_DC_SET_VEL_TARGET, CMD_DC_SET_VEL_GAINS,
    CMD_CTRL_SET_RATE, CMD_SAFETY_SET_RATE, CMD_TELEM_SET_RATE,
    CMD_CTRL_SLOT_CONFIG, CMD_CTRL_SLOT_ENABLE, CMD_CTRL_SLOT_RESET, CMD_CTRL_SLOT_SET_PARAM, CMD_CTRL_SLOT_STATUS,
    CMD_CTRL_SIGNAL_DEFINE, CMD_CTRL_SIGNAL_SET, CMD_CTRL_SIGNAL_GET,
    CMD_TELEM_SET_INTERVAL,
    CMD_SET_LOG_LEVEL,
}

REQUIRES_IDLE = {
    CMD_CTRL_SET_RATE,
    CMD_SAFETY_SET_RATE,
    CMD_TELEM_SET_RATE,
    CMD_CTRL_SIGNAL_DEFINE,
    CMD_CTRL_SLOT_CONFIG,
}

NO_PAYLOAD_OK = {
    CMD_HEARTBEAT,
    CMD_ARM,
    CMD_DISARM,
    CMD_ACTIVATE,
    CMD_DEACTIVATE,
    CMD_ESTOP,
    CMD_CLEAR_ESTOP,
    CMD_STOP,
    CMD_LED_ON,
    CMD_LED_OFF,
    CMD_GET_RATES,
    CMD_CTRL_SIGNALS_LIST,
}

IDLE_ONLY_COMMANDS = set(REQUIRES_IDLE)

SOFT_SKIP_ERRORS = {"no_control_module", "not_supported"}

NO_ACK_LIKE_ERRORS = {"CLEARED", "CANCELLED"}

CONTROL_COMMANDS = {
    CMD_CTRL_SLOT_CONFIG,
    CMD_CTRL_SLOT_ENABLE,
    CMD_CTRL_SLOT_RESET,
    CMD_CTRL_SLOT_SET_PARAM,
    CMD_CTRL_SLOT_STATUS,
    CMD_CTRL_SIGNAL_DEFINE,
    CMD_CTRL_SIGNAL_SET,
    CMD_CTRL_SIGNAL_GET,
    CMD_CTRL_SIGNALS_LIST,
}


# ---- Types ------------------------------------------------------------------

Payload = Dict[str, Any]
PayloadSpec = Union[Payload, List[Payload]]
PayloadMap = Dict[str, PayloadSpec]


# ---- Results ----------------------------------------------------------------

@dataclass
class CmdResult:
    cmd: str
    ok: bool
    skipped: bool
    latency_ms: Optional[float]
    error: Optional[str]
    payload: Payload
    ack: Optional[Dict[str, Any]]


@dataclass
class RunContext:
    control_available: bool = True
    signals_defined_ok: bool = True
    slot_config_ok: bool = True


# ---- Helpers ----------------------------------------------------------------

def parse_hostport(s: str) -> Tuple[str, int]:
    if ":" not in s:
        raise ValueError("Expected HOST:PORT")
    host, port_s = s.rsplit(":", 1)
    return host, int(port_s)


def load_payloads(path: Optional[str]) -> PayloadMap:
    if not path:
        return {}
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("payloads file must be a JSON object mapping CMD_* -> payload")
    out: PayloadMap = {}
    for k, v in data.items():
        if isinstance(v, dict):
            out[k] = v
        elif isinstance(v, list) and all(isinstance(x, dict) for x in v):
            out[k] = v
    return out


def ensure_artifacts_dir() -> Path:
    out_dir = Path("logs/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _import_class(dotted: str):
    if ":" in dotted:
        mod_path, cls_name = dotted.split(":", 1)
    else:
        mod_path, cls_name = dotted.rsplit(".", 1)
    mod = importlib.import_module(mod_path)
    obj = getattr(mod, cls_name)
    if not inspect.isclass(obj):
        raise TypeError(f"{dotted} did not resolve to a class")
    return obj


def _module_name_from_file(pkg_root: Path, py_file: Path, pkg_name: str) -> str:
    rel = py_file.relative_to(pkg_root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([pkg_name, *parts])


def _discover_transport_via_ast(
    pkg_name: str,
    token_sets: List[Tuple[str, ...]],
    exclude_dirs: Optional[set[str]] = None,
) -> Tuple[str, type]:
    import robot_host
    pkg_root = Path(robot_host.__file__).resolve().parent

    if exclude_dirs is None:
        exclude_dirs = {"runners", "tests", "ui", "gui", "scripts", "__pycache__", "modules"}

    candidates: List[Tuple[int, int, str, str, Path]] = []
    for py_file in pkg_root.rglob("*.py"):
        if any(part in exclude_dirs for part in py_file.parts):
            continue
        try:
            src = py_file.read_text(encoding="utf-8")
            tree = ast.parse(src, filename=str(py_file))
        except Exception:
            continue

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            clsname = node.name
            for tokens in token_sets:
                if all(t in clsname for t in tokens):
                    modname = _module_name_from_file(pkg_root, py_file, pkg_name)
                    async_pref = 0 if "Async" in clsname else 1
                    candidates.append((async_pref, len(tokens), modname, clsname, py_file))
                    break

    if not candidates:
        wanted = " OR ".join(["+".join(ts) for ts in token_sets])
        raise RuntimeError(
            f"Could not discover a transport class via AST scan (wanted {wanted}).\n"
            f"Fix: pass --transport with the exact class path (module:Class)."
        )

    candidates.sort(key=lambda t: (t[0], -t[1], len(t[3]), t[3]))
    _, _, modname, clsname, _py = candidates[0]

    mod = importlib.import_module(modname)
    TransportCls = getattr(mod, clsname)
    if not inspect.isclass(TransportCls):
        raise RuntimeError(f"Discovered {modname}.{clsname} but it is not a class")
    return f"{modname}:{clsname}", TransportCls


def _resolve_transport_class(explicit: Optional[str], mode: str) -> Tuple[str, type]:
    if explicit:
        cls = _import_class(explicit)
        return explicit, cls
    if mode == "serial":
        token_sets = [("Async", "Serial", "Transport"), ("Serial", "Transport")]
        return _discover_transport_via_ast("robot_host", token_sets=token_sets)
    if mode == "tcp":
        token_sets = [("Async", "Tcp", "Transport"), ("Tcp", "Transport"), ("Async", "TCP", "Transport"), ("TCP", "Transport")]
        return _discover_transport_via_ast("robot_host", token_sets=token_sets)
    raise ValueError(f"Unknown mode: {mode}")


def _construct_transport(
    TransportCls,
    *,
    serial: Optional[str],
    baud: int,
    io_timeout: float,
    tcp: Optional[str],
) -> Any:
    sig = inspect.signature(TransportCls.__init__)
    params = sig.parameters
    kw: Dict[str, Any] = {}

    if tcp:
        host, port = parse_hostport(tcp)
        for k in ("host", "hostname", "ip", "addr", "address"):
            if k in params:
                kw[k] = host
                break
        for k in ("port", "tcp_port"):
            if k in params:
                kw[k] = port
                break
        for k in ("timeout", "io_timeout", "read_timeout", "write_timeout"):
            if k in params:
                kw[k] = io_timeout
                break
        try:
            return TransportCls(**kw)
        except TypeError:
            try:
                return TransportCls(host, port)
            except TypeError:
                return TransportCls(tcp)

    if not serial:
        raise RuntimeError("serial transport requested but no serial port provided")

    for k in ("port", "device", "path", "serial", "serial_path", "dev"):
        if k in params:
            kw[k] = serial
            break
    for k in ("baud", "baudrate"):
        if k in params:
            kw[k] = baud
            break
    for k in ("timeout", "io_timeout", "read_timeout", "write_timeout"):
        if k in params:
            kw[k] = io_timeout
            break

    try:
        return TransportCls(**kw)
    except TypeError:
        try:
            return TransportCls(serial, baud)
        except TypeError:
            return TransportCls(serial)


def _send_reliable_supports_timeout(client: Any) -> Tuple[bool, Optional[str]]:
    fn = getattr(client, "send_reliable", None)
    if not callable(fn):
        return False, None
    try:
        sig = inspect.signature(fn)
    except Exception:
        return False, None
    params = sig.parameters
    for name in ("timeout_s", "timeout", "command_timeout_s", "cmd_timeout_s"):
        if name in params:
            return True, name
    return False, None


async def build_client(args):
    from robot_host.command.client import AsyncRobotClient

    mode = "tcp" if args.tcp else "serial"
    dotted, TransportCls = _resolve_transport_class(args.transport, mode=mode)
    print(f"[send_all_commands] Using transport: {dotted}")

    transport = _construct_transport(
        TransportCls,
        serial=args.serial,
        baud=args.baud,
        io_timeout=args.io_timeout,
        tcp=args.tcp,
    )

    # IMPORTANT:
    # If we can't pass per-call timeouts, make the client's command timeout big enough
    # for control operations.
    client_cmd_timeout = float(max(args.cmd_timeout, args.control_timeout))

    client = AsyncRobotClient(
        transport=transport,
        heartbeat_interval_s=getattr(args, "heartbeat_interval_s", 0.2),
        connection_timeout_s=getattr(args, "connection_timeout_s", 1.0),
        command_timeout_s=client_cmd_timeout,
        max_retries=1,
        require_version_match=getattr(args, "require_version_match", True),
        handshake_timeout_s=getattr(args, "handshake_timeout_s", 2.0),
    )

    await client.start()
    return client


async def warmup_client(client: Any, delay_s: float = 0.20, n_heartbeats: int = 2) -> None:
    if not hasattr(client, "send_reliable"):
        return

    for _ in range(max(1, int(n_heartbeats))):
        with contextlib.suppress(Exception):
            await client.send_reliable(CMD_HEARTBEAT, {}, wait_for_ack=True)
        await asyncio.sleep(delay_s)

    with contextlib.suppress(Exception):
        await client.send_reliable(CMD_GET_RATES, {}, wait_for_ack=True)
    await asyncio.sleep(delay_s)


async def _recovery_ping(client: Any, delay_s: float = 0.15) -> None:
    if not hasattr(client, "send_reliable"):
        return
    with contextlib.suppress(Exception):
        await client.send_reliable(CMD_HEARTBEAT, {}, wait_for_ack=True)
    await asyncio.sleep(delay_s)


async def send_cmd(client: Any, cmd: str, payload: Payload, timeout_s: float) -> Dict[str, Any]:
    if not hasattr(client, "send_reliable"):
        raise RuntimeError(
            f"Client {type(client).__name__} has no send_reliable(). "
            "Expected robot_host.command.client.AsyncRobotClient."
        )

    supports_timeout, timeout_param = _send_reliable_supports_timeout(client)

    async def _do():
        if supports_timeout and timeout_param:
            kw = {timeout_param: float(timeout_s)}
            ok, err = await client.send_reliable(cmd, payload or {}, wait_for_ack=True, **kw)
        else:
            ok, err = await client.send_reliable(cmd, payload or {}, wait_for_ack=True)
        return {"cmd": cmd, "ok": bool(ok), "error": err}

    # Always add a small cushion over whatever the client is doing.
    return await asyncio.wait_for(_do(), timeout=float(timeout_s) + 0.50)


def ack_is_ok(ack: Any) -> Tuple[bool, Optional[str]]:
    if ack is None:
        return False, "no ack"
    if isinstance(ack, dict):
        if ack.get("ok") is True:
            return True, None
        return False, ack.get("error") or "command failed"
    return True, None


def should_skip_cmd(
    cmd: str,
    *,
    payload_spec: PayloadSpec,
    only_set: Optional[set[str]],
    unsafe_motion: bool,
) -> Optional[str]:
    if only_set is not None and cmd in only_set:
        return None

    if cmd in DISRUPTIVE_COMMANDS:
        return "skipped (disruptive command; use --only to force)"

    if (not unsafe_motion) and (cmd in MOTION_COMMANDS):
        return "skipped (motion command; use --unsafe-motion or --only)"

    if cmd in NO_PAYLOAD_OK:
        return None

    has_payload = bool(payload_spec) if not isinstance(payload_spec, list) else (len(payload_spec) > 0)
    if cmd in REQUIRES_PAYLOAD and not has_payload:
        return "skipped (missing required payload/config)"

    return None


def build_argparser() -> argparse.ArgumentParser:
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


def get_command_category(cmd: str) -> str:
    categories = {
        "safety": {CMD_HEARTBEAT, CMD_ARM, CMD_DISARM, CMD_ACTIVATE, CMD_DEACTIVATE, CMD_ESTOP, CMD_CLEAR_ESTOP, CMD_STOP, CMD_SET_MODE},
        "rates": {CMD_GET_RATES, CMD_CTRL_SET_RATE, CMD_SAFETY_SET_RATE, CMD_TELEM_SET_RATE},
        "control": {CMD_CTRL_SLOT_CONFIG, CMD_CTRL_SLOT_ENABLE, CMD_CTRL_SLOT_RESET, CMD_CTRL_SLOT_SET_PARAM, CMD_CTRL_SLOT_STATUS,
                    CMD_CTRL_SIGNAL_DEFINE, CMD_CTRL_SIGNAL_SET, CMD_CTRL_SIGNAL_GET, CMD_CTRL_SIGNALS_LIST},
        "gpio": {CMD_GPIO_WRITE, CMD_GPIO_READ, CMD_GPIO_TOGGLE, CMD_GPIO_REGISTER_CHANNEL},
        "led": {CMD_LED_ON, CMD_LED_OFF},
        "pwm": {CMD_PWM_SET},
        "servo": {CMD_SERVO_ATTACH, CMD_SERVO_DETACH, CMD_SERVO_SET_ANGLE},
        "stepper": {CMD_STEPPER_ENABLE, CMD_STEPPER_MOVE_REL, CMD_STEPPER_STOP},
        "ultrasonic": {CMD_ULTRASONIC_ATTACH, CMD_ULTRASONIC_READ},
        "encoder": {CMD_ENCODER_ATTACH, CMD_ENCODER_READ, CMD_ENCODER_RESET},
        "dc": {CMD_DC_SET_SPEED, CMD_DC_STOP, CMD_DC_VEL_PID_ENABLE, CMD_DC_SET_VEL_TARGET, CMD_DC_SET_VEL_GAINS},
        "motion": {CMD_SET_VEL},
        "telem": {CMD_TELEM_SET_INTERVAL},
        "logging": {CMD_SET_LOG_LEVEL},
    }
    for cat, cmds in categories.items():
        if cmd in cmds:
            return cat
    return "other"


def filter_commands(cmds: List[str], only: Optional[str], skip: Optional[str], category: Optional[str] = None) -> List[str]:
    only_set = set([c.strip() for c in only.split(",") if c.strip()]) if only else None
    skip_set = set([c.strip() for c in skip.split(",") if c.strip()]) if skip else set()

    out: List[str] = []
    for c in cmds:
        if only_set is not None and c not in only_set:
            continue
        if c in skip_set:
            continue
        if category and get_command_category(c) != category:
            continue
        out.append(c)
    return out


def list_commands() -> None:
    from collections import defaultdict
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


def reorder_state_machine_aware(cmds: List[str], *, only_set: Optional[set[str]], unsafe_motion: bool) -> List[str]:
    cmds_set = set(cmds)

    prelude_order = [CMD_CLEAR_ESTOP, CMD_SET_MODE, CMD_HEARTBEAT, CMD_GET_RATES]
    prelude = [c for c in prelude_order if c in cmds_set]

    idle_rates = [c for c in cmds if c in {CMD_CTRL_SET_RATE, CMD_SAFETY_SET_RATE, CMD_TELEM_SET_RATE}]
    idle_define = [c for c in cmds if c == CMD_CTRL_SIGNAL_DEFINE]
    idle_slotcfg = [c for c in cmds if c == CMD_CTRL_SLOT_CONFIG]
    idle_other = [
        c for c in cmds
        if (c in IDLE_ONLY_COMMANDS and c not in {CMD_CTRL_SET_RATE, CMD_SAFETY_SET_RATE, CMD_TELEM_SET_RATE, CMD_CTRL_SIGNAL_DEFINE, CMD_CTRL_SLOT_CONFIG})
    ]
    idle_only = idle_rates + idle_define + idle_slotcfg + idle_other

    def _allowed_motion_cmd(c: str) -> bool:
        if only_set is not None and c in only_set:
            return True
        return unsafe_motion

    arm_activate = [c for c in (CMD_ARM, CMD_ACTIVATE) if c in cmds_set and _allowed_motion_cmd(c)]
    epilogue = [c for c in (CMD_STOP, CMD_DEACTIVATE, CMD_DISARM) if c in cmds_set]

    staged = set(prelude) | set(idle_only) | set(arm_activate) | set(epilogue)
    middle = [c for c in cmds if c not in staged]

    out = prelude + idle_only + arm_activate + middle + epilogue

    seen = set()
    uniq: List[str] = []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def _payload_items(spec: PayloadSpec) -> List[Payload]:
    if isinstance(spec, list):
        return [p for p in spec if isinstance(p, dict)]
    if isinstance(spec, dict):
        return [spec]
    return []


def _per_cmd_timeout(args, cmd: str) -> float:
    if cmd in CONTROL_COMMANDS:
        return float(max(args.cmd_timeout, args.control_timeout))
    return float(args.cmd_timeout)


def _extra_delay_ms(args, cmd: str) -> int:
    if cmd in CONTROL_COMMANDS:
        return int(args.delay_ms + args.control_delay_ms)
    return int(args.delay_ms)


async def _probe_control_module(client: Any, args, only_set: Optional[set[str]]) -> Tuple[bool, Optional[str]]:
    """
    Returns (control_available, reason_if_not).
    If the user forced control commands via --only, we still report unavailable
    but won't auto-skip them (caller uses only_set).
    """
    if not args.probe_control:
        return True, None

    # Probe only if any control commands are in the run set (or category filter is control).
    # Cheap heuristic: always probe; it's safe and fast when it works.
    timeout_s = float(max(args.cmd_timeout, args.control_timeout))

    try:
        ack = await send_cmd(client, CMD_CTRL_SIGNALS_LIST, {}, timeout_s)
        ok, err = ack_is_ok(ack)
        if ok:
            return True, None
        if err in NO_ACK_LIKE_ERRORS or err in SOFT_SKIP_ERRORS:
            return False, err
        # If it explicitly NACKs with another error, treat as available but "functional error".
        return True, None
    except asyncio.TimeoutError:
        return False, "timeout"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def run(args) -> int:
    if args.list_commands:
        list_commands()
        return 0

    payloads = load_payloads(args.payloads)
    cmds = filter_commands(ALL_COMMANDS, args.only, args.skip, args.category)
    only_set = set([c.strip() for c in args.only.split(",") if c.strip()]) if args.only else None

    cmds = reorder_state_machine_aware(cmds, only_set=only_set, unsafe_motion=args.unsafe_motion)

    ensure_artifacts_dir()
    out_prefix = Path(args.out)
    csv_path = out_prefix.with_suffix(".csv")
    json_path = out_prefix.with_suffix(".json")

    client = await build_client(args)
    await warmup_client(client, delay_s=0.20, n_heartbeats=getattr(args, "warmup_heartbeats", 2))

    ctx = RunContext()
    results: List[CmdResult] = []

    try:
        # ---- Probe control module early (while we're still IDLE)
        control_ok, control_reason = await _probe_control_module(client, args, only_set=only_set)
        if not control_ok:
            ctx.control_available = False
            print(f"[send_all_commands] Control probe: UNAVAILABLE ({control_reason})")

        for cmd in cmds:
            payload_spec: PayloadSpec = payloads.get(cmd, {})

            # ---- Capability skip: control module unavailable
            if (
                (cmd in CONTROL_COMMANDS)
                and (not ctx.control_available)
                and (only_set is None or cmd not in only_set)
            ):
                results.append(
                    CmdResult(
                        cmd=cmd,
                        ok=False,
                        skipped=True,
                        latency_ms=None,
                        error=f"skipped (control module not responding: {control_reason})",
                        payload=_payload_items(payload_spec)[0] if _payload_items(payload_spec) else {},
                        ack=None,
                    )
                )
                await asyncio.sleep(_extra_delay_ms(args, cmd) / 1000.0)
                continue

            # ---- Dependency skip: if signal define failed earlier, skip dependent control ops
            if (cmd in {CMD_CTRL_SIGNAL_SET, CMD_CTRL_SIGNAL_GET, CMD_CTRL_SLOT_CONFIG, CMD_CTRL_SLOT_ENABLE, CMD_CTRL_SLOT_RESET}) and (not ctx.signals_defined_ok):
                if only_set is None or cmd not in only_set:
                    results.append(
                        CmdResult(
                            cmd=cmd,
                            ok=False,
                            skipped=True,
                            latency_ms=None,
                            error="skipped (prereq failed: signals not defined)",
                            payload=_payload_items(payload_spec)[0] if _payload_items(payload_spec) else {},
                            ack=None,
                        )
                    )
                    await asyncio.sleep(_extra_delay_ms(args, cmd) / 1000.0)
                    continue

            # ---- Dependency skip: if slot config failed earlier, skip slot enable/reset
            if (cmd in {CMD_CTRL_SLOT_ENABLE, CMD_CTRL_SLOT_RESET}) and (not ctx.slot_config_ok):
                if only_set is None or cmd not in only_set:
                    results.append(
                        CmdResult(
                            cmd=cmd,
                            ok=False,
                            skipped=True,
                            latency_ms=None,
                            error="skipped (prereq failed: slot not configured)",
                            payload=_payload_items(payload_spec)[0] if _payload_items(payload_spec) else {},
                            ack=None,
                        )
                    )
                    await asyncio.sleep(_extra_delay_ms(args, cmd) / 1000.0)
                    continue

            reason = should_skip_cmd(
                cmd,
                payload_spec=payload_spec,
                only_set=only_set,
                unsafe_motion=args.unsafe_motion,
            )
            if reason:
                results.append(
                    CmdResult(
                        cmd=cmd,
                        ok=False,
                        skipped=True,
                        latency_ms=None,
                        error=reason,
                        payload=_payload_items(payload_spec)[0] if _payload_items(payload_spec) else {},
                        ack=None,
                    )
                )
                await asyncio.sleep(_extra_delay_ms(args, cmd) / 1000.0)
                continue

            items = _payload_items(payload_spec) or [{}]
            timeout_s = _per_cmd_timeout(args, cmd)

            for item in items:
                ok = False
                err: Optional[str] = None
                ack_obj: Optional[Dict[str, Any]] = None
                latency_ms: Optional[float] = None

                for attempt in range(1, args.retries + 1):
                    t0 = time.perf_counter_ns()
                    try:
                        ack = await send_cmd(client, cmd, item, timeout_s)
                        t1 = time.perf_counter_ns()
                        latency_ms = (t1 - t0) / 1e6

                        ack_obj = ack if isinstance(ack, dict) else {"raw": repr(ack)}
                        ok, err = ack_is_ok(ack_obj)

                        if ok:
                            break

                        # Recovery ping for no-ack-like outcomes
                        if err in NO_ACK_LIKE_ERRORS:
                            await _recovery_ping(client, delay_s=0.15)

                    except asyncio.TimeoutError:
                        t1 = time.perf_counter_ns()
                        latency_ms = (t1 - t0) / 1e6
                        err = f"timeout (attempt {attempt}/{args.retries})"
                        await _recovery_ping(client, delay_s=0.15)

                    except Exception as e:
                        t1 = time.perf_counter_ns()
                        latency_ms = (t1 - t0) / 1e6
                        err = f"{type(e).__name__}: {e}"

                    await asyncio.sleep(0.05)

                # Mark prereq flags on failures
                if cmd == CMD_CTRL_SIGNAL_DEFINE and not ok:
                    ctx.signals_defined_ok = False
                if cmd == CMD_CTRL_SLOT_CONFIG and not ok:
                    ctx.slot_config_ok = False

                # Soft-skip capability errors
                if (not ok) and (err in SOFT_SKIP_ERRORS) and (only_set is None or cmd not in only_set):
                    results.append(
                        CmdResult(
                            cmd=cmd,
                            ok=False,
                            skipped=True,
                            latency_ms=latency_ms,
                            error=f"skipped ({err})",
                            payload=item,
                            ack=ack_obj,
                        )
                    )
                    await asyncio.sleep(_extra_delay_ms(args, cmd) / 1000.0)
                    continue

                # Soft-skip CONTROL no-ack-like errors (default ON)
                if (
                    (not ok)
                    and args.soft_skip_control_noack
                    and (cmd in CONTROL_COMMANDS)
                    and (err in NO_ACK_LIKE_ERRORS)
                    and (only_set is None or cmd not in only_set)
                ):
                    results.append(
                        CmdResult(
                            cmd=cmd,
                            ok=False,
                            skipped=True,
                            latency_ms=latency_ms,
                            error=f"skipped ({err} - no ACK from MCU control handler)",
                            payload=item,
                            ack=ack_obj,
                        )
                    )
                    await asyncio.sleep(_extra_delay_ms(args, cmd) / 1000.0)
                    continue

                results.append(
                    CmdResult(
                        cmd=cmd,
                        ok=ok,
                        skipped=False,
                        latency_ms=latency_ms,
                        error=err,
                        payload=item,
                        ack=ack_obj,
                    )
                )
                await asyncio.sleep(_extra_delay_ms(args, cmd) / 1000.0)

    finally:
        stop = getattr(client, "stop", None)
        if callable(stop):
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await stop()

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["cmd", "category", "ok", "skipped", "latency_ms", "error", "payload", "ack"],
        )
        w.writeheader()
        for r in results:
            w.writerow(
                {
                    "cmd": r.cmd,
                    "category": get_command_category(r.cmd),
                    "ok": r.ok,
                    "skipped": r.skipped,
                    "latency_ms": f"{r.latency_ms:.3f}" if r.latency_ms is not None else "",
                    "error": r.error or "",
                    "payload": json.dumps(r.payload, separators=(",", ":")),
                    "ack": json.dumps(r.ack, separators=(",", ":")) if r.ack is not None else "",
                }
            )

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_out = [{**asdict(r), "category": get_command_category(r.cmd)} for r in results]
    json_path.write_text(json.dumps(json_out, indent=2), encoding="utf-8")

    passed = sum(1 for r in results if r.ok)
    failed = sum(1 for r in results if (not r.ok) and (not r.skipped))
    skipped = sum(1 for r in results if r.skipped)

    print(f"\n{'='*60}")
    print(f"[send_all_commands] RESULTS")
    print(f"{'='*60}")
    print(f"  Total:   {len(results)}")
    print(f"  Passed:  {passed}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")
    print(f"{'='*60}")

    if failed > 0:
        print("\nFailed commands:")
        for r in results:
            if not r.ok and not r.skipped:
                print(f"  ✗ {r.cmd}: {r.error}")

    print(f"\n[send_all_commands] wrote: {csv_path}")
    print(f"[send_all_commands] wrote: {json_path}")

    return 0 if failed == 0 else 2


def main() -> None:
    args = build_argparser().parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
