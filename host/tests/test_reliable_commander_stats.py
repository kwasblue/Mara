import asyncio
import inspect
import time
from typing import Any, Dict, Optional

import pytest


def _import_commander():
    from mara_host.command.coms.reliable_commander import ReliableCommander  # type: ignore
    return ReliableCommander


@pytest.mark.asyncio
async def test_reliable_commander_ack_and_stats():
    ReliableCommander = _import_commander()

    send_calls = []
    seq_counter = {"v": 100}

    async def send_func(cmd_type: str, payload: Dict[str, Any], seq: Optional[int] = None) -> int:
        # Emulate your client's behavior: if seq is passed, reuse it; else allocate
        if seq is None:
            seq_counter["v"] += 1
            seq = seq_counter["v"]
        send_calls.append((cmd_type, dict(payload), seq))
        return seq

    events = []

    def on_event(evt: Dict[str, Any]) -> None:
        events.append(evt)

    # Commander signature may or may not include on_event
    sig = inspect.signature(ReliableCommander.__init__)
    kwargs = dict(timeout_s=0.2, max_retries=2)
    if "on_event" in sig.parameters:
        kwargs["on_event"] = on_event

    commander = ReliableCommander(send_func=send_func, **kwargs)

    # Must start update loop for queue-based ACK processing (Phase 5 fix)
    await commander.start_update_loop(interval_s=0.01)

    try:
        # Start send and then ack it
        task = asyncio.create_task(commander.send("CMD_TEST", {"x": 1}, wait_for_ack=True))

        # Wait until at least one send happened
        t0 = time.time()
        while not send_calls and (time.time() - t0) < 1.0:
            await asyncio.sleep(0.001)

        assert send_calls, "Expected send_func to be called"
        seq = send_calls[-1][2]

        # Queue the ACK for async processing
        commander.on_ack(seq, ok=True, error=None)

        # Give time for ACK to be processed from queue
        await asyncio.sleep(0.05)

        ok, err = await asyncio.wait_for(task, timeout=1.0)
        assert ok is True
        assert err is None

        st = commander.stats()
        assert st["commands_sent"] >= 1
        assert st["acks_received"] >= 1
        assert st["pending"] == 0

        # If you wired event emission, ensure we emitted at least something
        if "on_event" in sig.parameters:
            assert len(events) > 0
    finally:
        await commander.stop_update_loop()


@pytest.mark.asyncio
async def test_reliable_commander_retries_then_ack():
    ReliableCommander = _import_commander()

    send_calls = []
    seq_counter = {"v": 200}

    async def send_func(cmd_type: str, payload: Dict[str, Any], seq: Optional[int] = None) -> int:
        if seq is None:
            seq_counter["v"] += 1
            seq = seq_counter["v"]
        send_calls.append((cmd_type, dict(payload), seq))
        return seq

    commander = ReliableCommander(send_func=send_func, timeout_s=0.02, max_retries=2)

    await commander.start_update_loop(interval_s=0.005)

    try:
        task = asyncio.create_task(commander.send("CMD_RETRY", {"a": 1}, wait_for_ack=True))

        # Wait for initial send
        t0 = time.time()
        while len(send_calls) < 1 and (time.time() - t0) < 1.0:
            await asyncio.sleep(0.001)
        assert len(send_calls) >= 1
        seq = send_calls[0][2]

        # Wait long enough for at least one retry
        await asyncio.sleep(0.05)
        assert len(send_calls) >= 2, f"Expected at least one retry send, got {len(send_calls)}"
        assert commander.stats()["retries"] >= 1

        # Ack and finish (queue-based processing)
        commander.on_ack(seq, ok=True, error=None)

        # Give time for ACK to be processed from queue
        await asyncio.sleep(0.05)

        ok, err = await asyncio.wait_for(task, timeout=1.0)
        assert ok is True
        assert err is None
    finally:
        await commander.stop_update_loop()
