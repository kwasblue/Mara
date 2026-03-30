# tests/test_reliable_commander.py
import asyncio
import pytest


def _import_reliable_commander():
    from mara_host.command.coms.reliable_commander import ReliableCommander
    return ReliableCommander


@pytest.mark.asyncio
async def test_reliable_commander_ack_resolves():
    ReliableCommander = _import_reliable_commander()

    calls = []

    async def send_func(cmd_type, payload, seq=None):
        # first send: seq is None
        # retry sends: seq is the original seq
        calls.append((cmd_type, payload, seq))
        # emulate client assigning a seq on first send
        return 1 if seq is None else seq

    rc = ReliableCommander(send_func=send_func, timeout_s=0.05, max_retries=2)
    await rc.start_update_loop(interval_s=0.01)

    try:
        task = asyncio.create_task(rc.send("CMD_SET_VEL", {"vx": 1.0}, wait_for_ack=True))

        # let rc.send run far enough to register pending
        await asyncio.sleep(0.02)
        assert rc.pending_count() == 1

        # Ack it (queued for async processing)
        rc.on_ack(1, True, None)

        # Give time for ACK to be processed from queue
        await asyncio.sleep(0.05)

        ok, err = await asyncio.wait_for(task, timeout=1.0)
        assert ok is True
        assert err is None
        assert rc.pending_count() == 0
        assert rc.acks_received == 1
    finally:
        await rc.stop_update_loop()


@pytest.mark.asyncio
async def test_reliable_commander_retries_and_timeout():
    ReliableCommander = _import_reliable_commander()

    sent = []

    async def send_func(cmd_type, payload, seq=None):
        # Return a stable seq on first send; reuse the same seq on retries
        if seq is None:
            sent.append(("first", cmd_type, payload, None))
            return 42
        sent.append(("retry", cmd_type, payload, seq))
        return seq

    rc = ReliableCommander(send_func=send_func, timeout_s=0.02, max_retries=2)
    await rc.start_update_loop(interval_s=0.005)

    try:
        ok, err = await rc.send("CMD_LED_ON", {}, wait_for_ack=True)

        assert ok is False
        assert err == "TIMEOUT"

        # first send + 2 retries (max_retries=2)
        assert len(sent) == 3
        assert sent[0][0] == "first"
        assert sent[1][0] == "retry"
        assert sent[2][0] == "retry"

        # retries should use the same seq
        assert sent[1][3] == 42
        assert sent[2][3] == 42

        assert rc.timeouts == 1
        assert rc.retries == 2
    finally:
        await rc.stop_update_loop()


@pytest.mark.asyncio
async def test_reliable_commander_clear_pending():
    ReliableCommander = _import_reliable_commander()

    async def send_func(cmd_type, payload, seq=None):
        return 7 if seq is None else seq

    rc = ReliableCommander(send_func=send_func, timeout_s=1.0, max_retries=0)
    await rc.start_update_loop(interval_s=0.01)

    try:
        task = asyncio.create_task(rc.send("CMD_TEST", {}, wait_for_ack=True))
        await asyncio.sleep(0.02)

        assert rc.pending_count() == 1

        # Must await async clear_pending
        await rc.clear_pending()

        ok, err = await asyncio.wait_for(task, timeout=1.0)
        assert ok is False
        assert err == "CLEARED"
        assert rc.pending_count() == 0
    finally:
        await rc.stop_update_loop()
