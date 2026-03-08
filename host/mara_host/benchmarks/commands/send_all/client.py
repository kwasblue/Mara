# mara_host/benchmarks/commands/send_all/client.py
"""Client building and communication functions."""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any, Dict

from .commands import CMD_HEARTBEAT, CMD_GET_RATES
from .types import Payload
from .helpers import (
    _resolve_transport_class,
    _construct_transport,
    _send_reliable_supports_timeout,
)


async def build_client(args) -> Any:
    """Build and start a MaraClient from command line arguments."""
    from mara_host.command.client import MaraClient

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

    client = MaraClient(
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
    """Warm up the client with heartbeats."""
    if not hasattr(client, "send_reliable"):
        return

    for _ in range(max(1, int(n_heartbeats))):
        with contextlib.suppress(Exception):
            await client.send_reliable(CMD_HEARTBEAT, {}, wait_for_ack=True)
        await asyncio.sleep(delay_s)

    with contextlib.suppress(Exception):
        await client.send_reliable(CMD_GET_RATES, {}, wait_for_ack=True)
    await asyncio.sleep(delay_s)


async def recovery_ping(client: Any, delay_s: float = 0.15) -> None:
    """Send a recovery heartbeat ping."""
    if not hasattr(client, "send_reliable"):
        return
    with contextlib.suppress(Exception):
        await client.send_reliable(CMD_HEARTBEAT, {}, wait_for_ack=True)
    await asyncio.sleep(delay_s)


async def send_cmd(client: Any, cmd: str, payload: Payload, timeout_s: float) -> Dict[str, Any]:
    """Send a command and return the result."""
    if not hasattr(client, "send_reliable"):
        raise RuntimeError(
            f"Client {type(client).__name__} has no send_reliable(). "
            "Expected mara_host.command.client.MaraClient."
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
