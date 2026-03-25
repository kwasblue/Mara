import pytest
from starlette.testclient import TestClient

from mara_host.mcp.http_server import create_http_app
from mara_host.mcp.runtime import MaraRuntime
from tests.fakes.fake_mara_server import FakeMaraTcpServer


@pytest.mark.asyncio
async def test_fake_tcp_server_supports_real_client_handshake():
    from mara_host.command.client import MaraClient
    from mara_host.transport.tcp_transport import AsyncTcpTransport

    server = await FakeMaraTcpServer().start()
    try:
        transport = AsyncTcpTransport("127.0.0.1", server.port)
        client = MaraClient(transport, heartbeat_interval_s=10.0, handshake_timeout_s=1.0, verbose=False)
        await client.start()
        try:
            assert client.version_verified is True
            assert client.firmware_version == "fake-fw"
            assert client.protocol_version > 0
        finally:
            await client.stop()
    finally:
        await server.stop()


def test_http_health_endpoint_reports_runtime_status_without_robot():
    runtime = MaraRuntime()
    app = create_http_app(runtime)

    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 503
        body = res.json()
        assert body["connected"] is False
        assert body["context_present"] is False
        assert body["healthy"] is False
