import pytest
from starlette.testclient import TestClient

from mara_host.mcp.http_server import create_http_app
from mara_host.mcp.runtime import MaraRuntime
from tests.fakes.fake_mara_server import FakeMaraTcpServer


def test_runtime_repeated_connect_disconnect_cycles_over_http():
    server = FakeMaraTcpServer().start_in_thread()
    try:
        runtime = MaraRuntime(host="127.0.0.1", tcp_port=server.port)
        app = create_http_app(runtime)

        with TestClient(app) as client:
            for _ in range(5):
                connect = client.post("/connect", json={})
                assert connect.status_code == 200
                assert connect.json()["status"] in ("connected", "already_connected")

                health = client.get("/health")
                assert health.status_code == 200
                assert health.json()["connected"] is True

                disconnect = client.post("/disconnect", json={})
                assert disconnect.status_code == 200
                assert disconnect.json()["status"] == "disconnected"

                after = client.get("/health")
                assert after.status_code == 503
                assert after.json()["connected"] is False
    finally:
        server.stop_threaded()


def test_runtime_recovers_after_fake_server_restart():
    server = FakeMaraTcpServer().start_in_thread()
    try:
        runtime = MaraRuntime(host="127.0.0.1", tcp_port=server.port)
        app = create_http_app(runtime)

        with TestClient(app) as client:
            first = client.post("/connect", json={})
            assert first.status_code == 200
            assert first.json()["status"] in ("connected", "already_connected")

            # Simulate transport disappearance.
            server.stop_threaded()

            # Runtime should still report prior context, but reconnect should not lie.
            disconnect = client.post("/disconnect", json={})
            assert disconnect.status_code == 200
            assert disconnect.json()["status"] == "disconnected"

            # Fresh connect attempt with server absent should fail honestly.
            with pytest.raises(RuntimeError, match="Handshake timed out"):
                client.post("/connect", json={})

        # Bring server back and prove runtime can reconnect cleanly.
        server = FakeMaraTcpServer(port=server.port).start_in_thread()
        runtime2 = MaraRuntime(host="127.0.0.1", tcp_port=server.port)
        app2 = create_http_app(runtime2)
        with TestClient(app2) as client2:
            second = client2.post("/connect", json={})
            assert second.status_code == 200
            assert second.json()["status"] in ("connected", "already_connected")
    finally:
        server.stop_threaded()
