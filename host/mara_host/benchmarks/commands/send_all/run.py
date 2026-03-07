# mara_host/benchmarks/commands/send_all/run.py
"""Main run logic for send_all benchmark."""
from __future__ import annotations

import asyncio
import contextlib
import csv
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .commands import (
    ALL_COMMANDS,
    CMD_ARM,
    CMD_ACTIVATE,
    CMD_CLEAR_ESTOP,
    CMD_CTRL_SET_RATE,
    CMD_CTRL_SIGNAL_DEFINE,
    CMD_CTRL_SIGNAL_GET,
    CMD_CTRL_SIGNAL_SET,
    CMD_CTRL_SIGNALS_LIST,
    CMD_CTRL_SLOT_CONFIG,
    CMD_CTRL_SLOT_ENABLE,
    CMD_CTRL_SLOT_RESET,
    CMD_DEACTIVATE,
    CMD_DISARM,
    CMD_GET_RATES,
    CMD_HEARTBEAT,
    CMD_SAFETY_SET_RATE,
    CMD_SET_MODE,
    CMD_STOP,
    CMD_TELEM_SET_RATE,
    CONTROL_COMMANDS,
    IDLE_ONLY_COMMANDS,
    NO_ACK_LIKE_ERRORS,
    SOFT_SKIP_ERRORS,
    filter_commands,
    get_command_category,
)
from .types import CmdResult, PayloadSpec, RunContext
from .helpers import (
    ack_is_ok,
    ensure_artifacts_dir,
    load_payloads,
    payload_items,
    should_skip_cmd,
)
from .client import build_client, warmup_client, recovery_ping, send_cmd


def reorder_state_machine_aware(cmds: List[str], *, only_set: Optional[set[str]], unsafe_motion: bool) -> List[str]:
    """Reorder commands to respect state machine constraints."""
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


def _per_cmd_timeout(args, cmd: str) -> float:
    """Get timeout for a specific command."""
    if cmd in CONTROL_COMMANDS:
        return float(max(args.cmd_timeout, args.control_timeout))
    return float(args.cmd_timeout)


def _extra_delay_ms(args, cmd: str) -> int:
    """Get extra delay for a specific command."""
    if cmd in CONTROL_COMMANDS:
        return int(args.delay_ms + args.control_delay_ms)
    return int(args.delay_ms)


async def _probe_control_module(client: Any, args, only_set: Optional[set[str]]) -> tuple[bool, Optional[str]]:
    """
    Probe the control module to check availability.

    Returns (control_available, reason_if_not).
    If the user forced control commands via --only, we still report unavailable
    but won't auto-skip them (caller uses only_set).
    """
    if not args.probe_control:
        return True, None

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
    """Main run function for the benchmark."""
    from .cli import list_commands

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
                        payload=payload_items(payload_spec)[0] if payload_items(payload_spec) else {},
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
                            payload=payload_items(payload_spec)[0] if payload_items(payload_spec) else {},
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
                            payload=payload_items(payload_spec)[0] if payload_items(payload_spec) else {},
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
                        payload=payload_items(payload_spec)[0] if payload_items(payload_spec) else {},
                        ack=None,
                    )
                )
                await asyncio.sleep(_extra_delay_ms(args, cmd) / 1000.0)
                continue

            items = payload_items(payload_spec) or [{}]
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
                            await recovery_ping(client, delay_s=0.15)

                    except asyncio.TimeoutError:
                        t1 = time.perf_counter_ns()
                        latency_ms = (t1 - t0) / 1e6
                        err = f"timeout (attempt {attempt}/{args.retries})"
                        await recovery_ping(client, delay_s=0.15)

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

    # Write results
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
