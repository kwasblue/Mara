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


def test_http_runtime_connect_state_and_disconnect_round_trip():
    server = FakeMaraTcpServer().start_in_thread()
    try:
        runtime = MaraRuntime(host="127.0.0.1", tcp_port=server.port)
        app = create_http_app(runtime)

        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200
            assert health.json()["connected"] is True

            state = client.get("/state")
            assert state.status_code == 200
            body = state.json()
            assert body["connected"] is True
            assert body["firmware"] == "fake-fw"
            assert body["robot_state"]["value"] == "ARMED"

            disconnect = client.post("/disconnect")
            assert disconnect.status_code == 200
            assert disconnect.json()["status"] == "disconnected"

            after = client.get("/health")
            assert after.status_code == 503
            assert after.json()["connected"] is False
    finally:
        server.stop_threaded()


def test_http_read_endpoints_return_fake_ack_payloads():
    server = FakeMaraTcpServer().start_in_thread()
    try:
        runtime = MaraRuntime(host="127.0.0.1", tcp_port=server.port)
        app = create_http_app(runtime)

        with TestClient(app) as client:
            gpio = client.post("/gpio/read", json={"channel": 5})
            assert gpio.status_code == 200
            gpio_body = gpio.json()
            assert gpio_body["ok"] is True
            assert gpio_body["data"]["channel"] == 5
            assert gpio_body["data"]["value"] == 1

            encoder = client.post("/encoder/read", json={"encoder_id": 2})
            assert encoder.status_code == 200
            encoder_body = encoder.json()
            assert encoder_body["ok"] is True
            assert encoder_body["data"]["encoder_id"] == 2
            assert encoder_body["data"]["ticks"] == 123

            ultrasonic = client.post("/ultrasonic/read", json={"sensor_id": 1})
            assert ultrasonic.status_code == 200
            ultrasonic_body = ultrasonic.json()
            assert ultrasonic_body["ok"] is True
            assert ultrasonic_body["data"]["sensor_id"] == 1
            assert ultrasonic_body["data"]["distance_cm"] == 42.5
    finally:
        server.stop_threaded()


def test_http_servo_attach_and_arm_flow_reaches_fake_firmware():
    server = FakeMaraTcpServer().start_in_thread()
    try:
        runtime = MaraRuntime(host="127.0.0.1", tcp_port=server.port)
        app = create_http_app(runtime)

        with TestClient(app) as client:
            arm = client.post("/state/arm", json={})
            assert arm.status_code == 200
            assert arm.json()["ok"] is True
            assert any(cmd.get("type") == "CMD_ARM" for cmd in server.command_log)

            attach = client.post(
                "/servo/attach",
                json={"servo_id": 0, "pin": 18, "min_us": 500, "max_us": 2500},
            )
            assert attach.status_code == 200
            attach_body = attach.json()
            assert attach_body["ok"] is True
            assert any(
                cmd.get("type") == "CMD_SERVO_ATTACH" and cmd.get("channel") == 18
                for cmd in server.command_log
            )
    finally:
        server.stop_threaded()


def test_http_state_endpoint_reflects_disarm_result_immediately():
    server = FakeMaraTcpServer().start_in_thread()
    try:
        runtime = MaraRuntime(host="127.0.0.1", tcp_port=server.port)
        app = create_http_app(runtime)

        with TestClient(app) as client:
            arm = client.post("/state/arm", json={})
            assert arm.status_code == 200
            assert arm.json()["state"] == "ARMED"

            disarm = client.post("/state/disarm", json={})
            assert disarm.status_code == 200
            assert disarm.json()["state"] == "IDLE"

            state = client.get("/state")
            assert state.status_code == 200
            assert state.json()["robot_state"]["value"] == "IDLE"
    finally:
        server.stop_threaded()
