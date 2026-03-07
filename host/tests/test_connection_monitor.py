import asyncio
import pytest


def _import_connection_monitor():
    # Support either location
    try:
        from mara_host.command.coms.connection_monitor import ConnectionMonitor  # type: ignore
        return ConnectionMonitor
    except Exception:
        from mara_host.core.connection_monitor import ConnectionMonitor  # type: ignore
        return ConnectionMonitor


@pytest.mark.asyncio
async def test_connection_monitor_disconnect_reconnect(monkeypatch):
    ConnectionMonitor = _import_connection_monitor()

    # Controlled monotonic time
    t = {"now": 1000.0}

    def fake_monotonic():
        return t["now"]

    import time as _time
    monkeypatch.setattr(_time, "monotonic", fake_monotonic)

    events = []

    def on_disc():
        events.append("disc")

    def on_rec():
        events.append("rec")

    cm = ConnectionMonitor(timeout_s=1.0, on_disconnect=on_disc, on_reconnect=on_rec)

    # First message => connected + reconnect callback
    cm.on_message_received()
    assert cm.connected is True
    assert events == ["rec"]

    # No timeout yet
    t["now"] += 0.5
    cm.check()
    assert cm.connected is True
    assert events == ["rec"]

    # Timeout triggers disconnect
    t["now"] += 1.0
    cm.check()
    assert cm.connected is False
    assert events == ["rec", "disc"]

    # New message => reconnect again
    cm.on_message_received()
    assert cm.connected is True
    assert events == ["rec", "disc", "rec"]


@pytest.mark.asyncio
async def test_connection_monitor_background_loop():
    ConnectionMonitor = _import_connection_monitor()

    events = []
    cm = ConnectionMonitor(timeout_s=0.02, on_disconnect=lambda: events.append("disc"))

    cm.on_message_received()
    await cm.start_monitoring(interval_s=0.005)
    try:
        await asyncio.sleep(0.05)  # real time
        assert "disc" in events
    finally:
        await cm.stop_monitoring()
