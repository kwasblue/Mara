import asyncio
import pytest

from mara_host.core import protocol
from tests.fakes.fake_async_transport import FakeAsyncTransport
from tests.helpers import CapturingBus


def _import_client():
    # Your file name in the listing is mara_host/core/client.py but you pasted client_async.py
    # We'll support both.
    try:
        from mara_host.command.client import BaseMaraClient  # type: ignore
        return BaseMaraClient
    except Exception:
        from mara_host.command.client_async import BaseMaraClient  # type: ignore
        return BaseMaraClient


@pytest.mark.asyncio
async def test_client_receives_pong_and_heartbeat_events():
    BaseMaraClient = _import_client()

    bus = CapturingBus()
    transport = FakeAsyncTransport(auto_ack=False)  # we're manually injecting inbound frames
    client = BaseMaraClient(
        transport=transport,
        bus=bus,
        heartbeat_interval_s=10.0,    # avoid background traffic
        connection_timeout_s=0.2,
        command_timeout_s=0.05,
        max_retries=0,
        require_version_match=False,  # ✅ skip handshake for unit tests
    )

    await client.start()

    await transport.inject_pong()
    await transport.inject_heartbeat()

    assert "pong" in bus.topics()
    assert "heartbeat" in bus.topics()

    await client.stop()


@pytest.mark.asyncio
async def test_client_routes_json_hello_and_telemetry():
    BaseMaraClient = _import_client()

    bus = CapturingBus()
    transport = FakeAsyncTransport(auto_ack=False)
    client = BaseMaraClient(
        transport=transport,
        bus=bus,
        heartbeat_interval_s=10.0,
        connection_timeout_s=0.2,
        command_timeout_s=0.05,
        max_retries=0,
        require_version_match=False,  # ✅
    )
    await client.start()

    # HELLO
    await transport._inject_json_from_mcu({"type": "HELLO", "foo": 1})
    assert bus.last("hello") is not None
    assert bus.last("hello").data["foo"] == 1

    # TELEMETRY
    await transport._inject_json_from_mcu({"type": "TELEMETRY", "bar": 2})
    assert bus.last("telemetry.raw") is not None
    assert bus.last("telemetry") is not None
    assert bus.last("telemetry").data["bar"] == 2

    await client.stop()


@pytest.mark.asyncio
async def test_client_reliable_command_completes_with_ack():
    BaseMaraClient = _import_client()

    bus = CapturingBus()
    transport = FakeAsyncTransport(auto_ack=True)  # auto-ACK reliable commands
    client = BaseMaraClient(
        transport=transport,
        bus=bus,
        heartbeat_interval_s=10.0,
        connection_timeout_s=0.5,
        command_timeout_s=0.05,
        max_retries=1,
        require_version_match=False,
    )
    await client.start()

    ok, err = await client.send_reliable("CMD_SET_VEL", {"vx": 0.2, "omega": 0.1}, wait_for_ack=True)
    
    # The return value tells us if ACK was received
    assert ok is True, f"Command failed with error: {err}"
    assert err is None

    await client.stop()

@pytest.mark.asyncio
async def test_client_disconnect_clears_pending_and_publishes():
    BaseMaraClient = _import_client()

    bus = CapturingBus()
    transport = FakeAsyncTransport(auto_ack=False)
    # Very short timeouts to force disconnect
    client = BaseMaraClient(
        transport=transport,
        bus=bus,
        heartbeat_interval_s=10.0,
        connection_timeout_s=0.05,
        command_timeout_s=0.02,
        max_retries=0,
        require_version_match=False,  # ✅
    )
    await client.start()

    # Force "connected" first
    await transport.inject_pong()
    assert client.is_connected is True

    # Send reliable command, but no ACK ever arrives -> it'll be pending
    task = asyncio.create_task(client.send_reliable("CMD_LED_ON", {}, wait_for_ack=True))
    await asyncio.sleep(0)  # allow pending registration

    # Now wait for connection timeout to trigger disconnect (monitor loop runs every 0.1 in your code;
    # we started it with interval_s=0.1 inside start()).
    await asyncio.sleep(0.25)

    # Should publish connection.lost and clear pending => task returns CLEARED or TIMEOUT depending on timing
    assert "connection.lost" in bus.topics()

    ok, err = await task
    assert ok is False
    assert err in ("CLEARED", "TIMEOUT")

    await client.stop()


@pytest.mark.asyncio
async def test_client_raw_frame_fallback():
    BaseMaraClient = _import_client()

    bus = CapturingBus()
    transport = FakeAsyncTransport(auto_ack=False)
    client = BaseMaraClient(
        transport=transport,
        bus=bus,
        heartbeat_interval_s=10.0,
        connection_timeout_s=0.5,
        command_timeout_s=0.05,
        max_retries=0,
        require_version_match=False,  # ✅
    )
    await client.start()

    # Unknown msg_type should publish raw_frame
    await transport.inject_raw(0x99, b"\x01\x02\x03")
    evt = bus.last("raw_frame")
    assert evt is not None
    assert evt.data["msg_type"] == 0x99
    assert evt.data["payload"] == b"\x01\x02\x03"

    await client.stop()
