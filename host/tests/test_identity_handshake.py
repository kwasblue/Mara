# tests/test_identity_handshake.py

import pytest
import asyncio

from tests.helpers import CapturingBus
from tests.fakes.fake_async_transport import FakeAsyncTransport
from mara_host.config.version import PROTOCOL_VERSION


def _import_client():
    from mara_host.command.client import BaseAsyncRobotClient
    return BaseAsyncRobotClient


@pytest.mark.asyncio
async def test_identity_handshake_completes_on_identity_kind():
    BaseAsyncRobotClient = _import_client()

    bus = CapturingBus()
    transport = FakeAsyncTransport(auto_ack=False)

    client = BaseAsyncRobotClient(
        transport=transport,
        bus=bus,
        heartbeat_interval_s=10.0,
        require_version_match=True,
        handshake_timeout_s=0.5,
    )

    start_task = asyncio.create_task(client.start())
    await asyncio.sleep(0.05)  # let it reach handshake

    # Inject VERSION_RESPONSE (msg_type 0x05)
    await transport._inject_version_response({
        "protocol": PROTOCOL_VERSION,
        "firmware": "test-fw",
        "board": "esp32",
        "name": "robot",
    })

    await start_task

    assert client.version_verified is True
    assert client.firmware_version == "test-fw"
    assert client.protocol_version == PROTOCOL_VERSION

    await client.stop()