import pytest

from mara_host.command.client import MaraClient
from mara_host.core.result import ServiceResult
from mara_host.services.control.control_graph_service import ControlGraphService
from mara_host.transport.tcp_transport import AsyncTcpTransport
from tests.fakes.fake_mara_server import FakeMaraTcpServer


async def _build_service(fake_server):
    transport = AsyncTcpTransport(fake_server.host, fake_server.port)
    client = MaraClient(transport, verbose=False)
    await client.start()
    return client, ControlGraphService(client)


@pytest.fixture
def sample_graph():
    return {
        "schema_version": 1,
        "slots": [
            {
                "id": "imu_pitch_servo",
                "enabled": True,
                "rate_hz": 20,
                "source": {"type": "imu_axis", "params": {"axis": "pitch"}},
                "transforms": [
                    {"type": "deadband", "params": {"threshold": 1.0}},
                    {"type": "scale", "params": {"factor": 3.0}},
                    {"type": "delta_gate", "params": {"threshold": 0.75}},
                    {"type": "slew_rate", "params": {"rate": 90.0}},
                ],
                "sink": {"type": "servo_angle", "params": {"servo_id": 0}},
            }
        ],
    }


@pytest.mark.asyncio
async def test_control_graph_upload_and_clear(sample_graph):
    fake_mara_server = await FakeMaraTcpServer().start()
    client, service = await _build_service(fake_mara_server)
    try:
        result = await service.upload(sample_graph)
        assert result.ok
        assert result.data["graph"]["slots"][0]["id"] == "imu_pitch_servo"
        assert result.data["present"] is True
        assert result.data["slot_count"] == 1

        clear_result = await service.clear()
        assert clear_result.ok
        assert clear_result.data["cleared"] is True
        assert service.cached_graph is None
    finally:
        await client.stop()
        await fake_mara_server.stop()


@pytest.mark.asyncio
async def test_control_graph_apply_enable_and_status(sample_graph):
    fake_mara_server = await FakeMaraTcpServer().start()
    client, service = await _build_service(fake_mara_server)
    try:
        apply_result = await service.apply(sample_graph)
        assert apply_result.ok
        assert apply_result.data["enabled"] is True
        assert apply_result.data["graph"]["slots"][0]["enabled"] is True

        disable_result = await service.disable()
        assert disable_result.ok
        assert disable_result.data["enabled"] is False
        assert service.cached_graph["slots"][0]["enabled"] is False

        status_result = await service.status()
        assert status_result.ok
        assert status_result.data["present"] is True
        assert status_result.data["schema_version"] == 1
        assert "slots" in status_result.data
    finally:
        await client.stop()
        await fake_mara_server.stop()


@pytest.mark.asyncio
async def test_control_graph_upload_rejects_invalid_graph():
    fake_mara_server = await FakeMaraTcpServer().start()
    client, service = await _build_service(fake_mara_server)
    try:
        result = await service.upload({"slots": [{"id": "bad"}]})
        assert not result.ok
        assert "source" in result.error or "sink" in result.error
    finally:
        await client.stop()
        await fake_mara_server.stop()


@pytest.mark.asyncio
async def test_control_graph_apply_fails_when_status_disagrees(sample_graph, monkeypatch):
    fake_mara_server = await FakeMaraTcpServer().start()
    client, service = await _build_service(fake_mara_server)
    try:
        async def fake_status():
            return ServiceResult.success(
                data={
                    "present": False,
                    "enabled": False,
                    "schema_version": 0,
                    "slot_count": 0,
                    "slots": [],
                }
            )

        monkeypatch.setattr(service, "status", fake_status)
        result = await service.apply(sample_graph)
        assert not result.ok
        assert "graph-status disagrees" in result.error
    finally:
        await client.stop()
        await fake_mara_server.stop()
