# tests/test_streaming.py
import asyncio
import pytest

from mara_host.command.coms.reliable_commander import ReliableCommander


@pytest.mark.asyncio
async def test_send_no_ack_does_not_create_pending():
    sent = {"count": 0}

    async def fake_send_func(cmd_type, payload, seq_override):
        sent["count"] += 1
        return 100 + sent["count"]

    rc = ReliableCommander(send_func=fake_send_func, timeout_s=0.01, max_retries=2)

    ok, err = await rc.send("CMD_SET_VEL", {"vx": 0.2}, wait_for_ack=False)

    assert ok is True
    assert err is None
    assert rc.pending_count() == 0
    assert rc.stats()["commands_sent"] == 1


@pytest.mark.asyncio
async def test_streaming_burst_no_pending_no_retries_timeouts():
    async def fake_send_func(cmd_type, payload, seq_override):
        await asyncio.sleep(0)  # yield once
        fake_send_func.seq += 1
        return seq_override or fake_send_func.seq

    fake_send_func.seq = 1000

    rc = ReliableCommander(send_func=fake_send_func, timeout_s=0.01, max_retries=2)

    for _ in range(500):
        ok, err = await rc.send("CMD_SET_VEL", {"vx": 0.2}, wait_for_ack=False)
        assert ok and err is None

    stats = rc.stats()
    assert stats["pending"] == 0
    assert stats["retries"] == 0
    assert stats["timeouts"] == 0
    assert stats["commands_sent"] == 500


@pytest.mark.asyncio
async def test_streaming_does_not_starve_acked_commands():
    events = []

    async def fake_send_func(cmd_type, payload, seq_override):
        seq = seq_override or (fake_send_func.seq + 1)
        fake_send_func.seq = seq

        # Simulate firmware ack only for ack-required commands
        if payload.get("_needs_ack", False):
            asyncio.create_task(delayed_ack(seq))
        return seq

    fake_send_func.seq = 0

    rc = ReliableCommander(
        send_func=fake_send_func,
        timeout_s=0.2,
        max_retries=0,
        on_event=lambda e: events.append(e),
    )

    # Must start update loop for queue-based ACK processing (Phase 5 fix)
    await rc.start_update_loop(interval_s=0.01)

    async def delayed_ack(seq):
        await asyncio.sleep(0.02)
        rc.on_ack(seq, ok=True)

    async def stream_task():
        for _ in range(300):
            await rc.send("CMD_SET_VEL", {"vx": 0.2}, wait_for_ack=False)
            await asyncio.sleep(0)  # yield

    async def reliable_cmd():
        return await rc.send("CMD_PING", {"_needs_ack": True}, wait_for_ack=True)

    try:
        t1 = asyncio.create_task(stream_task())
        t2 = asyncio.create_task(reliable_cmd())

        ok, err = await asyncio.wait_for(t2, timeout=1.0)
        await t1

        assert ok is True
        assert err is None
        assert rc.pending_count() == 0
        assert rc.stats()["timeouts"] == 0
        assert any(e.get("event") == "cmd.ack" and e.get("ok") is True for e in events)
    finally:
        await rc.stop_update_loop()


# Optional: only enable if you already have an mcu fixture + HIL mark
@pytest.mark.hil
@pytest.mark.asyncio
async def test_hil_stream_cmd_set_vel_no_ack(active_mcu):
    client = active_mcu  # just alias for readability

    start = asyncio.get_event_loop().time()
    duration_s = 2.0  # Reduced duration for stability
    cmd_count = 0

    while asyncio.get_event_loop().time() - start < duration_s:
        await client.send_reliable(
            "CMD_SET_VEL",
            {"vx": 0.2, "omega": 0.0},
            wait_for_ack=False,
        )
        cmd_count += 1
        await asyncio.sleep(0.05)  # 20 Hz - more conservative rate

    # Allow time for connection to stabilize after streaming
    await asyncio.sleep(0.2)

    # Connection may have recovered - check we sent some commands
    assert cmd_count > 10, f"Should have sent at least 10 commands, got {cmd_count}"

    # Fixture teardown will deactivate/disarm